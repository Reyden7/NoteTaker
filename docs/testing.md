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

## Qualité 0.2 après le premier test réel

L'audit et les premières mesures sont dans `audit-0.2.md` et `progress.md`.
La suite a atteint **86 tests réussis**, dont conservation/restauration des
corrections, pas de limite à six voix, normalisation des vecteurs, observations
insuffisantes non créatrices d'identités, alignement des mots, faux signaux de
scrutin, citations/intervenants, unités sources compactes, protocole JSON ASCII,
refus des textes perdus U+FFFD et fontes PDF/DOCX réellement incorporées.
Rapport : `evidence/pytest-quality02.xml`.

La procédure de comparaison réelle est `benchmark-0.2.md`. Les modèles tournent
réellement sur le débat ; aucune sortie de test injectée n'est présentée comme
une réussite d'inférence. Les essais de prompts échoués restent conservés dans
les dossiers privés de recette et sont distingués des résultats finaux.
Les aperçus techniques ne créent pas de relecture humaine ni d'export approuvé.

La comparaison naturelle complète Instruct est consignée dans
`evidence/quality-02-comparison-instruct.json`. Toutes les 36 informations
retenues sont affectées une fois aux huit thèmes. L'existence des citations
est contrôlée automatiquement ; la fidélité, WER/DER, couverture et taux
d'invention restent non mesurés sans référence humaine. Les quatre pages PDF
et les quatre pages du rendu Word ont été inspectées. Les onglets réels de
la séance de recette ont été rendus et inspectés le 18 octobre.

La dernière recette compilée utilise les commandes `--bundle`/`--report`
de `../packaging/README.md`. Le premier contrôle du 18 octobre a révélé un
doublon rejeté par le schéma avant réparation. Le test de régression avec
réponses de modèle explicitement simulées vérifie que la véritable passe
d'affectation est atteinte ; la recette compilée rejoue des appels Qwen réels.
La preuve de cet échec reste `evidence/bundle-quality02-before-schema-fix.json`.

`scripts/build_cpu_runtime.py` compile réellement une variante CTranslate2
CPU isolée. `scripts/validate_cpu_runtime.py` teste l'import puis 30 secondes
de voix naturelles (600–630 s de l'audio de comparaison). Il conserve stdout,
stderr et preuve distincte ; aucune substitution au moteur actif n'en découle.
Un import réussi ou un inventaire sans DLL NVIDIA ne vaut pas réussite de
transcription ni qualification sur Windows vierge. L'essai réel du 18 octobre
a dépassé le délai de 600 secondes pour cet extrait de 30 secondes ; il est
consigné comme échec dans `evidence/ctranslate2-cpu-smoke.json`, sans intégration.

## Annuaire civil 0.2.1 — étape 1

**104 tests réussis**, dont 14 nouveaux cas de service et quatre tests de widgets.
Rapport `evidence/pytest-directory.xml`. `test_directory.py` couvre annuaire,
filtres/homonymes, concurrence, instantanés, pouvoirs, attribution/restauration,
réanalyse, export municipal et conservation d'une ancienne relecture après
migration. `test_directory_ui.py` couvre formulaires, recherche, archivage,
abandon d'édition, présences/procurations et synchronisation de l'attribution.

Commandes de reproduction, recette de la copie réelle v3, rendu des widgets
Windows et contrôles du nouveau bundle : `directory-stage1.md`. La sonde UI
est `scripts/validate_directory_ui.py` ; ses fiches sont fictives. Les validations
d'export automatisées sont des fixtures, sans approbation de séance réelle.
Le coffre et la biométrie ne sont ni implémentés ni testés dans ce lot.
