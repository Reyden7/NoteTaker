# Annuaire municipal 0.2.1 — recette de l'étape 1

18 octobre 2026. Cette étape est implémentée ; la validation ergonomique par les
agents municipaux reste à faire. Les étapes 2–6 ne sont pas commencées.

## Fonctionnement disponible

- Annuaire accessible sans séance : prénom/nom, fonction permanente, commune,
  création, modification, archivage/réactivation, historique, recherche sans
  distinction de casse/accents, filtres commune et statut. Homonymes distincts.
- Participants réutilisables par séance : À renseigner, Présent, Absent, Excusé
  ou Représenté ; rôle de séance séparé de la fonction permanente, mandataire
  et référence/période du pouvoir. Pas de présence déduite de la sélection.
- Refus des doublons, auto-procurations et mandataires absents/non sélectionnés.
  Un mandataire encore référencé ne peut pas être retiré. Aucun quorum, nombre
  de voix ou résultat calculé ; la régularité du pouvoir reste à vérifier.
- Instantanés d'identité/fonction par séance : corriger ou archiver une fiche
  ne réécrit pas les séances existantes. Anciennes notes libres conservées.
- Attribution manuelle d'un passage ou d'une voix à un participant, confirmation
  d'une voix entière, texte conservé, historique restaurable après réanalyse.
  Ni fiche permanente modifiée ni appel IA pour cette opération.
- Présences, rôles et pouvoirs dans les exports municipaux. Nouvelle relecture
  obligatoire après modification des participants ou des attributions.
- Emplacement visuel du futur assistant vocal : bouton grisé sans action.
  Aucun enrôlement, audio de référence, embedding permanent ou reconnaissance
  nominative automatique ajouté. La diarisation anonyme existante est conservée.

L'annuaire civil reste dans la SQLite actuelle, sous les permissions Windows.
Ce n'est pas un coffre chiffré ni un contrôle d'habilitations avancé. Les lots
suivants de protection et de biométrie attendent la validation de cette interface.

## Migration et conservation

Le schéma v4 ajoute `directory_person`, `directory_history` et
`session_participant`. La migration est transactionnelle ; une sauvegarde SQLite
cohérente est créée et contrôlée avant la mise à niveau d'une base existante.
Les procurations ont une clé étrangère composite différée et une validation
métier. Le contexte des séances sans nouveaux participants reste identique,
donc une ancienne relecture valide n'est pas invalidée par la seule migration.

Une copie isolée de l'instantané réel v3 a été migrée : valeurs des neuf tables
historiques identiques avant/après, dont 195 voix, 1 485 interventions, deux prises,
brouillon, export et historique. Sauvegarde créée et clés étrangères vérifiées.
Hash de l'instantané source inchangé ; base utilisateur active non ouverte en
écriture. Preuve : `evidence/directory-legacy-migration.json`.

Un ancien exécutable refuse v4. Un retour arrière doit utiliser une sauvegarde
compatible dans un dossier distinct, application fermée ; ne pas écraser les
travaux effectués avec la nouvelle version. Sauvegarder aussi le dossier audio.

## Tests réellement exécutés

**104 tests réussis**, dont 14 nouveaux cas de service/migration/export et quatre
tests d'interface. Rapport : `evidence/pytest-directory.xml`. Couverture : filtres,
homonymes, champs invalides, concurrence, instantanés entre séances, procurations
invalides sans modification partielle, archivage, attributions/restauration,
réanalyse, ancienne relecture après migration et refus d'export après changement
de présence. Les parcours d'annuaire testés n'appellent aucun worker IA.

Les widgets Qt Windows réels ont été exécutés/rendus sur cinq fiches fictives,
les cinq statuts, une procuration et une attribution manuelle. L'inspection a
révélé une sélection d'éditeur périmée après attribution : correction, test
renforcé et nouveau rendu inspecté. Annuaire, Participants et Transcription
lisibles ; bouton vocal désactivé, aucune relecture créée par la sonde.
Preuve : `evidence/directory-ui.json` et les images privées qui y sont référencées.

Les exports de test PDF/DOCX sont relus automatiquement. Deux pages par format
sont rendues et inspectées (Poppler et Word en lecture seule, source DOCX
inchangée) : présences, pouvoir, rôle et accents lisibles. Ce sont des fixtures
avec relecture de test explicite, pas des séances réelles approuvées. Word reste
un outil de QA, pas une dépendance du produit.

## Build de travail

`dist/directory-01/NoteTaker`, version 0.2.1.dev0 : nouveau dossier PyInstaller
avec dépendances et modèles locaux, sans téléchargement ajouté. Le précédent
lot `dist/quality-02/NoteTaker` est conservé. Les 104 tests passent aussi pendant
le build. L'interface compilée démarre, répond et se ferme normalement sur base
isolée. Les trois workers compilés exécutent ASR, sherpa et Qwen en CPU.
Preuves : `evidence/desktop-directory.json`, `evidence/bundle-directory.json`.
Inventaire natif : 292 fichiers PE, ASIO/Qt Virtual Keyboard absents,
`evidence/native-payload-directory.json`. Aucun nouveau modèle nécessaire.

## Limites de cette recette

Poste de développement connecté, sans qualification Windows vierge hors ligne.
Pas de nouveau benchmark de qualité du débat de 51 minutes. Les réserves
précédentes de redistribution, GPU et qualité sémantique restent ouvertes.
Aucun Setup commercial produit. Le coffre, la rétention, les habilitations,
l'enrôlement et l'identification ne sont pas déclarés implémentés ou validés.

## Reproduire

```powershell
.venv\Scripts\python.exe -m pytest --basetemp=.cache/pytest-directory-local --junitxml=docs/evidence/pytest-directory.xml
.venv\Scripts\python.exe scripts\validate_directory_ui.py
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build.ps1 -Development -DistributionDirectory dist/directory-01
.venv\Scripts\python.exe scripts\validate_bundle.py --bundle dist/directory-01/NoteTaker --report docs/evidence/bundle-directory.json
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_desktop.ps1 -BundleDirectory dist\directory-01\NoteTaker -ReportFile docs\evidence\desktop-directory.json
```

Le build refuse une cible existante ; choisir un nouveau dossier ou utiliser
`rebuild-dev.ps1` après avoir préservé les résultats. La sonde UI génère un nouveau
dossier de fiches fictives, sans modifier les séances de l'utilisateur.
