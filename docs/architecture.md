# Architecture 0.2 en évaluation

## Compte rendu par sujet — 22 octobre 2026

Le parcours par défaut est désormais `Pipeline.automatic_report()` : audio
existant réutilisé, `engines/editorial_report.py` pour le contrat éditorial v5,
paragraphes attribués et rapport de vérification séparé. Le registre et son
parcours de rédaction restent disponibles en mode avancé. Les sections plus
anciennes ci-dessous conservent l'historique des choix ; le registre n'est plus
un prérequis du premier brouillon. Aucune migration SQLite ni modification des
moteurs audio. Les contrôles d'export officiel et de relecture demeurent communs.

Voir [plan et audit](editorial-report-plan.md),
[recette initiale](editorial-report-results.md),
[passe de fidélité v5](editorial-fidelity-audit.md). La fidélité n'est pas validée.
Le contrôle de couverture par sujet/voix et les reprises de formulations
explicites ne créent aucune approbation. Les noms de présentation sont liés
aux mêmes voix par un style versionné ; les anciennes révisions restent lisibles.

## Registre guidé — correctif du 21 octobre 2026

`registry_summary.py` extrait les propositions sous contrat versionné v4 ; les
citations sont résolues vers les mêmes instantanés de transcription. Les sources
restent distinctes. Les propositions machine antérieures sont consultables et
séparées de la rédaction automatique ; les fiches humaines sont protégées.
`services/registry_workflow.py` expose les blocages et bilans communs à la
persistance et à l'interface. JSON optionnel dans les révisions existantes,
sans migration SQL. Contrôles de rédaction et d'export conservés.

Voir [diagnostic et procédure](registry-workflow-fix.md).

## Audio CPU / GPU — 21 octobre 2026

La politique `services/audio_engine.py` et le worker CUDA isolé
`workers/gpu_audio.py` ajoutent Large-v3 + Community-1 au pipeline audio partagé.
Le mode CPU reste Small + sherpa. Réglage local atomique, contrôle CUDA réel,
repli CPU à l'admission automatique et relance explicitement demandée après
échec d'inférence GPU. Aucun moteur de rédaction modifié, aucune migration SQL.
Les tours simultanés standards sont conservés dans les sources ; le texte de
ces zones reste incertain et à attribuer à l'écoute.

Détails, formats, runtime externe et recette : [audio-gpu-integration.md](audio-gpu-integration.md).

## Laboratoire 0.2.5 — synthèse directe par sujet

Le parcours habituel reste celui du registre. Un service distinct
`services/direct_summary.py` n'est accessible qu'avec activation explicite sur
copie marquée. `domain/direct_summary.py` porte les contextes, citations et
inventaires ; `engines/direct_summary.py` rédige par contexte puis réutilise les
phrases dans un plan global. `engines/direct_runtime.py` mesure chaque appel CPU
et contrôle strictement la reprise. `ui/direct_summary.py` présente alertes,
paragraphes, rejets et sources, puis renvoie vers l'éditeur et la relecture.

Le registre SQLite v5 reste intact. Les expériences sont des artefacts locaux
indépendants avec instantanés et empreintes ; la provenance facultative du
brouillon est vérifiée avant approbation/export, en plus des contrôles existants.
Les modifications de séance invalident l'essai. Aucun avis machine ne vaut une
relecture humaine. Voir `direct-summary-0.2.5-plan.md` et `direct-summary-0.2.5.md`.

Le socle Python 3.11, PySide6, SQLite WAL et workers isolés est conservé.
Capture, copie des originaux, journal PCM et normalisation locale ne sont pas
remplacés. L'architecture 0.1 est conservée dans `history/architecture-0.1.md`.

## Registre intermédiaire 0.2.4 (sources)

La préparation du registre et la rédaction sont désormais deux tâches séparées
du même worker Qwen CPU. SQLite v5 ajoute des révisions immuables et leur
instantané intégral de transcription. Inventaire des passages, candidats et
variantes, refus, relations et omissions restent consultables, même après
échec du moteur. Les corrections opérateur sont distinctes des avis machine.
Les sujets sont proposés depuis les sources originales, puis les informations
y sont classées ; les paragraphes partent du registre courant seulement.

