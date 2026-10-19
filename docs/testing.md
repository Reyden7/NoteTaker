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

## Corrections 0.2.2

125 tests réussis (21 nouveaux), rapport `evidence/pytest-validation-fixes.xml`.
`test_evidence_corrections.py` couvre incohérences d'attribution/citations,
réparations explicites, fermeture/réouverture, conservation des historiques,
remappage de scission/fusion, rollback après échec de stockage, migration avec
relecture préservée et protection des corrections humaines. `test_evidence_ui.py`
teste les vrais widgets : diagnostic avant demande du nom de relecteur,
correction d'affirmation, prose gardant les contrôles et relecture après réparation.

```powershell
.venv\Scripts\python.exe -m pytest --basetemp=.cache/pytest-corrections-new --junitxml=docs/evidence/pytest-validation-fixes.xml
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\create_corrections_fixture.ps1
.venv\Scripts\python.exe scripts\validate_corrections_chain.py
.venv\Scripts\python.exe scripts\render_validation_fixes.py
```

Le générateur exige une voix française SAPI installée, et refuse d'écraser la
fixture existante. Le script est UTF-8 avec BOM pour Windows PowerShell 5.1.
Le parcours n'accepte aucun audio utilisateur : seule la fixture synthétique
connue peut recevoir la relecture automatisée explicitement marquée. Les moteurs
CPU sont réellement appelés, sans simulation d'inférence. Le rapport consigne
aussi les échecs ; succès final en 362,143 s, PDF/DOCX et réouverture compris.
La qualité de diarisation/semantique sur voix naturelles n'est pas mesurée.

`audit_corrections_copy.py --snapshot <copie.sqlite3> --session <UUID>` ouvre la
source en lecture seule puis travaille dans une nouvelle copie isolée sous
`output`. Il ne crée jamais de relecture. Ne pas confondre cette preuve de
cohérence des références avec une validation humaine de la fidélité du résumé.
Les captures Qt, pages d'export rendues et données privées ne sont pas livrées
dans le bundle. Les commandes de contrôle de l'exécutable sont dans
`../packaging/README.md`. Windows vierge déconnecté reste non validé.

## Synthèse thématique 0.2.3

Rapport des tests rapides : `evidence/pytest-topic-summary.xml`. La suite couvre
la séparation transcription/synthèse, trois profils de longueur, lexique local,
questions/avis rapportés/anecdotes, contraintes de classification du propos,
interdiction d'emprunter un détail au contexte voisin, liens phrase→note→source,
changements de noms et UUID annuaire, scission/fusion, modification humaine,
réouverture et exports PDF/DOCX uniquement après relecture de fixture.

Les widgets testés sont réels ; les résultats d'IA des tests unitaires sont
explicitement construits. `topic-verifier-controls.json` consigne sept contrôles
textuels réellement soumis à Qwen CPU. Ils sont écrits pour des erreurs connues,
avec deux contrôles positifs, et ne sont pas une référence humaine annotée du
débat. `topic-classification-controls.json` vérifie séparément la classification
et la reformulation sur la fixture du worker auparavant refusée.

```powershell
.venv\Scripts\python.exe -m pytest --basetemp=.cache/pytest-topics-new --junitxml=docs/evidence/pytest-topic-summary.xml
.venv\Scripts\python.exe scripts\probe_topic_verifier.py
.venv\Scripts\python.exe scripts\render_topic_ui.py
.venv\Scripts\python.exe scripts\compare_topic_summary.py --snapshot <copie.sqlite3> --session <UUID> --work output/summary-paragraphs/nouvel-essai --length standard
```

Le dernier script lit un instantané en lecture seule, fige les 670 passages du
test retrouvé et appelle les vrais workers Qwen. Aucun nouveau calcul ASR ou
diarisation : les deux rédactions utilisent exactement les mêmes corrections.
Les reprises vérifient l'identité de chaque prompt/schéma/modèle avant cache ;
elles ne constituent pas de nouvelles mesures de performance isolées. Les
premiers refus et essais interrompus restent dans les preuves et dossiers privés.

