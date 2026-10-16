# Reproduire et lire les validations

Le développement nécessite Internet pour acquérir dépendances et modèles sur
la machine de build. Le produit installé n'en nécessitera pas. Le README donne
les commandes ; les scripts d'acquisition restent hors du code de l'application.

`requirements.lock` est un verrou avec hashes pour les fondations et les sondes
ASR/sherpa. Après modification, synchroniser `.venv` puis exécuter
`scripts/test.ps1`. Le dossier temporaire unique reste dans le dépôt pour éviter
les restrictions du bac à sable et l'effacement de dossiers non liés à ce travail.
Le rapport JUnit est enregistré dans `docs/evidence/pytest.xml`.

Les tests rapides vérifient les règles métier, le refus d'exports sans relecture
de la révision, les sources et votes inconnus, les assets altérés, migrations,
sauvegarde SQLite, crash d'un vrai processus, délais workers, repli CPU et
conservation des fichiers après erreur. Les fautes synthétiques sont des tests
de résistance et sont marquées comme telles. Elles ne remplacent pas les sondes IA.

`run_phase0_probes.py` lance un worker CUDA puis CPU via le routeur réel et un
processus llama.cpp CPU. `run_diarization_alternative.py` lance le worker sherpa
sur une fixture synthétique à deux voix, avec nombre de groupes automatique.
Les résultats sont conservés dans `docs/evidence`, les requêtes/audio/sorties
de fixtures dans `output/phase0` exclu de Git. Pour le produit, les contenus des
séances ne devront jamais alimenter ces journaux techniques.

Les maxima RSS sont des sommes échantillonnées sur l'arbre de processus,
avec partage mémoire potentiellement compté plusieurs fois. Les durées murales
incluent le chargement. Le son synthétique ne mesure ni WER réaliste ni DER
de réunion. Les trois essais ne forment pas encore une chaîne applicative.

Pour vérifier l'export de phase 0, générer la fixture par `sample_exports.py`.
Les tests relisent les fichiers réels. La QA a rendu le PDF avec Poppler et le
DOCX avec Word installé après indisponibilité de LibreOffice. `render_docx_word.ps1`
ouvre le document en lecture seule, désactive macros et alertes, ferme sa session
et vérifie que le fichier source n'a pas changé. Word reste un outil de QA local.

La recette finale devra couvrir tous les cas du cahier des charges sur VM
Windows propre sans réseau. Un échec GPU doit être injecté à chaque étape, les
sons originaux vérifiés par hashes après crash et les votes inventés recherchés
dans un corpus adversarial. La validation d'une release devra enregistrer les
versions, le hash du Setup et les résultats de chaque machine de recette.
