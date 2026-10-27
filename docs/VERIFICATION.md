# Vérification de la livraison

- Installation réussie dans un environnement Python 3.12 isolé avec `requirements.txt`.
- Exécution complète du pipeline et génération du rapport, des tables et des six graphiques.
- Six tests automatisés réussis : nettoyage causal, absence de fuite depuis le test,
  référence saisonnière, métriques, rejet du premier mois absent, prévisions finies.
- Vérification des douze lignes de prévision et de l'ordre des bornes 80/95 %.
- Inspection visuelle des six graphiques.
- Syntaxe des cellules Python du notebook vérifiée ; notebook fourni sans sorties intégrées.
- Script R autonome disponible dans `scripts/analyse.R` pour exécution locale sous RStudio.

`reports/tables/summary.json` donne les versions effectivement utilisées.
`requirements-lock.txt` fige aussi les dépendances transitives de cet environnement.
Pour le reproduire exactement : `python -m pip install -r requirements-lock.txt`.
