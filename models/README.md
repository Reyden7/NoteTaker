# Modèles locaux

Les poids de test sont exclus de Git. Le script explicite `scripts/acquire_phase0.py`
les acquiert sur la machine de développement, à des révisions précises et avec
contrôle SHA-256. L'application ne contient aucun téléchargeur.

`models_manifest.json` décrit les fichiers réellement acquis. Son statut
`development-only` interdit de les considérer comme un lot de distribution approuvé.
Community-1 n'est pas acquis : accès HTTP 401, conditions à accepter par le compte de build.