Le contexte du brouillon inclut la révision de registre lorsqu'elle existe,
sans changer les empreintes des documents hérités sans registre. La provenance
du nouveau document référence une révision immuable et son empreinte ; une
révision obsolète ne peut pas être approuvée comme courante. Les contrôles de
citations, de sens et de relecture finale restent en place. Aucun changement
des moteurs de transcription ou de voix. Voir `information-registry-0.2.4.md`.

## Chaîne audio et voix

1. Copie vérifiée des imports ou capture journalisée ; dérivation PCM16 mono
   16 kHz sans réécriture des originaux.
2. Whisper small int8 CPU avec VAD Silero local. Les mots et leurs timestamps
   sont désormais conservés par le worker.
3. sherpa-onnx segmentation pyannote 3.0 et premier regroupement ERes2Net global.
   Le modèle natif exclut les chevauchements qu'il détecte pour ses embeddings.
4. `speaker_refinement` construit des fenêtres de quatre secondes et retranche
   le masque de chevauchement possible. Les observations avec au moins deux
   secondes propres peuvent créer un groupe ; les observations courtes ne
   peuvent que rejoindre un prototype compatible ou rester non attribuées.
5. Le profil WeSpeaker emploie des vecteurs normalisés L2, distance cosinus,
   liaison complète à 0,4, sans nombre de voix imposé. Les seuils de confiance
   emploient la dispersion et la séparation des prototypes ; ce ne sont pas
   des probabilités calibrées par une référence humaine.
6. Attribution par couverture des mots, scission lors d'un changement, propagation
   des incertitudes. En l'absence de timestamps de mots historiques, l'alignement
   grossier reste explicitement identifié comme approximatif.

Les identifiants sont globaux sur la séance et déterministes pour un même
résultat, numérotés dans l'ordre des premières observations. Ils ne représentent
pas des identités biométriques reconnues. Les noms restent manuels. Aucun
nombre fixe de participants n'est utilisé pour faire correspondre le test à six.

## Synthèse hiérarchique

`hierarchical_summary` reçoit des citations JSON, échappées contre l'injection
de tokens spéciaux. Les blocs bornés suivent les tours, environ trois minutes
au maximum, avec un tour de contexte commun. Les identifiants d'origine sont
conservés lorsque des textes anormalement longs doivent être fragmentés.

Les passages consécutifs de la même voix connue sont compactés avec leurs
positions exactes dans les sources. Qwen extrait au plus quatre informations
substantielles par bloc : sujet, note préliminaire, type, intervenant et courts
extraits justificatifs. Une passe locale vérifie les citations et l'intervenant ;
un identifiant erroné n'est corrigé que par une citation exacte unique de cette
même voix dans le bloc. Une étape Qwen distincte, sur contexte court, reformule
les citations exactes au style indirect, sans réinjecter la note préliminaire
ni sa catégorie comme des faits. Le thème lui-même n'est pas une preuve.
Cette séparation répond aux copies de
transcription observées lors des premiers essais réels ; les longues copies
restent refusées même si la ponctuation change. Une autre passe Qwen contrôle
l'appui sémantique et rejette contradictions, inférences,
attributions mélangées et résultats de vote. Les sources complètes restent
accessibles dans l'éditeur ; les citations ne surchargent pas le document.
Le contrôle reçoit aussi les tours proches, avec leurs voix séparées, pour
détecter une rectification ou contradiction. Ces tours ne servent pas à emprunter
un fait à une autre personne ni à réparer un chiffre par supposition.

Le regroupement global réunit les mêmes sujets à travers les blocs et conserve
les positions divergentes. Chaque information fournie doit être affectée une
fois ; les omissions et doublons provoquent une passe Qwen d'affectation aux
thèmes existants, avec une clé obligatoire par information. Le contrôle final
refuse encore toute affectation manquante ou inconnue. Le schéma intermédiaire
ne rejette pas les doublons avant cette réparation : la grammaire llama.cpp
ne garantit pas `uniqueItems`. Aucun texte de synthèse n'est fabriqué pour
remplacer une sortie manquante. Les grands contextes restent bornés et peuvent
échouer explicitement ; ce n'est pas une garantie de couverture humaine.
Les affirmations retenues gardent leurs références, leurs extraits et le statut
`supported_not_human_verified`. Les rejetées et étapes intermédiaires restent
dans le job privé, sans être présentées comme des informations établies.

