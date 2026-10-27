# Dictionnaire et provenance des données

Jeu de données fourni par la professeure dans le cadre de la SAÉ Analyse Statistique et Séries Temporelles.
Période : janvier 2018 à décembre 2025 ; fréquence mensuelle ; variable cible : volume de demande mensuelle (unités).

| Champ brut | Type | Description / Règle de validation |
|---|---|---|
| date | YYYY-MM-DD | Premier jour du mois ; clé temporelle après nettoyage |
| demand | réel | Demande mensuelle observée, attendue positive |

Le fichier brut `data/raw/monthly_demand.csv` contient 97 enregistrements pour 96 mois effectifs, incluant des défauts de qualité réels rencontrés en pratique :
- 1 doublon temporel (mois de juin 2019 dupliqué)
- 3 valeurs manquantes (septembre 2018, juillet 2020, juillet 2022)
- 1 valeur aberrante négative (juin 2021)
- L'échantillon de test (année 2025) est intègre et ne comporte aucune anomalie.

Nettoyage : tri chronologique, conversion de type numérique, recodage des valeurs négatives en valeurs manquantes, calcul de la médiane pour les doublons, réindexation mensuelle continue (`MS`), et imputation causale stricte (valeur à l'horizon m-12 ou médiane des mois antérieurs disponibles).
Le premier mois absent provoquerait une erreur bloquante. Aucun accès aux données futures n'est permis lors de l'imputation.
Les observations imputées sont tracées et exclues du calcul des erreurs de validation/test pour ne pas fausser l'évaluation des modèles.

`data/processed/monthly_clean.csv` ajoute le marqueur `imputed` (booléen).
Les fichiers de résultats contiennent `date`, `actual`, `prediction`, `lower80`, `upper80`, `lower95`, `upper95`.
`actual` est vide pour la projection future 2026 ; les bornes d'incertitude sont calculées de manière empirique sur la validation.
