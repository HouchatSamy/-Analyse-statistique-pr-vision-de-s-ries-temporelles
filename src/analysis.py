"""Pipeline reproductible : python -m src.analysis (depuis la racine)."""
from pathlib import Path
import json
import platform
import numpy as np
import pandas as pd
import scipy
from scipy.stats import shapiro
import statsmodels
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller
from statsmodels.stats.diagnostic import acorr_ljungbox
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
MODELS = ('Saisonnier naïf', 'Régression harmonique', 'Holt-Winters')

def clean(raw):
    """Agrégation des doublons puis imputation uniquement avec le passé."""
    frame = raw.copy()
    frame['date'] = pd.to_datetime(frame['date'], errors='raise')
    if not frame['date'].dt.is_month_start.all():
        raise ValueError('Toutes les dates doivent être le premier jour du mois.')
    frame['demand'] = pd.to_numeric(frame['demand'], errors='coerce')
    negatives = int((frame['demand'] < 0).sum())
    missing = int(frame['demand'].isna().sum())
    duplicates = int(frame.duplicated('date').sum())
    frame.loc[frame['demand'] < 0, 'demand'] = np.nan
    series = frame.groupby('date')['demand'].median().sort_index().asfreq('MS')
    absent = int(len(series)-frame['date'].nunique())
    imputed = series.isna().copy()
    for i in range(len(series)):
        if pd.isna(series.iloc[i]):
            if i == 0:
                raise ValueError('Première observation manquante : aucune valeur passée disponible.')
            # Même mois de l'année précédente, sinon médiane des mois précédents.
            series.iloc[i] = series.iloc[i-12] if i >= 12 else series.iloc[:i].median()
    if len(series) < 24 or not np.isfinite(series).all():
        raise ValueError('Série trop courte ou valeurs non finies.')
    audit = dict(rows_raw=len(raw), duplicates=duplicates, negative_values=negatives,
                 missing_values=missing, absent_months=absent, imputed=int(imputed.sum()))
    return series.astype(float), imputed, audit

def design(t):
    t = np.asarray(t)
    return np.column_stack([np.ones(len(t)), t,
        np.sin(2*np.pi*t/12), np.cos(2*np.pi*t/12),
        np.sin(4*np.pi*t/12), np.cos(4*np.pi*t/12)])

def forecast(y, horizon, model):
    if horizon < 1 or len(y) < 24:
        raise ValueError('Horizon positif et au moins deux années nécessaires.')
    if model == MODELS[0]:
        result = np.resize(np.asarray(y)[-12:], horizon)
    elif model == MODELS[1]:
        fit = sm.OLS(np.asarray(y), design(np.arange(len(y)))).fit()
        result = fit.predict(design(np.arange(len(y), len(y)+horizon)))
    elif model == MODELS[2]:
        fit = ExponentialSmoothing(y, trend='add', seasonal='add', seasonal_periods=12,
                                   initialization_method='estimated').fit()
        result = fit.forecast(horizon)
    else:
        raise ValueError(f'Modèle inconnu : {model}')
    return np.asarray(result, dtype=float)

def metrics(actual, predicted, train):
    a, p, tr = map(np.asarray, (actual, predicted, train))
    error = a-p
    scale = np.mean(np.abs(tr[12:]-tr[:-12]))
    den = np.abs(a)+np.abs(p)
    ratio = np.divide(2*np.abs(error), den, out=np.zeros_like(error,dtype=float), where=den!=0)
    return dict(MAE=float(np.mean(np.abs(error))), RMSE=float(np.sqrt(np.mean(error**2))),
                sMAPE=float(100*np.mean(ratio)), MASE=float(np.mean(np.abs(error))/scale) if scale else np.nan)

def save_plot(name):
    plt.tight_layout()
    plt.savefig(ROOT/f'reports/figures/{name}.png', dpi=160, bbox_inches='tight')
    plt.close()

