# NoteTaker 0.2.2 — corrections humaines et sources

## Cause reproduite

Audit sur copie cohérente SQLite, jamais sur une connexion modifiable à la base
utilisée par l'opérateur. La séance en échec contient 670 passages dont 429
attribués manuellement, cinq groupes et 18 affirmations. Onze affirmations ont
42 citations dont le passage existe et le texte est encore exact, mais dont
`claim.speaker` garde l'ancien UUID alors que `utterance.speaker_id` désigne
désormais une personne de l'annuaire. Aucun vote n'a été ajouté.

L'ancienne interface enregistrait le brouillon contre le contexte courant avant
la relecture. Le contrôle `grounded_claim` rejetait alors le premier désaccord
et ne retournait que `CLAIM_EVIDENCE_INVALID`. Rebattre seulement l'empreinte du
contexte ne pouvait résoudre cette différence. Supprimer les contrôles ou les
affirmations aurait masqué le problème. La modification de prose supprimait
auparavant le champ `claims` : ce comportement est corrigé.

Le correctif conserve les citations et vérifie à nouveau les affirmations à
l'enregistrement strict, à l'approbation et à l'export, y compris pour une
ancienne révision migrée. Un validateur ne modifie plus les citations en place,
afin de ne pas changer implicitement une révision ou son hash de relecture.
Un nom imprimé ancien est également détecté après renommage du même UUID.

## Réparer une séance existante

1. Fermer l'ancien exécutable et conserver une sauvegarde du dossier complet
   des données. Ouvrir `dist/validation-fixes/NoteTaker/NoteTaker.exe` avec le
   même dossier de données. Le schéma reste v4 ; aucune migration supplémentaire
   n'est requise depuis 0.2.1.
2. Ouvrir la séance puis **Projet de procès-verbal**. Utiliser **Contrôler les
   références** : la liste indique le point, l'affirmation, le passage et la
   cause. Ouvrir le point, corriger l'affirmation ou écouter sa source.
3. Si seules les attributions ont changé, cliquer **Actualiser les attributions
   depuis les sources…**, lire la proposition et l'accepter explicitement. Elle
   ne corrige que les affirmations dont toutes les citations valides désignent
   une même voix connue. Une source absente, un texte changé ou plusieurs voix
   restent à traiter individuellement. Les paragraphes rédigés manuellement
   ne sont pas remplacés par cet outil : relire aussi les noms dans cette prose.
4. Avec **Corriger l'affirmation…**, modifier le texte, remplacer/ajouter une
   citation exacte, choisir la personne, prévisualiser puis appliquer. Le choix
   d'une source permet une recherche et affiche son horodatage et son texte.
   La suppression d'une affirmation demande confirmation ; la révision ancienne
   demeure dans l'historique. Supprimer sa dernière affirmation supprime le point.
5. Contrôler les références, relire tout le document, les personnes, décisions
   et votes puis utiliser **J'ai relu cette révision**. Saisir son nom et confirmer.
   Le mode PV municipal exige le rôle de secrétaire. Exporter PDF ou DOCX.

Une révision de travail peut être sauvegardée et rouverte pendant la correction,
avec toutes ses incohérences visibles. Elle n'est jamais réputée relue. Chaque
réparation crée une nouvelle révision sans validation humaine héritée.
La proposition testée sur la copie réelle résout les 42 liens, sur sept points,
sans changer texte des affirmations, citations ou identifiants sources.
La copie conserve zéro approbation créée par le test et l'export y est refusé.

## Segments et voix

Le fractionnement mot par mot au changement de groupe, les mots ponctuels sans
couverture vocale et les limites Whisper/sherpa produisaient beaucoup de courts
fragments. L'audit de la séance corrigée compte 20 passages exclusivement
ponctués, 146 de moins d'une seconde et 471 paires consécutives de même groupe
séparées d'au plus 750 ms. Ces observations expliquent une partie de la gêne
d'édition ; elles ne permettent pas de désigner l'auteur véritable d'une voix.
Les écarts acoustiques et les chevauchements ne sont pas résolus par le seul
regroupement et restent à mesurer avec une annotation humaine.

La nouvelle compaction retire les sorties automatiques vides/non lexicales et
réunit les fragments compatibles d'une même voix connue : même état d'incertitude,
aucun chevauchement signalé, même audio, écart ≤750 ms, durée totale ≤20 s et
texte ≤1 400 caractères. Les sorties ASR brutes restent dans le dossier du job.
Le premier ID et les horaires extrêmes sont conservés, avec provenance et mots
horodatés. Les voix inconnues ne sont jamais réunies par supposition.

Sur les sorties ASR et WeSpeaker déjà calculées du même débat : 1 822→903
passages, 491→237 de moins d'une seconde, neuf groupes dans les deux cas et
égalité des mots lexicaux vérifiée. Aucun recalcul acoustique ni plafonnement
du nombre de voix. WER, DER, faux positifs et exactitude des noms : non mesurés.

Les UUID demeurent internes ; la table affiche « Voix N » et les noms attribués.
Les états inconnue, incertaine et confirmée manuellement sont distincts. Sélection
multiple Ctrl/Maj, confirmation d'une voix sur la sélection, attribution annuaire
individuelle/sélection/groupe et regroupement explicite sont disponibles. Un
regroupement exige des passages consécutifs de même voix, sans chevauchement et
sur le même audio. La lecture audio est accessible directement depuis la sélection.
Le texte long reste lisible dans l'éditeur latéral défilant et les infobulles.

