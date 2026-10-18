# Avancement NoteTaker 0.2 — qualité en évaluation

Dernier lot : **0.2.1.dev0, annuaire municipal sans biométrie, étape 1**.
Le dossier compilé est `dist/directory-01/NoteTaker`. Bilan détaillé :
`directory-stage1.md`. Les étapes 2–6 attendent la validation de cette interface.

Mise à jour du 18 octobre 2026 (comparaison naturelle exécutée le 16 octobre).
**Le test réel 0.1 a échoué ; le problème global n'est pas
déclaré résolu.** L'audit a précédé les modifications des moteurs. Référence :
`audit-0.2.md`. L'ancien état est conservé dans `history/progress-0.1.md`.

## Référence réelle

Débat télévisé français de 50 min 54,733 s, environ six voix annoncées. Une
prise micro cochée de 9,899 s précède le MP3 dans la séance ; comparaison sur
la même dérivation de 51 min 4,632 s, sans la retirer artificiellement.

| Mesure 0.1 observée | Valeur |
|---|---|
| Identifiants / tours sherpa | 195 / 576 |
| Passages Whisper / incertains | 1 485 / 506 |
| Identifiants avec moins de 5 s attribuées | 61 |
| Caractères U+FFFD déjà perdus avant PDF | 1 734 |
| Brouillon / PDF | 88 404 caractères / 54 pages |
| Alertes de vérification | 29 |

L'instantané de la base et les sorties privées sont dans
`output/quality-02/baseline`. Statistiques : `evidence/quality-02-baseline.json`.
Le MP3 importé est identique à l'original selon SHA-256 ; aucune séance initiale
n'a été remplacée pour la recette.

## Corrections développées

- IPC JSON ASCII sans perte et décodage strict ; nouvelle transcription requise
  pour les textes historiques corrompus, sans substitution heuristique.
- Embeddings propres suffisamment longs, regroupement global sans nombre imposé,
  diagnostic de durée/segments courts/incertains et comparaison WeSpeaker/ERes2Net.
- Conservation des mots Whisper et alignement lors des changements de voix.
- Synthèse Qwen hiérarchique : blocs avec contexte partagé, informations sourcées,
  contrôle des citations/intervenants, seconde vérification et regroupement des
  sujets réellement abordés. Les décisions/actions rapportées restent à confirmer.
- Trois cadres explicites : transcription intégrale, compte rendu synthétique,
  projet de PV municipal avec relecture par le secrétaire.
- Noto Sans OFL embarqué et incorporé, couverture, pagination, sections espacées,
  références accessibles dans l'éditeur plutôt qu'imprimées intégralement.
- Signal de scrutin fondé sur des formulations procédurales ; les mots « voix »,
  « contre » ou « vote » seuls ne créent pas d'alerte ni d'objet vote.
- Fusion, scission et noms conservés ; restauration des transcriptions/corrections
  antérieures depuis l'interface. Un nouveau traitement ne supprime pas l'historique.

## Validations réelles à ce stade

La suite de **86 tests** a réussi, y compris restauration des corrections de
brouillons, refus des textes corrompus, protocole Unicode et polices incorporées.
Le rapport final est `evidence/pytest-quality02.xml`.

La nouvelle transcription complète produit **1 485 segments, 12 216 mots** et
**zéro U+FFFD**. Temps mural du rapport : 1 369,168 s. Les mots ne constituent pas
une référence humaine ; WER non mesuré.

L'alignement corrige aussi les élisions françaises et les mots de durée nulle :
2 350 passages deviennent 1 822, avec 644 unités de citation au lieu de 1 172.
Les caractères hors espaces et les neuf groupes sont conservés. Les 148
passages avec timing déduit restent incertains ; il reste 894 passages incertains.
Ces compteurs sur des passages redécoupés ne prouvent pas une amélioration de
précision. Preuve : `evidence/quality-02-word-alignment.json`.

Les mêmes 619 fenêtres propres longues ont été regroupées avec plusieurs seuils
et les deux embeddings. La liaison complète WeSpeaker à 0,4 produit **neuf
groupes sans nombre imposé** ; d'autres réglages descendent jusqu'à un groupe,
ce qui illustre le risque de sur-fusion. Le profil reste expérimental.
La chaîne native complète a aussi été exécutée (573,678 s), puis la géométrie
de confiance a été étudiée sur ses mêmes observations, sans réextraire des
vecteurs différents. Rapports : `evidence/quality-02-speakers*.json`.

