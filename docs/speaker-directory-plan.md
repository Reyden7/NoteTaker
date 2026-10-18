# Annuaire et références vocales — audit et plan préalable

18 octobre 2026. **Plan proposé, fonctionnalité non implémentée ni activée.**
Aucun changement du code applicatif, de la base des séances ou du bundle dans
cette étape. L'annuaire utilisable sans identification vocale est prioritaire.

## 1. Audit du dépôt et des API installées

Le socle reste Python 3.11/PySide6, SQLite WAL et workers CPU isolés. La capture
PortAudio journalisée et les imports WAV/MP3/M4A existent. Les noms, fusion et
scission actuels concernent une séance ; il n'existe pas de personne permanente,
d'enrôlement, de droits applicatifs, de rétention automatique ou de coffre chiffré.
`docs/privacy.md` décrit encore le fonctionnement actuel sans annuaire vocal.
La SQLite et les journaux PCM actuels sont en clair : ils ne doivent pas recevoir
directement les nouvelles références biométriques.

### sherpa-onnx 1.13.8 réellement présent

| API | Constat | Conséquence |
|---|---|---|
| `SpeakerEmbeddingExtractor` | CPU, `create_stream`, `is_ready`, `compute`, `dim` | Réutiliser l'extracteur déjà employé dans `engines/speaker_refinement.py` |
| Modèle WeSpeaker adapté | 256 dimensions ; SHA-256 `38622d7a9b6f72f612f3371f49e2edb00cb60bdb3c24aa27535ad4a70a88e9a2` | Même modèle pour enrôlement et comparaison |
| ERes2Net initial | 512 dimensions ; SHA-256 `1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b` | Espaces incompatibles ; aucun mélange de vecteurs |
| `SpeakerEmbeddingManager.add(id, vecteurs)` | Agrège les vecteurs en un prototype normalisé | Garder chaque empreinte source dans notre coffre ; manager en mémoire seulement |
| `score(id, vecteur)` | Score de similarité disponible dans le binding installé | Construire classement, marge et diagnostics dans NoteTaker |
| `search(v, seuil)` | Renvoie un seul identifiant ou une chaîne vide | Ne fournit ni score ni règle de rejet par marge |
| `verify`, `remove`, `all_speakers` | Disponibles et exécutés | Contrôle d'une référence, retrait et inventaire en mémoire |
| `GetBestMatches` natif | Existe en C++, absent du binding Python installé | Utiliser `score()` pour chaque profil sélectionné ; aucune nouvelle extension requise |

Les embeddings bruts extraits n'ont pas une norme unitaire garantie. Le manager
normalise son prototype et les requêtes. NoteTaker doit contrôler dimension,
valeurs finies et norme non nulle, puis normaliser chaque référence avant
agrégation pour éviter de pondérer involontairement les voix par leur norme.
Le seuil de distance de clustering 0,4 ne devient pas un seuil d'identification :
ce sont deux décisions distinctes à calibrer.

Le manager n'apporte ni stockage sécurisé, ni contrôle de qualité audio, ni
anti-usurpation, ni habilitations. `is_ready()` atteste seulement qu'une extraction
est possible. Une tonalité sans parole a suffi à obtenir un embedding lors de
l'audit : ce n'est pas une preuve qu'un échantillon contient une voix exploitable.