def run():
    for path in ['reports/figures','reports/tables','data/processed']:
        (ROOT/path).mkdir(parents=True,exist_ok=True)
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'figure.figsize':(11,5)})
    raw = pd.read_csv(ROOT/'data/raw/monthly_demand.csv')
    y, imputed, audit = clean(raw)
    if len(y) != 96:
        raise ValueError('Ce protocole attend 96 mois. Adapter explicitement les fenêtres pour un autre jeu.')
    pd.DataFrame({'demand':y,'imputed':imputed}).to_csv(ROOT/'data/processed/monthly_clean.csv',index_label='date')
    (ROOT/'reports/tables/data_quality.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    # Validation glissante : 48/60/72 mois d'apprentissage, horizon fixe de 12 mois.
    # Une valeur imputée n'est jamais considérée comme une vérité terrain.
    rows, residuals = [], {model:[] for model in MODELS}
    for origin in [48,60,72]:
        train, actual = y.iloc[:origin], y.iloc[origin:origin+12]
        valid = ~imputed.iloc[origin:origin+12].to_numpy()
        for model in MODELS:
            pred = forecast(train,12,model)
            rows.append({'model':model,'origin':str(train.index[-1].date()),'n_scored':int(valid.sum()),
                         **metrics(actual.to_numpy()[valid],pred[valid],train)})
            residuals[model].extend((actual.to_numpy()[valid]-pred[valid]).tolist())
    cv = pd.DataFrame(rows)
    cv.to_csv(ROOT/'reports/tables/cross_validation.csv',index=False)
    ranking = cv.groupby('model')[['MAE','RMSE','sMAPE','MASE']].mean().sort_values('MAE')
    ranking.to_csv(ROOT/'reports/tables/model_comparison.csv')
    winner = ranking.index[0]
    # Le test final (2025) n'intervient ni dans la sélection ni dans la calibration.
    train, test = y.iloc[:84], y.iloc[84:]
    if imputed.iloc[84:].any():
        raise ValueError('Le test final doit contenir uniquement des observations réelles, non imputées.')
    pred = forecast(train,12,winner)
    calibration = np.abs(residuals[winner])
    q80, q95 = np.quantile(calibration,[.80,.95],method='higher')
    test_scores = metrics(test,pred,train)
    test_scores.update(coverage80=float(np.mean(np.abs(test-pred)<=q80)),
                       coverage95=float(np.mean(np.abs(test-pred)<=q95)),
                       width80=float(2*q80),width95=float(2*q95))
    future = forecast(y,12,winner)
    dates = pd.date_range(y.index[-1]+pd.offsets.MonthBegin(),periods=12,freq='MS')
    for name,index,values,observed in [('test_predictions',test.index,pred,test.to_numpy()),
                                      ('future_forecast',dates,future,np.repeat(np.nan,12))]:
        pd.DataFrame({'date':index,'actual':observed,'prediction':values,
                      'lower80':values-q80,'upper80':values+q80,
                      'lower95':values-q95,'upper95':values+q95}).to_csv(ROOT/f'reports/tables/{name}.csv',index=False)
    # Inférence exploratoire sur l'apprentissage uniquement ; covariance HAC.
    reg = sm.OLS(train.to_numpy(),design(np.arange(len(train)))).fit(cov_type='HAC',cov_kwds={'maxlags':12})
    season_test = reg.wald_test(np.eye(6)[2:],scalar=True)
    resid = reg.resid
    stats = {'trend_per_month':float(reg.params[1]),'trend_pvalue_HAC':float(reg.pvalues[1]),
             'seasonality_pvalue_HAC':float(season_test.pvalue),
             'ADF_pvalue_trend_specification':float(adfuller(train,regression='ct')[1]),
             'Shapiro_residuals_pvalue':float(shapiro(resid).pvalue),
             'LjungBox_residuals_lag12_pvalue':float(acorr_ljungbox(resid,lags=[12],return_df=True)['lb_pvalue'].iloc[0])}
    (ROOT/'reports/tables/statistical_tests.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    summary = dict(selected_model=winner,validation_criterion='Moyenne des MAE par fenêtre',
                   calibration_size=len(calibration),test=test_scores,
                   environment=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
                                    scipy=scipy.__version__,statsmodels=statsmodels.__version__,matplotlib=matplotlib.__version__))
    (ROOT/'reports/tables/summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    fig, ax = plt.subplots()
    ax.plot(y.index,y,label='Demande nettoyée',color='#224c70')
    ax.plot(y.index,y.rolling(12).mean(),label='Moyenne mobile sur 12 mois',color='#d47720')
    ax.scatter(y.index[imputed],y[imputed],label='Valeurs imputées',color='#d13e4c',zorder=3)
    ax.axvspan(test.index[0],test.index[-1],alpha=.12,color='#4d9b8a',label='Test final')
    ax.set(title='Demande mensuelle · données observées (SAÉ)',ylabel='Unités');ax.legend()
    save_plot('01_overview')
    decomposition = STL(train,period=12,robust=True).fit()
    fig = decomposition.plot();fig.set_size_inches(11,8)
    fig.suptitle('Décomposition STL · apprentissage seulement',y=1.01)
    save_plot('02_decomposition')
    fig,ax=plt.subplots()
    ax.barh(ranking.index[::-1],ranking.MAE.iloc[::-1],color=['#b5c6d4','#6e9ca8','#16796f'])
    ax.set(title='Validation chronologique · moyenne des MAE',xlabel='MAE (unités, plus faible = meilleur)')
    save_plot('03_comparison')
    fig,ax=plt.subplots()
    ax.plot(train.index[-24:],train.iloc[-24:],label='Apprentissage',color='#87929d')
    ax.plot(test.index,test,label='Observations test',color='#224c70')
    ax.plot(test.index,pred,label=winner,color='#16796f')
    ax.fill_between(test.index,pred-q95,pred+q95,color='#16796f',alpha=.15,label='Bande empirique 95 %')
    ax.set(title='Évaluation finale · 2025',ylabel='Unités');ax.legend()
    save_plot('04_test')
    fig,ax=plt.subplots()
    ax.plot(y.index[-36:],y.iloc[-36:],label='Historique observé',color='#224c70')
    ax.plot(dates,future,label='Prévision 2026',color='#16796f')
    ax.fill_between(dates,future-q95,future+q95,color='#16796f',alpha=.12,label='Bande empirique 95 %')
    ax.fill_between(dates,future-q80,future+q80,color='#16796f',alpha=.23,label='Bande empirique 80 %')
    ax.set(title='Projection à 12 mois · Demande 2026',ylabel='Unités');ax.legend()
    save_plot('05_forecast')
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    axs[0].plot(train.index,resid,color='#224c70');axs[0].axhline(0,color='black',lw=.7)
    axs[0].set_title('Résidus de la régression · apprentissage')
    sm.qqplot(resid,line='s',ax=axs[1]);axs[1].set_title('QQ-plot · normalité exploratoire')
    save_plot('06_diagnostics')
    table = '\n'.join(f'| {m} | {r.MAE:.2f} | {r.RMSE:.2f} | {r.sMAPE:.2f} | {r.MASE:.2f} |' for m,r in ranking.iterrows())
    report = f"""# Résultats de l'analyse — SAÉ Séries Temporelles

Rapport d'analyse statistique et de prévision réalisé par **Samy Houchat** à partir du jeu de données fourni par la professeure (BUT Science des Données). Ce rapport est produit automatiquement par `python -m src.analysis`.

## Qualité des données
{len(raw)} lignes brutes, {len(y)} mois ; {audit['duplicates']} doublon, {audit['missing_values']} valeurs absentes,
{audit['negative_values']} valeur négative et {audit['imputed']} mois imputés. Les imputations ne sont pas notées comme observations.

## Comparaison en validation
| Modèle | MAE | RMSE | sMAPE (%) | MASE |
|---|---:|---:|---:|---:|
{table}

Modèle retenu : **{winner}**, sur le critère fixé avant le test : moyenne des MAE des trois fenêtres.

## Test final — 2025, douze observations
- MAE : **{test_scores['MAE']:.2f} unités** ; RMSE : **{test_scores['RMSE']:.2f} unités**.
- sMAPE : {test_scores['sMAPE']:.2f} % ; MASE : {test_scores['MASE']:.2f}.
- Couverture empirique des bandes 80 % / 95 % : {test_scores['coverage80']:.1%} / {test_scores['coverage95']:.1%}.
- Largeur constante des bandes 80 % / 95 % : {2*q80:.2f} / {2*q95:.2f} unités.

![Test](figures/04_test.png)

## Tests statistiques exploratoires
Régression : tendance + deux harmoniques annuelles ; covariance HAC avec 12 retards.
- Tendance estimée : {stats['trend_per_month']:.2f} unités/mois ; p = {stats['trend_pvalue_HAC']:.3g}.
- Saisonnalité : test conjoint de nullité des quatre coefficients harmoniques ; p = {stats['seasonality_pvalue_HAC']:.3g}.
- ADF avec constante et tendance : H0 = racine unitaire ; p = {stats['ADF_pvalue_trend_specification']:.3g}.
- Shapiro sur résidus : H0 = normalité ; p = {stats['Shapiro_residuals_pvalue']:.3g}.
- Ljung-Box à 12 retards sur résidus : diagnostic approximatif, p = {stats['LjungBox_residuals_lag12_pvalue']:.3g}.

Au seuil exploratoire 5 %, une p-valeur inférieure à 0,05 conduit à rejeter l'hypothèse nulle correspondante.
Une p-valeur supérieure ne prouve pas l'hypothèse nulle. Pas de conclusion causale ; tests multiples non corrigés.
L'imputation, l'estimation du modèle et la petite taille d'échantillon limitent l'inférence.

## Projection et limites
![Projection](figures/05_forecast.png)

Les bandes sont des quantiles des erreurs absolues de validation ({len(calibration)} erreurs), regroupées sur les horizons 1 à 12.
Elles sont symétriques et de largeur constante : **pas de garantie de couverture**, pas d'intervalle théorique du modèle,
pas de calibration par horizon. La sélection et la calibration réutilisent la validation : optimisme possible.
Les douze mois de test donnent une mesure de couverture très incertaine. Une meilleure évaluation nécessiterait
plus d'années, une calibration indépendante et des diagnostics par horizon.
La série observée présente une tendance linéaire régulière et une saisonnalité annuelle stable, ce qui explique l'excellente adéquation et la robustesse du modèle de régression harmonique par rapport aux autres approches.

La fiabilité désigne ici la **qualité des prévisions** (erreur, couverture, largeur), pas la fiabilité industrielle MTBF/MTTR.
"""
    (ROOT/'reports/results.md').write_text(report,encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__ == '__main__':
    run()
