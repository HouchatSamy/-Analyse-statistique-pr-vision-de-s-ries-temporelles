# Protocole d'analyse

## Question
Comment anticiper la demande mensuelle à 12 mois et évaluer rigoureusement l'incertitude prédictive ?
Étude menée dans le cadre de la SAÉ Séries Temporelles (BUT Science des Données) à partir des données fournies par la professeure.

## Séparation chronologique
| Étape | Apprentissage | Évaluation |
|---|---|---|
| Validation 1 | 2018–2021 | 2022 |
| Validation 2 | 2018–2022 | 2023 |
| Validation 3 | 2018–2023 | 2024 |
| Test unique | 2018–2024 | 2025 |
| Projection finale | 2018–2025 | 2026 sans vérité terrain |

Pas de mélange aléatoire train/test. Aucun réglage décidé à partir du test final.
Critère fixé : moyenne non pondérée des MAE des trois fenêtres (une fenêtre contient un point imputé exclu).
Le pipeline réestime le modèle retenu sur les 96 mois pour la projection finale.
Les paramètres du nettoyage sont fixés ; le nettoyage causal complet équivaut au nettoyage de chaque préfixe.

## Modèles et analyse
- Saisonnier naïf : reproduit les douze derniers mois ; référence indispensable.
- Régression : constante, tendance, sinus/cosinus annuels et semestriels ; structure fixée avant validation.
- Holt-Winters : tendance et saisonnalité additives, période 12 ; paramètres estimés sur chaque apprentissage.
- Moyenne mobile arrière sur douze mois : lissage descriptif, pas une prévision.
- STL robuste sur l'apprentissage 2018–2024 : tendance, saisonnalité, résidu ; usage descriptif uniquement.

La série présentant une tendance nette et une composante saisonnière régulière, la régression harmonique capture efficacement la structure temporelle globale.
Python et R ont des initialisations Holt-Winters et des décompositions STL différentes : pas d'égalité numérique attendue.

## Hypothèses et diagnostics
Python : tests de tendance et de saisonnalité conjointe avec covariance HAC, ADF avec constante et tendance,
Shapiro et Ljung-Box sur les résidus de régression. La covariance HAC atténue certaines violations d'indépendance ;
elle ne corrige pas tout. Les p-valeurs restent exploratoires, notamment après imputation.
R : tests classiques de régression avec hypothèse iid, Shapiro et Ljung-Box. Les résultats R ne remplacent pas les tests HAC.
Les diagnostics de régression ne sont pas automatiquement des diagnostics du modèle sélectionné s'il s'agit d'un autre modèle.
Aucun test de différence de moyennes naïf entre mois dépendants. Pas de conclusion causale.

## Mesures de qualité
MAE = moyenne des erreurs absolues ; RMSE = racine de la moyenne des carrés des erreurs.
sMAPE = 100 × moyenne de 2|y−ŷ|/(|y|+|ŷ|), avec 0 si les deux valeurs valent 0.
MASE = MAE divisée par la moyenne des écarts saisonniers absolus de l'apprentissage (retard 12).
MASE < 1 signifie une erreur inférieure à cette échelle d'apprentissage ; ce n'est pas une comparaison directe
avec la performance de la référence sur le test. Si l'échelle est nulle, MASE est indéfinie (NaN).

Les bandes 80/95 % utilisent les quantiles « higher » des erreurs absolues de validation du modèle retenu.
Elles regroupent tous les horizons et réutilisent les données de sélection : calibration indicative, sans garantie.
Couverture = proportion des observations de test comprises entre les bornes ; largeur = borne haute − borne basse.
Avec douze observations, la couverture varie par pas de 8,33 points de pourcentage.
La fiabilité désigne ici la qualité prédictive et non une analyse de durée de vie ou un taux de panne.

## Perspectives et prolongements
Prise en compte d'effets calendaires fins (jours ouvrés, vacances), modélisation SARIMAX avec variables explicatives exogènes, calibration des intervalles de prévision dépendante de l'horizon, et détection de ruptures de tendance.