Des fenêtres courtes, chevauchées ou ambiguës restent non attribuées et de
nombreuses attributions sont incertaines. La diminution des groupes ne suffit
pas à prouver une meilleure précision. Les durées par groupe peuvent compter
des plages simultanées ; ce ne sont pas des temps de parole de référence.

Le dernier bundle a été reconstruit avec le modèle Instruct sélectionné et
les corrections d'alignement. La recette compilée du 18 octobre a révélé des
références répétées : la validation JSON arrêtait le traitement avant la passe
de réparation. Cette sortie échouée est conservée dans
`evidence/bundle-quality02-before-schema-fix.json`. Le contrôle d'unicité reste
obligatoire à l'issue de la réparation par un véritable appel Qwen ; le schéma
intermédiaire laisse désormais les doublons atteindre cette passe. Un test de
régression couvre ce chemin. La recette finale et ses empreintes sont dans
`bundle-quality02.json` et `desktop-quality02.json`.

La nouvelle recette compilée réussit ensuite les **trois moteurs CPU réels**
(ASR, sherpa, Qwen), avec protocole français sans perte et environnement Python
retiré du PATH. Le cas Qwen exerce effectivement la réparation des doublons,
puis conserve ses deux informations une seule fois. L'interface compilée
démarre, répond et se ferme normalement avec une base isolée. Le lot mesure
3 559 987 654 octets avant compression. Le poste possède des runtimes installés
et reste connecté : ces contrôles ne valent pas recette Windows vierge hors ligne.
Le résultat naturel complet du 16 octobre précède cette correction ciblée de
schéma du 18 ; sa fidélité n'est pas déclarée revalidée par la fixture compilée.

Ces réussites attestent l'exécution, pas l'exactitude sémantique. Sur la fixture
compilée, Qwen a rattaché un budget global de travaux à la seule toiture, sans
appui suffisant ; son vérificateur l'a accepté. Un contrôle plus strict a rejeté
ce glissement mais aussi une paraphrase fidèle, donc n'a pas été intégré sur
la base de ce seul essai (`evidence/quality-02-verifier.json`). Cette erreur
connue confirme la nécessité de relire les sources et la limite du même modèle
employé pour générer et vérifier.

Les PDF Unicode de contrôle ont été rendus avec Poppler et inspectés ; le DOCX
avec ses TTF a été ouvert/rendu en lecture seule par Word, source inchangée.
Accents, œ, apostrophes et euro lisibles, sans carrés noirs sur ces contrôles.
Word reste un outil de QA et n'est pas requis sur le poste utilisateur.
Les deux formats refusent les glyphes absents de la police embarquée avant de
remplacer le fichier de destination ; ce refus a été testé sur chaque format.

La première synthèse complète 0.2 est **rejetée** malgré une chaîne exécutée
jusqu'aux aperçus PDF/DOCX. Elle donne huit sujets, 1 006 caractères et deux pages,
mais ne retient que les huit premières informations sur 31 : ses sources
s'arrêtent à 708,060 s dans un fichier de 3 064,632 s. Le vérificateur a aussi
accepté une causalité ajoutée et une question créée. La réduction de 54 à deux
pages ne constitue donc pas une réussite. Rapport `evidence/quality-02-comparison.json`.
Les deux pages PDF et les deux pages rendues par Word ont été inspectées :
glyphes et mise en page lisibles, fidélité et couverture insuffisantes.

Un contrôle refuse désormais le regroupement global s'il omet ou répète une
information vérifiée. Il ne mesure pas la couverture humaine des sujets.
La comparaison complète de Qwen3-4B-Instruct-2507 est **exécutée**, séparée dans
`output/quality-02/instruct-2507`. Il est sélectionné pour le développement,
avec sa quantification Unsloth et sa provenance figées au manifeste. Le bundle
embarque seulement ces nouveaux poids LLM ; les anciens restent conservés hors
de ce lot. Aucun téléchargement au lancement n'est ajouté.

| Mesure sur le même audio | 0.1 | Recette 0.2 Instruct |
|---|---:|---:|
| Groupes vocaux, sans nombre imposé | 195 | 9 |
| Caractères de remplacement U+FFFD dans le texte | 1 734 | 0 |
| Caractères du brouillon synthétique | 88 404 | 6 844 |
| Pages PDF | 54 | 4 |
| Thèmes | 11 points initiaux | 8 |

