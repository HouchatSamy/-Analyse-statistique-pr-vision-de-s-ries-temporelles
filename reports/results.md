# Résultats de l'analyse — SAÉ Séries Temporelles

Rapport d'analyse statistique et de prévision réalisé par **Samy Houchat** à partir du jeu de données fourni par la professeure (BUT Science des Données). Ce rapport est produit automatiquement par `python -m src.analysis`.

## Qualité des données
97 lignes brutes, 96 mois ; 1 doublon, 3 valeurs absentes,
1 valeur négative et 4 mois imputés. Les imputations ne sont pas notées comme observations.

## Comparaison en validation
| Modèle | MAE | RMSE | sMAPE (%) | MASE |
|---|---:|---:|---:|---:|
| Régression harmonique | 30.89 | 36.37 | 2.27 | 0.41 |
| Holt-Winters | 33.22 | 40.93 | 2.46 | 0.44 |
| Saisonnier naïf | 79.52 | 89.64 | 5.89 | 1.04 |

Modèle retenu : **Régression harmonique**, sur le critère fixé avant le test : moyenne des MAE des trois fenêtres.

## Test final — 2025, douze observations
- MAE : **32.07 unités** ; RMSE : **37.93 unités**.
- sMAPE : 2.12 % ; MASE : 0.42.
- Couverture empirique des bandes 80 % / 95 % : 83.3% / 91.7%.
- Largeur constante des bandes 80 % / 95 % : 99.18 / 139.40 unités.

![Test](figures/04_test.png)

## Tests statistiques exploratoires
Régression : tendance + deux harmoniques annuelles ; covariance HAC avec 12 retards.
- Tendance estimée : 5.79 unités/mois ; p = 0.
- Saisonnalité : test conjoint de nullité des quatre coefficients harmoniques ; p = 2.47e-307.
- ADF avec constante et tendance : H0 = racine unitaire ; p = 1.35e-13.
- Shapiro sur résidus : H0 = normalité ; p = 3.43e-05.
- Ljung-Box à 12 retards sur résidus : diagnostic approximatif, p = 0.232.

Au seuil exploratoire 5 %, une p-valeur inférieure à 0,05 conduit à rejeter l'hypothèse nulle correspondante.
Une p-valeur supérieure ne prouve pas l'hypothèse nulle. Pas de conclusion causale ; tests multiples non corrigés.
L'imputation, l'estimation du modèle et la petite taille d'échantillon limitent l'inférence.

## Projection et limites
![Projection](figures/05_forecast.png)

Les bandes sont des quantiles des erreurs absolues de validation (35 erreurs), regroupées sur les horizons 1 à 12.
Elles sont symétriques et de largeur constante : **pas de garantie de couverture**, pas d'intervalle théorique du modèle,
pas de calibration par horizon. La sélection et la calibration réutilisent la validation : optimisme possible.
Les douze mois de test donnent une mesure de couverture très incertaine. Une meilleure évaluation nécessiterait
plus d'années, une calibration indépendante et des diagnostics par horizon.
La série observée présente une tendance linéaire régulière et une saisonnalité annuelle stable, ce qui explique l'excellente adéquation et la robustesse du modèle de régression harmonique par rapport aux autres approches.

La fiabilité désigne ici la **qualité des prévisions** (erreur, couverture, largeur), pas la fiabilité industrielle MTBF/MTTR.