Un contrôle par le même modèle n'est pas une preuve de fidélité. Les décisions
et actions rapportées restent à confirmer ; aucune sortie IA ne crée une
décision métier confirmée, un responsable établi ou un résultat de scrutin.
Les décisions et votes confirmés proviennent exclusivement de l'opérateur.
Les attributions incertaines restent signalées dans la reformulation assemblée.
Les marqueurs explicites de discours rapporté (« vous estimez », « selon lui »…)
déclenchent aussi « opinion rapportée — auteur à confirmer ». Une voix de source
ne prouve pas que la personne défend elle-même la position qu'elle reformule.
Cette détection partielle ne remplace pas la vérification des opinions à l'écoute.

Les appels intermédiaires sont réutilisables seulement pour un prompt, schéma,
configuration et identité locale de fichiers inchangés. Les résultats sont
validés à la relecture du cache. `summary-progress.json` indique l'étape réelle.
Une erreur conserve la transcription et le brouillon antérieur.

## Modes, relecture et export

Le schéma de brouillon ajoute `document_mode` (summary/transcript/municipal),
les informations de génération et les preuves internes de chaque point.
La transcription intégrale ne passe pas par le LLM. La synthèse produit des
reformulations thématiques. Le cadre municipal ajoute séance, présences,
décisions et scrutins ; sa relecture exige une confirmation du rôle de secrétaire.

Tout export de l'interface reste lié aux empreintes du contenu et du contexte.
Modifier texte, voix, prises, décisions ou votes invalide la relecture. Les
aperçus techniques de benchmark sont marqués non validés et ne créent aucune
relecture ni export validé dans la séance.

Noto Sans Regular/Bold, sous OFL, est embarqué et incorporé au PDF et au DOCX.
Le PDF a une couverture, des en-têtes/pieds et une pagination ; il refuse un
glyphe absent. Les identifiants techniques de sources restent dans l'instantané
et l'éditeur. Un texte contenant U+FFFD n'est pas considéré réparé par la police :
la synthèse et l'export normal exigent une nouvelle transcription/correction.

## Persistance et isolation

Les migrations SQLite 1–4 sont transactionnelles ; aucun nouveau serveur ou service.
Avant mise à niveau d'une base existante, une sauvegarde SQLite cohérente et
contrôlée est créée dans `migration-backups`. Le schéma v4 ajoute seulement
`directory_person`, `directory_history` et `session_participant` ; les tables
historiques ne sont pas réécrites. Les procurations utilisent une clé étrangère
composite différée et une validation métier sur le mandataire présent.

`services/directory.py` gère l'annuaire civil, recherche Unicode, versions,
sélection des participants et attributions manuelles. L'annuaire reste dans
la SQLite existante pour cette étape non biométrique ; le coffre séparé prévu
pour de futures références vocales n'est pas développé. Les widgets sont dans
`ui/directory.py`, appelés depuis la fenêtre existante sans changer les cinq
premiers onglets. L'onglet Participants est ajouté après ceux-ci.

Une participation contient une copie de l'identité/fonction, présence, rôle de
séance et pouvoir éventuel. Les changements d'annuaire ne modifient pas les
séances historiques. Le contexte de relecture inclut les participants structurés
seulement s'ils existent, pour conserver les empreintes des anciennes séances.
Une attribution annuaire est une correction explicite d'interventions : UUID
personne et instantané dans `source_json`, nom dans un groupe manuel de séance,
historique restaurable. Les corrections ne déclenchent aucune IA. L'export
municipal conserve les présences structurées et les notes historiques libres.
La restauration de transcription utilise les instantanés edit_history existants.
Restaurer conserve à son tour la version active, y compris corrections, noms et
références audio ; le brouillon requiert ensuite une nouvelle relecture.

Le protocole worker est JSON ASCII sans perte, stdout configuré UTF-8 et lecteur
strict : aucun remplacement silencieux d'octets invalides. La capture demeure
indépendante des moteurs. Délais, annulation et Job Objects sont conservés.