Les 18 blocs/644 unités sources ont donné 46 informations reformulées, dont
36 retenues par le vérificateur. Les 36 sont affectées exactement une fois aux
huit thèmes, sans omission interne au regroupement. Le premier regroupement
du candidat omettait onze informations et en répétait une : il a été refusé,
puis réparé par un appel Qwen d'affectation à clés obligatoires. Aucune synthèse
de secours fabriquée n'est substituée au modèle.

Le contrôle automatique trouve zéro information retenue sans citation exacte.
**Ce résultat ne mesure ni la fidélité sémantique ni la couverture des sujets.**
Les sources retenues s'étendent de 78,460 à 2 968,180 s ; cette étendue ne prouve
pas que les sujets intermédiaires soient tous traités. Le vérificateur voit le
contexte proche : il refuse notamment l'unité « établissements » après une
rectification portant sur des personnes et des blocages.

Temps cumulés des appels natifs de synthèse : **3 056,834 s**, soit environ
51 minutes. La dernière reprise de 90,011 s réutilisait les étapes précédentes ;
elle n'est pas le coût d'une synthèse complète. Les calculs étaient concurrents,
donc ces durées ne constituent pas une comparaison de performances isolée.

Rapport complet : `evidence/quality-02-comparison-instruct.json`. Les quatre
pages PDF et les quatre pages du DOCX rendu par Word ont été inspectées :
accents et symboles français lisibles, police incorporée, mise en page lisible.
Le DOCX source est inchangé après QA. Les onglets réels transcription,
brouillon et votes de cette séance isolée ont aussi été rendus et inspectés.

**La qualité professionnelle du compte rendu reste non validée.** Des phrases
restent maladroites, certaines catégories et attributions d'opinions doivent
être corrigées. Les marqueurs de discours rapporté ne couvrent pas tous les
cas. Une citation exacte et l'accord du même LLM ne prouvent pas qu'une
reformulation est fidèle. Aucun résultat de scrutin n'est créé (zéro objet vote).
L'export normal de cette séance est réellement refusé avec
`HUMAN_REVIEW_REQUIRED_FOR_CURRENT_SESSION`. Les fichiers PDF/DOCX sont des
**aperçus techniques non validés** ; aucune relecture humaine n'a été créée.

La séance de recette distincte peut être ouverte avec le lanceur
`scripts/run-quality-review.ps1`. Le MP3 et la séance utilisateur initiale
restent préservés. Les anciennes sorties échouées restent consultables.

## Redistribution native et chantier CPU

L'inventaire final contient 292 fichiers PE ; les deux fichiers Qt Virtual
Keyboard GPL/commerciaux seulement sont exclus et ASIO reste exclu. Le
démarrage réel du bundle réussit. L'audit confirme toutefois que la roue
CTranslate2 active importe directement le frontal NVIDIA `cudnn64_9.dll`,
même pour CPU. Les conditions cuDNN 9.1 empêchent d'approuver en l'état ce lot
pour une cible commerciale générale sans GPU NVIDIA. Les réserves FFmpeg,
Qt/LGPL et Visual C++ restent ouvertes : voir `licenses.md`.

Une DLL CTranslate2 4.6.0 CPU seule a été réellement compilée depuis la révision
amont figée, avec Ruy, sans MKL/OpenMP/CUDA/cuDNN. Ses imports PE ne contiennent
pas de DLL NVIDIA. Sa taille est 7 082 496 octets ; preuve
`evidence/ctranslate2-cpu-build.json`. Elle reste isolée, sans remplacement du
moteur actif ni du bundle. Son import Python réussit (zéro périphérique CUDA,
types CPU float32/int8/int8_float32), mais la transcription de l'extrait naturel
de 30 secondes dépasse **600 secondes** et termine en `TimeoutExpired`.
**Cet essai d'inférence est un échec**, pas une réussite CPU produit. Preuve
`evidence/ctranslate2-cpu-smoke.json`. La variante reste non intégrée ; le
moteur actif est inchangé. Le lanceur d'essai gère désormais les délais et
l'arrêt de son propre arbre de processus, y compris le lanceur de venv Windows.

Aucun compte rendu réel n'a été approuvé automatiquement ; aucune réussite
globale de résumé n'est annoncée.
Les calculs de développement ont été concurrents : leurs durées observées ne
forment pas une comparaison de performances CPU isolée avec l'ancien test.

## Non validé

