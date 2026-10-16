# Reproduire et lire les validations

Le développement nécessite Internet pour acquérir dépendances et modèles sur
la machine de build. Le produit installé n'en nécessitera pas. Le README donne
les commandes ; les scripts d'acquisition restent hors du code de l'application.

`requirements.lock` est un verrou avec hashes pour les fondations, l'interface,
ASR/sherpa et le build. Après modification, synchroniser `.venv` puis exécuter
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
de réunion. Ces trois sondes de phase 0 sont indépendantes ; le parcours applicatif
0.1 est désormais exercé séparément par `validate_chain.py`.

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

## Parcours applicatif 0.1 réellement vérifié

Dernière suite : **50 tests réussis** sous Windows, sans modèle ni microphone
nécessaires pour ces tests rapides. `test_session_workflow.py` couvre notamment
stockage, corrections, règles de vote, invalidation de la relecture, import,
rotation/récupération et conservation après erreur. `test_ui.py` manipule les
widgets Qt et simule explicitement les réponses au dialogue de confirmation
sur des séances fictives. Ce test ne vaut pas relecture humaine d'une séance.

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
.venv\Scripts\python.exe -m pytest --basetemp=.cache/pytest-local --junitxml=docs/evidence/pytest-workflow.xml
.venv\Scripts\python.exe scripts\validate_chain.py --audio output/phase0/fr-synthetic.wav --data-dir output/chain-validation-new --fixture
.venv\Scripts\python.exe scripts\validate_codecs.py
.venv\Scripts\python.exe scripts\validate_microphone.py --device 33 --seconds 3
.venv\Scripts\python.exe scripts\validate_bundle.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\validate_desktop.ps1
```

Adapter le numéro du microphone aux périphériques réellement énumérés sur le
poste ; le numéro 33 appartient seulement au contrôle de ce PC. Utiliser un
nouveau dossier `--data-dir` pour chaque chaîne de contrôle. `--fixture` crée
des décisions/votes de test et une validation **automated-fixture-only** :
réservé aux données fictives, jamais à une séance réelle. Le test vérifie d'abord
le refus d'export non relu. Sans cette option, aucun export n'est auto-approuvé.

Les rapports JSON sont `application-chain.json`, `codec-validation.json`,
`microphone-validation.json`, `bundle-validation.json` et `desktop-validation.json`
dans `docs/evidence`. Le dernier vérifie seulement le démarrage/la fermeture de
l'interface compilée et la création de sa base isolée, par messages Windows sur
sa propre fenêtre masquée ; il ne teste pas une réunion complète dans le bundle.
Les fichiers audio et contenus des séances restent dans les dossiers locaux
ignorés par Git. `render_ui.py` rend les cinq onglets avec Qt Windows ; le
moteur offscreen de ce poste affichait des glyphes manquants et ne convient
pas à la vérification visuelle des polices.

Les derniers essais réels sont décrits avec leurs durées et limites dans
`progress.md`. La procédure de réunion naturelle est dans `field-test.md`,
la recette Windows propre déconnecté dans `../packaging/README.md`.
Ces deux recettes restent **non exécutées / non validées**. Le bundle autonome
est testé sur le poste de développement, sans conclure à l'absence de dépendance
à un runtime déjà installé ni à l'absence de sockets natives.