Sources figées : [binding Python 1.13.8](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/sherpa-onnx/python/csrc/speaker-embedding-manager.cc),
[implémentation native 1.13.8](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/sherpa-onnx/csrc/speaker-embedding-manager.cc),
[exemple officiel d'identification](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/python-api-examples/speaker-identification.py).
Les licences et restrictions du lot restent celles de `licenses.md` ; cet ajout
ne lève pas les réserves commerciales précédentes et ne requiert aucun poids neuf.

### Contrôles réellement exécutés dans cet audit

Preuve : `evidence/speaker-directory-api-audit.json`.

- Chargement CPU des deux modèles déjà locaux, vérification de leurs hashes et dimensions.
- Stream vide non prêt ; extraction sur une tonalité artificielle de trois secondes,
  vecteurs finis de dimension attendue. Aucun audio de personne enrôlé.
- Vecteurs artificiels : ajout multiple, refus d'identifiant dupliqué, agrégation,
  score, normalisation de requête, recherche connue, rejet d'un vecteur orthogonal,
  vérification et retrait des deux identifiants de fixture.
- Deux scores égaux à environ 0,707 : la recherche native renvoie tout de même
  `fixture-a` avec le seuil de test 0,6. Une garde d'ambiguïté externe est nécessaire.

Ces contrôles ont réussi ; les seuils employés sont uniquement des valeurs de
test mathématique. **Aucune précision, aucun gain de fiabilité et aucune qualité
d'enrôlement sur voix naturelles ne sont mesurés.** La suite applicative n'a pas
été relancée pour cet audit sans changement applicatif ; ses 86 tests précédents
ne sont pas des tests de cette future fonctionnalité.

## 2. Architecture proposée

### Annuaire civil distinct des groupes de séance

Une personne possède un UUID stable, nom, prénom, fonction, commune, statut actif
ou archivé. Le statut vocal est calculé séparément : absent, prise à contrôler,
référence technique non qualifiée, utilisable sous autorisation, expiré,
incompatible ou révoqué. Plusieurs mandats/communes ne sont pas déduits d'un nom.
Un homonyme n'est jamais fusionné automatiquement.

Créer un `DirectoryStore` et un répertoire protégé séparés des données techniques
de séance. Les champs personnels et objets vocaux sont chiffrés ; seuls les UUID
et métadonnées minimales nécessaires restent indexables. Une migration additive
de la base des séances ajoutera sélection des participants et liens d'attribution.
Les liens entre les deux bases sont contrôlés par le service ; il n'existe pas de
clé étrangère SQLite automatique entre deux fichiers indépendants.

Un groupe `speaker_7` demeure un groupe acoustique de séance. Une attribution
contient séparément : UUID du groupe, UUID de personne éventuel, origine manuelle
ou suggestion, scores/marge, version des références et statut à confirmer ou
confirmé. Renommer l'annuaire ne réécrit pas silencieusement les anciens PV.
Une suppression d'identité ne doit pas casser l'ouverture de ces séances.

L'annuaire ordinaire permet de sélectionner une personne et de lui attribuer
manuellement des passages **sans collecter de référence biométrique nominative**.
La diarisation actuelle reste disponible. Les vecteurs acoustiques temporaires
qu'elle utilise ne deviennent pas un annuaire interséances.

### Découpage proposé, sans remplacer le pipeline existant

- `services/directory.py` : annuaire, sélection des participants, archivage/suppression.
- `infrastructure/identity_vault.py` : protection locale, identités Windows, coffre,
  autorisations et purge ; aucune clé dans SQLite en clair.
- `services/voice_enrollment.py` et dialogue PySide6 : prises, import, écoute,
  contrôle, validation et versions des références.
- `engines/speaker_identification.py` : comparaison CPU et rejet, sans modifier
  le nombre de groupes ni leurs frontières.
- Worker dédié : extraction/comparaison dans l'isolation déjà en place, avec
  délais et annulation ; pas de noms ou vecteurs en clair dans les fichiers JSON.
- Extensions ciblées de l'éditeur et du contexte de relecture des séances.

## 3. Assistant d'enrôlement

1. Vérifier habilitation et validation juridique avant de capturer, importer ou
   extraire une référence destinée à l'identification ; une simple option UI ne suffit pas.
2. Proposer un texte français neutre, sans opinions politiques, à lire naturellement.
   Cible : **30–60 secondes de parole exploitable**, en plusieurs prises possibles,
   avec compteur distinct du temps total enregistré. Ne pas forcer une lecture rapide.
3. Réutiliser sélection du microphone, import local et lecteur existants. Préserver
   l'original importé ; seule sa copie dans le coffre appartient à NoteTaker.
4. Mesurer durée VAD, silences, écrêtage/saturation, énergie et estimation prudente
   du bruit. Demander de reprendre si insuffisant ; ne pas confondre un SNR estimé
   avec une mesure de référence ni appliquer un débruitage agressif par défaut.
5. Exclure les chevauchements possibles, rechercher les changements de voix avec
   sherpa et signaler les prises suspectes. Un seul cluster ne prouve pas une
   seule personne ; écoute et confirmation de l'opérateur restent requises.
6. Extraire plusieurs fenêtres propres et non redondantes, par exemple 4–8 secondes,
   sur plusieurs prises lorsque possible. Ces durées sont un point de départ à
   évaluer, pas un seuil de qualité déjà validé. Détecter les empreintes aberrantes
   sans supprimer silencieusement une prise litigieuse.
7. Conserver chaque vecteur et ses paramètres, qualité, prise source et dates dans
   le coffre. Reconstruire le prototype en mémoire. Réécouter, annuler ou recommencer.

Les journaux PCM de capture actuelle sont en clair. L'enrôlement nécessite un
sink de capture chiffré par blocs et récupérable, avec déchiffrement en mémoire
pour la lecture/extraction, avant toute collecte réelle. Ne pas laisser une
copie `normalized.wav`, un cache de lecteur ou une requête worker contenant les
empreintes dans les dossiers de jobs ordinaires. Les limites mémoire et la
récupération de ces blocs devront être testées sur CPU.

### Compatibilité des références

L'identité technique comprend SHA-256 du modèle ONNX adapté, famille, dimension,
prétraitement 16 kHz, paramètres des fenêtres, normalisation et version de schéma.
Même dimension ne signifie pas compatibilité. Un changement non explicitement
qualifié rend les références incompatibles ; il bloque leur utilisation et
demande un nouvel enrôlement. Aucune conversion arbitraire 512 → 256. Une
réextraction d'anciennes prises ne serait permise que sous autorisation encore
valide, conservation autorisée et action explicite, jamais à partir des corrections.

## 4. Reconnaissance facultative et validation

Le chemin proposé est : **diarisation libre inchangée → observations propres →
comparaison avec les seuls profils sélectionnés et autorisés → suggestions →
confirmation humaine**. Ni le nombre de profils ni la liste des présents ne
fixent le nombre de groupes. Un invité hors annuaire doit pouvoir rester inconnu.

Le manager indexe des UUID, sans noms civils. Pour chaque observation assez
longue et propre, obtenir les scores des profils sélectionnés via `score()`.
La décision combine seuil absolu, marge entre les deux meilleurs candidats,
cohérence de plusieurs fenêtres et qualité audio. Un groupe hétérogène ou des
observations contradictoires doivent rester à contrôler, pas recevoir un nom
unique imposé par majorité. Un score cosinus n'est pas une probabilité.

Court, chevauché, bruité, marge insuffisante, modèle incompatible, référence
expirée ou absence de calibration : rejet ou indication à vérifier, **sans nom
attribué automatiquement**. Un unique profil sélectionné n'est pas une preuve
d'identité ; le rejet des inconnus doit aussi être qualifié dans ce cas.
Les seuils sont versionnés et calibrables par un administrateur habilité sur un
corpus distinct de la recette. Au premier lot, les correspondances restent des
suggestions à confirmer, même avec un score élevé.

L'opérateur peut confirmer, remplacer, enlever un lien nominatif, fusionner des
groupes ou dissocier certains passages dans une nouvelle voix. Ne pas faire
réapparaître un lien rejeté lors d'une reprise. Chaque correction invalide la
relecture du brouillon concerné et conserve l'historique, sans apprentissage ni
modification des empreintes permanentes. Un nouvel enrôlement est une action
séparée, habilitée et explicite.

Un échec du coffre ou du moteur d'identification conserve l'audio, la transcription,
la diarisation libre et les corrections ; l'erreur reste visible. Aucun repli
sur des noms devinés ni sur un service externe.

## 5. Sécurité, gouvernance et RGPD

### Verrou préalable

L'enrôlement nominatif et l'identification sont désactivés par défaut, avec une
garde dans les services et workers en plus de l'interface. Leur ouverture exige
une habilitation administrative et une décision juridique documentée de la
collectivité : périmètre/finalité, références du dossier, date, décideur habilité,
avis DPO, conditions et échéance de réexamen. Un clic dans NoteTaker n'est ni une
validation de licéité ni une autorisation de la CNIL. Retrait/révocation bloque
immédiatement les usages suivants et vide l'index en mémoire.

Les empreintes destinées à identifier durablement une personne nécessitent une
analyse au titre des articles 4(14), 6 et 9 du RGPD. Le dossier doit identifier
la base de l'article 6 **et** l'exception pertinente de l'article 9 ; la mission
publique ne suffit pas à présumer celle-ci. Le consentement explicite ne doit
pas être présumé libre ou nécessairement adapté au contexte d'une collectivité.
Évaluer nécessité, proportionnalité et alternative manuelle ; documenter
l'obligation éventuelle d'AIPD avant traitement. Une prise publique ou un débat
autorisé pour transcription ne vaut pas automatiquement autorisation d'enrôlement.

Le règlement type CNIL sur la biométrie au travail concerne le contrôle d'accès ;
il ne doit pas être présenté comme une autorisation de ce nouvel usage.
Le responsable de traitement et le DPO doivent évaluer ce cas précis, avec la
consultation préalable prévue à l'article 36 si un risque résiduel élevé l'exige.

### Protection locale proposée

- Windows DPAPI en portée **utilisateur**, sans `CRYPTPROTECT_LOCAL_MACHINE`,
  et ACL restrictives du coffre ; contrôle de l'identité Windows avant accès.
  Protéger aussi annuaire personnel, prises, embeddings, journaux et sauvegardes.
- Habilitations distinctes : administrer la politique/les droits, enrôler ou
  supprimer, exploiter les suggestions autorisées, consulter les journaux.
  Un rôle enregistré dans une SQLite modifiable ne suffit pas : privilégier les
  comptes/groupes Windows et une frontière de sécurité vérifiée. Des utilisateurs
  partageant un même compte Windows ne sont pas isolés par DPAPI.
- Premier périmètre : coffre par compte Windows habilité. DPAPI n'est pas un
  partage transparent entre agents ; un coffre commun impliquerait une gestion
  de clés et de droits distincte à concevoir avant toute promesse multiutilisateur.
  Ne pas promettre la protection contre un administrateur local ou un malware
  exécuté dans le même contexte utilisateur.
- Aucun déchiffrement en fichier temporaire ; mémoire des workers limitée et
  processus détruits après usage. Auditer aussi caches, crash dumps et swap ;
  BitLocker est une mesure du poste, pas une propriété supposée de l'application.
- Conservation configurable par catégorie : prises de référence, empreintes,
  suggestions et journaux. Pas de durée indéfinie par défaut ; une configuration
  validée est nécessaire avant collecte. L'archivage exclut le profil des recherches,
  sans se substituer à l'effacement ou à l'expiration.
- Suppression : retrait immédiat des index, purge des fichiers/applications de
  référence et caches maîtrisés, WAL/journaux inclus dans l'étude ; restauration
  bloquée pour profils expirés ou révoqués. Définir aussi cycle des sauvegardes
  et registre de suppressions. Ne pas promettre un effacement physique garanti
  sur SSD ni l'effacement automatique des originaux hors coffre ou de sauvegardes
  externes. Les documents historiques relèvent de leur propre politique de conservation.
- Journaliser acteur, opération, UUID, date et code de résultat ; ni audio, ni
  vecteurs, ni texte nominatif. L'intégrité et l'accès du journal doivent être
  testés, sans prétendre à une inviolabilité face à l'administrateur du poste.

Le dossier DPO prévu comprendra cartographie des flux, registre, information des
personnes et exercice des droits, analyse de nécessité et alternatives, matrice
d'accès, conservation/purge/sauvegarde, risques d'erreur/usurpation, mesures de
sécurité, trame AIPD et décisions motivées. Ce sera une aide à l'évaluation,
pas un certificat de conformité ni une licéité déduite du fonctionnement hors ligne.

Sources : [RGPD, notamment articles 4, 6, 9, 25, 32, 35 et 36](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32016R0679),
[CNIL, AIPD](https://www.cnil.fr/fr/RGPD-analyse-impact-protection-des-donnees-aipd),
[CNIL, champ du règlement type biométrie](https://www.cnil.fr/fr/question-reponses-sur-le-reglement-type-biometrie),
[Microsoft, portée et limites DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).

## 6. Ordre d'intégration et critères de passage

| Lot | Livraison prévue | Contrôles avant passage au lot suivant |
|---|---|---|
| A — Annuaire sans biométrie | CRUD, archive/suppression, sélection par séance, liens manuels ; garde désactivée | Migrations, homonymes, droits, historique, suppression sans séance cassée, relecture invalidée, absence d'appels biométriques |
| B — Coffre et politique | Protection Windows, rôles, rétention, révocation, récupération ; documentation DPO | Autre compte refusé, contexte autorisé accepté, altération détectée, aucune donnée vocale en clair, crash/backup/restore/purge ; garde vérifiée dans service et worker |
| C — Enrôlement CPU | Assistant, prises/import/écoute, qualité, plusieurs embeddings versionnés | Silence, saturation, bruit contrôlé, plusieurs voix, court/chevauchement, modèle changé, annulation/crash ; vrais contrôles audio après cadre juridique |
| D — Suggestions en séance | Reconnaissance après diarisation, rejet, confirmation/correction/dissociation | Inconnu, égalité/marge, profil unique, profil non sélectionné/archivé/expiré, groupe mélangé, aucune réécriture des références, audio préservé sur erreur |
| E — Recette comparative et livraison | Benchmark annoté, performances CPU, tests bundle et Windows hors ligne | Corpus indépendant, mesures ci-dessous ; protections du coffre et absence de téléchargement dans le bundle, Windows vierge, notices exactes |

La documentation de confidentialité actuelle sera révisée avec l'implémentation,
en distinguant la diarisation libre du mode biométrique optionnel. Le cahier
des charges utilisateur remplace sa restriction historique contre tout annuaire
vocal, mais ne vaut pas validation juridique d'une collectivité particulière.

## 7. Benchmark à préparer, résultats non mesurés

Sur le même audio autorisé, figer ASR, frontières/groupes de diarisation,
modèle, configuration et hashes. Comparer la diarisation libre avec attribution
manuelle à la même diarisation suivie des suggestions des profils sélectionnés ;
garder les prises d'enrôlement séparées du test.
Un extrait utilisé pour enrôler n'est pas une donnée indépendante de recette.
Séparer aussi calibration des seuils et corpus de mesure ; varier séances,
microphones, bruit et conditions plutôt que multiplier les fenêtres corrélées.

Référence humaine requise : personne réelle par plage, inconnus/hors annuaire,
chevauchements et zones indécidables. Mesurer séparément :

- précision des attributions nominatives proposées et confirmées, couverture
  des propositions et taux de rejet ; ne pas gagner en précision en masquant
  une couverture devenue presque nulle ;
- faux positifs sur inconnus, fausses attributions entre personnes connues,
  faux rejets de connues ; détailler numérateurs/dénominateurs et unités
  (fenêtres/groupes/temps), sans appeler une simple proportion « probabilité » ;
- cas courts, chevauchés et bruités, homonymes et voix proches, un seul profil,
  personne présente non sélectionnée ;
- DER de diarisation avec règles explicites pour chevauchement/collar, séparé
  des erreurs d'identité : une couche de noms après clustering ne prouve pas
  une amélioration des frontières acoustiques ;
- temps CPU, mémoire, temps de correction opérateur et concordance finale.

Les enregistrements disponibles n'ont actuellement ni référence humaine annotée
ni prises d'enrôlement dédiées sous le nouveau cadre. Le débat de 51 minutes
reste une recette de diarisation/transcription et ne sera pas transformé
automatiquement en base nominative. Les tests logiciels utiliseront des données
artificielles clairement identifiées ; aucun gain de reconnaissance réelle ne
sera annoncé avant le benchmark humain autorisé et documenté.