Le profil LLM de développement est Qwen3-4B-Instruct-2507 Q4_K_M (Unsloth),
sans préfixe de raisonnement, sélectionné après la comparaison complète. La
variante initiale demeure archivée hors du nouveau payload ; ne pas embarquer
deux poids de 2,5 Go. Les manifestes restent non approuvés commercialement.

Les poids WeSpeaker dérivés, modèles sélectionnés et polices sont embarqués dans le
bundle de développement séparé `dist/quality-02/NoteTaker`. Le lot commercial,
GPU et Windows propre déconnecté restent à qualifier.

## Références et corrections 0.2.2

`services/evidence.py` centralise le diagnostic des liens point/affirmation/
citation/passage/intervenant. Le contrôle est sans mutation du contenu. Une
révision de travail peut rester incohérente (`allow_invalid=True`, schéma de
base toujours vérifié) pour permettre sauvegarde et réparation ; approbation et
export recontrôlent systématiquement les références et règles métier. Les
empreintes de contexte et de texte restent obligatoires. L'édition de prose
conserve les affirmations structurées. Aucun vote n'est déduit d'une réparation.

La proposition d'actualisation des intervenants est distincte de l'application :
prévisualisation et acceptation explicite avant nouvelle révision sans relecture.
La filiation des scissions/fusions remappe les citations dans la même transaction
SQLite ; un historique complet est conservé. Pas de nouvelle migration : v4.
Une migration v3→v4 avec citations, contexte et relecture a été testée.

`services/transcript.py` compacte prudemment les sorties automatiques et conserve
les passages corrigés humainement pendant une réanalyse. Les coordonnées de
temps sont liées au hash du montage WAV ; désaccord ou intersection non alignable
signifie arrêt avant remplacement. Les UUID anonymes ne sont réutilisés que sur
correspondance temporelle mutuelle dominante ; aucun profil vocal n'est créé.
Les mots horodatés et anciennes sorties de jobs restent disponibles localement.

`ui/evidence.py` fournit diagnostic, choix de sources exactes et correction des
affirmations. La fenêtre existante ajoute sélection multiple, regroupement,
lecture rapide et éditeur défilant. Les UUID de voix sont portés en données Qt,
avec noms/numéros lisibles à l'écran. Détails : `validation-fixes-0.2.2.md`.

## Synthèse thématique 0.2.3

Le worker de synthèse utilise `engines/topic_summary.py` : sélection de citations,
reformulation/classification avec contexte, vérification du soutien sémantique,
catalogue global puis affectation de chaque note par clé obligatoire, rédaction de paragraphes et vérification de
leurs phrases/titres. Les citations et appels llama hors ligne reposent sur les
helpers existants. Des alias remplacent les longs IDs de voix dans les données
de reformulation et de vérification, sans modifier texte source, IDs ni stockage.
Le contexte voisin est compacté par voix en conservant ses IDs et frontières.

`domain/summary.py` gère graphies locales, profils de longueur et gabarits de
phrases à alias. Le point garde ses `claims`/`sources` et peut ajouter `narrative`
avec les liens phrase→affirmations→citations. Une reprise par anaphore exige
la même voix unique que la phrase précédente ; son identifiant est conservé et
contrôlé lors des changements d’attribution. Les contrôles existants sont
conservés ; la cohérence du nouveau rendu et de ses voix est également vérifiée.
Une modification volontaire du paragraphe conserve ses références avec le
statut de modification humaine nécessitant relecture. L'historique garde la
liaison plus fine antérieure. Aucun nouveau texte n'hérite d'une approbation.

Le schéma SQLite reste v4 ; lexique et longueur sont des métadonnées de séance.
Le schéma JSON étend seulement les points avec une propriété facultative ; les
anciens brouillons restent lisibles. Employer la nouvelle version pour les
documents contenant `narrative`, qu'un ancien exécutable peut refuser.
Une liste de passages écartés/incertains conserve leurs coordonnées audio et
permet leur consultation/écoute dans l'interface. Les sorties intermédiaires
restent privées, séparées des modèles redistribuables. Aucun profil biométrique.