Après succès de l'inférence, `prepare_topic_review.py` crée une copie isolée pour
relecture et vérifie que l'export de production y reste bloqué sans approbation.
`render_topic_comparison.py` produit un rapport technique distinct, marqué non
validé, avec version archivée, proposition et annexe des citations/horodatages.
Il n'appelle ni `approve` ni l'export normal avec une relecture fabriquée.
Le PDF final doit être rendu et toutes ses pages inspectées avant remise.

Le délai de test du worker LLM compilé est désormais 1 800 secondes : il exerce
plusieurs appels natifs successifs, contrairement à une simple génération.
Whisper et sherpa gardent chacun leur délai de 600 secondes. Le délai d'un appel
llama reste 600 secondes et le produit conserve son délai borné et son annulation.
Les preuves compilées sont `bundle-topic-summary.json`, `desktop-topic-summary.json`
et `native-payload-topic-summary.json`. Elles ne valent pas recette sur Windows
vierge déconnecté ni acceptation commerciale. Aucune biométrie n'est ajoutée.


Contrôles natifs des titres : probe_topic_headings.py teste un titre neutre,
un vote inventé, un budget réaffecté et une affiliation absente. Le modèle seul
a accepté cette dernière erreur. `topic-heading-before-source-guard.json`
conserve ce faux positif ; `topic-heading-controls.json` distingue verdict brut
et refus combiné avec le contrôle lexical des noms. Les quatre cas connus
passent avec les contrôles combinés, sans mesure de généralisation.
Le budget réaffecté à la toiture a aussi passé une vérification native sur
fixture ; ce cas a motivé le refus déterministe des reformulations monétaires
hors clause source littérale. Un tel refus conservateur n’est pas une preuve
que les autres quantités ou les relations restantes sont exactes.

Résultat final du lot : **175 tests réussis**. Comparaison de terrain sur les
670 mêmes passages : 6 paragraphes et 12 phrases sourcées, un sujet refusé
explicitement signalé. Dernière reprise Qwen CPU : 5 appels natifs réellement
exécutés, 212,362 s, autres réponses en cache strict ; aucune performance à
froid ni précision humaine n'en est déduite. Le PDF technique final comporte
8 pages rendues à 110 dpi, toutes inspectées. La copie de relecture préserve
l'historique et refuse l'export normal sans approbation du nouveau brouillon.

Le bundle final a été recompilé avec ces sources. Whisper et sherpa ont été
recalculés ; le dernier contrôle du worker Qwen compilé réutilise 9 réponses
natives à identité vérifiée, 0 nouvel appel. Le calcul compilé frais antérieur
de 352,302 s est dans `bundle-topic-before-stance-guard.json` et précède les
derniers contrôles conservateurs. `scripts/record_topic_release.py` vérifie
les empreintes, l'égalité des modules gelés avec les sources, le guide livré,
les résultats de workers, le PDF inspecté et le refus d'export sans relecture,
puis écrit `evidence/topic-summary-release.json`. Ce contrôle de cohérence ne
remplace ni une référence humaine du débat ni une recette sur PC vierge.

## Registre intermédiaire 0.2.4 (bundle de développement)

Le plan est `information-registry-plan.md`, le contrat détaillé
`information-registry-0.2.4.md`. La suite conserve les tests des anciennes
versions et ajoute inventaire complet/IDs, migration v4→v5 et sauvegarde,
annulation transactionnelle, citations et relations invalides, correction/
approbation/exclusion, concurrence, conservation des refus et variantes,
reprise après erreur, obsolescence, provenance de brouillon, relecture finale,
exports PDF/DOCX de fixtures et réouverture. Les tests UI exercent de vrais
widgets ; leurs réponses IA sont construites, pas des inférences simulées
présentées comme mesures de qualité. Les captures fictives sont dans
`evidence/information-registry-ui.json`.