Référence humaine des voix, WER/DER, couverture thématique et taux d'invention
sémantique : **NON MESURÉS**. Les références/citations et le second passage du
LLM ne remplacent pas une relecture humaine. La réunion municipale naturelle,
capture longue, bruit/chevauchements avec vérité terrain, GPU, minima matériels,
Windows vierge déconnecté et installateur commercial signé restent non validés.
Les réserves de redistribution native restent dans `licenses.md`.

Procédure et conventions : `benchmark-0.2.md`. Le produit reste en développement.

L'utilisateur a confirmé ne pas disposer d'extraits annotés de référence.
Les scores d'exactitude ne sont donc pas calculés et aucun nombre n'est
substitué à cette absence de vérité terrain.

## Annuaire et références vocales — audit préalable du 18 octobre 2026

La nouvelle demande est cadrée dans `speaker-directory-plan.md`, avant modification
du code applicatif. L'annuaire nominatif interséances n'est pas encore développé.
La collecte d'empreintes nominatives et l'identification restent désactivées/non
implémentées ; aucune personne du débat n'est enrôlée dans cet audit.

Les API sherpa-onnx 1.13.8 installées ont été inspectées et leurs opérations
réellement exécutées sur CPU. WeSpeaker charge en 256 dimensions, ERes2Net en
512 ; les extractions sur tonalité artificielle donnent des vecteurs finis.
Le manager accepte plusieurs embeddings mais les agrège ; son binding expose
`score`, pas `GetBestMatches`. L'ajout, le refus d'un UUID dupliqué, le rejet
d'un vecteur inconnu et le retrait réussissent sur vecteurs artificiels.
Une égalité de scores renvoie quand même un identifiant via `search` : NoteTaker
devra ajouter une garde d'ambiguïté. `is_ready` ne prouve pas la présence de parole.
Rapport : `evidence/speaker-directory-api-audit.json`.

Le plan propose annuaire sans biométrie, coffre/contrôles Windows, enrôlement
CPU puis suggestions après diarisation libre, sans nombre imposé ni apprentissage
à partir des corrections. Le code de capture/SQLite en clair n'est pas adapté
tel quel aux références biométriques. La validation juridique doit précéder
l'enrôlement lui-même, avec évaluation des articles 6/9 et de l'AIPD par la
collectivité/DPO ; aucune approbation juridique n'est déduite de cette demande.

**Non exécutés/non validés pour cette fonctionnalité :** enrôlement naturel,
coffre et habilitations, purge/restauration, correspondances réelles et benchmark
annoté libre/profils. Les contrôles API artificiels ne mesurent aucune précision.
Les 86 tests de l'application précédente n'ont pas été relancés dans cet audit
sans changement applicatif et ne valident pas la future fonctionnalité.

## Étape 1 de l'annuaire implémentée — 18 octobre 2026

Après validation du plan : annuaire civil, recherche/filtres, fiches modifiables,
archive/réactivation, sélection par séance, présences/procurations et rôles
distincts des fonctions permanentes. Attribution manuelle de la transcription,
instantanés/historique conservés, nouvelle relecture requise après modification.
Assistant vocal grisé sans action ; aucun profil vocal ou traitement nominatif
biométrique ajouté. Les étapes suivantes ne sont pas commencées.

**104 tests réussis**, dont 18 nouveaux contrôles de service et d'interface.
Migration v3 → v4 sur copie isolée de l'instantané réel : valeurs des neuf
tables historiques identiques, 1 485 interventions conservées, sauvegarde et
clés étrangères vérifiées, source inchangée. La base utilisateur active n'a pas
été ouverte en écriture pour cette recette. Les rendus réels de l'annuaire,
des présences et de l'attribution ont été inspectés ; un défaut de synchronisation
de l'éditeur a été corrigé et couvert. Les deux pages de chaque export de test
PDF/DOCX sont également inspectées, DOCX rendu par Word en lecture seule.

Le nouveau lot **`dist/directory-01/NoteTaker`** démarre/se ferme normalement ;
les trois workers compilés passent leurs contrôles CPU. Le lot antérieur est
conservé. Rapports : `pytest-directory.xml`, `directory-ui.json`,
`directory-legacy-migration.json`, `desktop-directory.json`,
`bundle-directory.json` et `native-payload-directory.json` dans `evidence`.

Recette sur le poste de développement connecté, pas sur Windows vierge hors
ligne. Ergonomie à valider par les agents ; aucun Setup commercial produit.
La base civile reste sous les permissions Windows, sans coffre chiffré ni
habilitations avancées ; le lot 2 n'est pas commencé. Les limites précédentes
des moteurs et de redistribution restent ouvertes. Voir `directory-stage1.md`.