## Réanalyse et historique

Une correction explicite de personne, un nom manuel historique, un texte modifié
ou une scission manuelle protège le passage. Les données originales de la
correction sont réinsérées telles quelles après analyse. Les mots automatiques
extérieurs à la zone protégée restent disponibles si leur alignement est fiable.
Une intersection partielle sans mots horodatés provoque un refus avant écriture.
Les groupes anonymes peuvent reprendre leurs UUID par recouvrement temporel
mutuel suffisamment dominant (75 %, marge 20 %) sur le même montage audio.
Une correspondance ambiguë crée un nouveau groupe ; elle ne propage aucun nom.

Le hash du WAV préparé est comparé à celui référencé par les corrections avant
remplacement. Un changement de prises, de montage ou un ancien audio absent
arrête le remplacement : conserver la séance corrigée et créer au besoin une
séance distincte. Aucun fichier audio n'est effacé par une erreur de moteur.

Scission et regroupement remappent les références par filiation exacte. Une
citation à cheval sur la scission est divisée entre les deux enfants ; une
citation ambiguë ou absente reste signalée, jamais retrouvée par devinette dans
la transcription entière. L'historique conserve la transcription complète et
chaque révision du document. Le remappage est dans la même transaction SQLite
que les segments. Même une coupure au milieu d'un mot peut être réunie sans
ajouter artificiellement un espace si les deux textes n'ont pas été modifiés.
Les anciennes scissions sans instantané complet ne sont pas prétendues restaurables.

## Tests réellement exécutés

- 125 tests pytest sous Windows, dont 21 nouveaux : intégrité des liens,
  proposition explicite, citation modifiée/absente, voix mélangées, noms imprimés,
  sauvegarde d'incohérences, relecture stricte, scission/fusion/citations,
  rollback injecté, migration v3→v4/relecture conservée, préservation manuelle,
  correspondance temporelle ambiguë et widgets de correction/relecture.
- Moteurs CPU réels sur 32,02 s de voix synthétique SAPI locale : création,
  import WAV, Whisper, sherpa, Qwen, attribution fictive A puis B, correction
  explicite des références, scission, regroupement, seconde analyse, régénération,
  refus avant relecture, relecture simulée marquée « AUTOMATED FIXTURE ONLY »,
  export PDF/DOCX et réouverture : succès en 362,143 s. Aucun résultat de vote.
- Première fixture courte : refus réel `NO_SUPPORTED_SUMMARY_CLAIMS` ; aucune
  synthèse forcée. Deuxième essai : fixture SAPI altérée par un script UTF-8
  sans BOM lu sous Windows PowerShell 5.1, également refusé. Le générateur de
  fixture est désormais UTF-8 avec BOM. Ces deux échecs sont conservés dans
  `corrections-real-workers-chain-initial-rejected.json` et
  `corrections-real-workers-chain-encoding-failed.json` dans `docs/evidence`.
  Ce défaut de fixture ne justifiait aucun assouplissement des
  contrôles de synthèse du produit.
- Exports finaux : deux pages PDF et deux pages DOCX rendu par Word en lecture
  seule, toutes inspectées sans coupure de texte ni glyphe manquant ; fichier
  DOCX original inchangé. Word est un outil de QA, pas une dépendance du produit.
- Trois captures des vrais widgets Qt Windows inspectées : transcription longue,
  diagnostic et éditeur d'affirmation. Elles n'approuvent aucune réunion réelle.

Preuves dans `docs/evidence` : `pytest-validation-fixes.xml`,
`validation-fix-real-audit.json`, `segmentation-fix-real-replay.json`,
`corrections-real-workers-chain.json`, `validation-fixes-ui.json`.

## Livraison et limites

Bundle PyInstaller de développement : `dist/validation-fixes/NoteTaker`, version
0.2.2.dev0, modèles locaux et llama CPU inclus, aucun nouveau modèle/dépendance.
Les anciens dossiers sont préservés. Pour limiter le disque de la machine de
build, les modèles du nouveau dossier sont des liens physiques NTFS vérifiés :
des entrées de fichiers ordinaires, copiables avec le dossier complet. Les
garder immuables ; leur contenu est partagé avec les assets locaux de build.

Le démarrage/arrêt de l'interface compilée a réussi avec une base isolée.
Whisper, sherpa et Qwen compilés ont terminé avec succès sur CPU, PATH limité
à System32 et sans PYTHONPATH/PYTHONHOME ; français Unicode conservé.
Ce contrôle des workers compilés est distinct du parcours complet en sources.
Les
preuves des workers compilés et de l'inventaire natif sont
`bundle-validation-fixes.json`, `desktop-validation-fixes.json` et
`native-payload-validation-fixes.json`. L'inventaire comporte 292 fichiers PE,
aucun ASIO/Virtual Keyboard et encore `cudnn64_9.dll` dans la wheel CT2 officielle.
Ce constat ne constitue pas une autorisation de redistribution commerciale.

Ce PC possède des runtimes et n'est pas vierge/déconnecté. Le Setup commercial,
les conditions natives déjà recensées et cette recette finale restent à valider.
Aucun gain de précision vocale ou de fidélité sémantique n'est annoncé sans
référence annotée. Aucune biométrie nominative développée ou activée.