```powershell
.venv\Scripts\python.exe -m pytest --basetemp=.cache/pytest-registry-new --junitxml=docs/evidence/pytest-information-registry.xml
.venv\Scripts\python.exe scripts\render_registry_ui.py
.venv\Scripts\python.exe scripts\compare_information_registry.py --work output/information-registry/field-670 --prepare-only --resume
.venv\Scripts\python.exe scripts\compare_information_registry.py --work output/information-registry/field-670 --resume
```

Le rejeu natif lit l'instantané figé des 670 passages. La première commande
native prépare une copie persistante du registre ; la seconde rédige depuis
ce registre sans inventer d'approbation. Les points de reprise et réponses
brutes restent privés dans `output`. Ne pas exécuter simultanément deux
rejeux sur le même dossier. Un arrêt volontaire du premier essai a été
consigné avant de séparer classement et reformulation ; son code de retour
ne doit pas être décrit comme une défaillance spontanée du moteur.

Dimensions à comparer :

| Dimension | Compte technique disponible | Qualification nécessaire |
|---|---|---|
| Couverture des thèmes | Classement de toutes les fiches, sources intégrales conservées | Thèmes de référence annotés indépendamment |
| Informations perdues | Fiches sources, résidus, refus, exclusions et omissions de rédaction | Unités de sens attendues et réellement restituées |
| Attributions | Égalité des voix stockées et des sources citées | Identification humaine à l'écoute |
| Inversions de sens | Motifs statiques et verdicts Qwen conservés | Comparaison humaine du propos et du contexte |
| Regroupements | Affectations et graphe de relations consultables | Relations et sujets attendus annotés |
| Rédaction | Paragraphes, longueur, phrases et sources | Jugement humain sur cohérence et fidélité |

Les comptes automatiques ne sont pas des scores pour ces six dimensions.
Une source citée n'est pas une preuve que la phrase la reformule correctement.

Résultats finaux : 226 tests réussis en 8,98 s, après correction du dossier
temporaire de test (première tentative conservée : 151 erreurs de fixture,
accès refusé au dossier temporaire système). Les trois captures Qt actuelles
ont été inspectées. `validate_registry_request.py --bundle
dist/information-registry/NoteTaker` a exercé le vrai worker compilé : trois
appels natifs CPU en 53,732 s, aucune tentative réseau Python, aucun changement
des 670 sources ni des relectures historiques. L'hôte n'était pas déconnecté.
Ce calcul frais précède la correction purement visuelle des horaires absents.
Un second cas vérifie le texte du contexte historique d'une citation rejetée
sans correspondance exacte, après modification de la transcription courante.
Après recompilation, `replay_registry_frozen_check.py` a exercé le worker final
avec trois réponses natives en cache strict, zéro nouvel appel natif. Le
résultat est identique, les algorithmes gelés sont identiques et l'ancien
instantané n'a pas été enregistré à la place du registre courant. Deux captures
supplémentaires sur les 670 passages réels ont été inspectées après correction.

`record_registry_release.py` compare les modules gelés des deux exécutables
aux sources, les empreintes des preuves et les guides livrés. La recette de
démarrage/fermeture et l'inventaire PE sont séparés du contrôle Qwen. La
préparation intégrale a été répartie en trois processus par le harnais de
recette uniquement, avec des réponses natives antérieures en cache strict.
La vérification sémantique demeure partielle, demandée par fiche ; toute
information non vérifiée reste hors rédaction automatique.

Rejeu de rédaction achevé : 46 appels natifs, 1 996,973 s, cinq paragraphes,
neuf fiches reprises, export sans relecture refusé. Les 670 lignes et les
anciennes versions restent inchangées. L'examen du texte a révélé des
regroupements erronés malgré les contrôles machine ; huit fiches ont ensuite
été remises à vérifier, sans approbation. Le brouillon comparatif est donc
conservé avec une provenance obsolète : corriger le registre et régénérer.
Preuves : `information-registry-real-comparison.json` et
`information-registry-post-writing-observations.json`. Ce succès d'exécution
ne vaut pas succès de qualité. Le rapport lisible garde les deux plans, les
comptes, les refus et le texte non approuvé. Les six scores restent non mesurés.
