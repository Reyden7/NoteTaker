# Compte rendu automatique — architecture et qualification

**Depuis le 22 octobre**, le parcours par défaut utilise le contrat éditorial v5 :
[audit de fidélité](editorial-fidelity-audit.md). Le
[plan v4](editorial-report-plan.md) et ses [résultats](editorial-report-results.md)
restent archivés. La matrice par sujet/voix est produite avant rédaction ;
les reprises contrôlées restent sourcées et requièrent une relecture humaine.
L’orchestration et les protections décrites ici restent partagées ; les mesures
et le contrat de rédaction ci-dessous décrivent l’archive v3 du 21 octobre.

## Audit et choix

L’annuaire civil et les sélections de participants existent. Aucun système
d’enrôlement permanent n’était actif. L’audit du 18 octobre avait confirmé les
API sherpa `SpeakerEmbeddingExtractor` / `SpeakerEmbeddingManager` : celui-ci
normalise et agrège mais sa recherche seule ne rejette pas les ex æquo.
Le nouvel adaptateur utilise le même extracteur WeSpeaker CPU et une comparaison
cosinus explicite avec prototype moyen normalisé, seuil, marge et concordance
de plusieurs observations. Le nombre de personnes connues ne fixe jamais le
nombre de groupes acoustiques. Whisper et Community-1 ne sont pas réentraînés.

La rédaction existante `Pipeline.generate()` exige un registre courant et ses
informations approuvées. Elle reste disponible en mode avancé. Le nouveau
`Pipeline.automatic_report()` est un chemin distinct de premier brouillon,
sans modifier les règles d’approbation ou d’export du chemin antérieur.

## Services

- `services/automatic_report.py` orchestre les moteurs existants, la réutilisation
  du montage/transcription par hash, la correspondance facultative, Qwen puis
  une nouvelle révision du brouillon. Concurrence contrôlée par empreinte de
  contexte et conservation des anciens brouillons/jobs. Aucun registre modifié.
- `engines/automatic_report.py` traite tous les passages en blocs contextuels
  bornés avec recouvrement (14 000 caractères / 600 secondes). Le format compact
  demande des paragraphes et des identifiants sources : les citations exactes
  sont recopiées par le service depuis les sources, et non régénérées par Qwen.
  Extraction/rédaction par sujet puis un contrôle sémantique groupé par bloc.
  Une seule réécriture ciblée des refus est permise, uniquement depuis leurs
  citations, puis contrôlée. Auteur, nature et sources restent fixés ; les
  variantes initiales et les refus sont conservés. Réemploi des contrôles de sources, modalités,
  identités, propositions et votes ; contrôle supplémentaire des chiffres.
  Les avis Qwen ne sont jamais une référence humaine de qualité.
- Chaque reformulation garde ses affirmations/citations et bindings de voix.
  Une reformulation refusée n’est pas réintroduite comme fait : citation exacte
  utilisable, prudence explicite, refus et omissions dans l’inventaire consultable.
  Aucun vote métier créé, aucune approbation de fiche ou de document créée.
- Cache privé par contexte et version du moteur ; chaque réponse est réutilisée
  seulement après vérification de l’identité exacte prompt/schéma/modèle/binaire
  par `call_json`. Les sorties et historiques antérieurs restent conservés.
  La disponibilité de caches est consignée ; un temps de reprise n’est pas
  présenté comme celui de nouvelles inférences CPU à froid.
  Répertoire raccourci à 24 caractères avec marqueur SHA-256 complet et contrôle
  de collision ; les chemins trop longs pour le binaire Windows sont refusés
  avant lancement. Aucun décalage de source ou d’horodatage pour les raccourcir.
- `services/working_export.py` produit une copie non relue, clairement marquée,
  sans fabriquer de `HumanReview`. Contrôles structurels de citations obligatoires.
  Les exports usuels et leur relecture demeurent inchangés. DOCX/PDF répètent
  la mention non validée dans le pied de page du document de travail.
- `ui/simple_report.py` est la page par défaut ; les widgets avancés existants
  gardent leurs indices et actions. Les corrections sont enregistrées dans les
  révisions habituelles, sans réduire les contrôles de validation officielle.

## Coffre et références

`voice-vault.sqlite3` est séparé de la base des séances : aucune migration des
tables existantes. Blocs PCM, embeddings et politique sont chiffrés avec DPAPI
du **compte Windows courant**, jamais de clé en clair ni d’embedding dans une
requête de génération. Métadonnées techniques minimales (UUID, dates, états)
indexées en clair. Le chiffrement n’empêche pas l’accès par un logiciel déjà
autorisé sous le même compte : ce n’est pas une authentification multiutilisateur
ou une séparation contre un administrateur du poste.

`EncryptedVoiceCapture` écrit une file bornée de blocs chiffrés transactionnels.
Une interruption laisse les blocs complets lisibles et la prise à vérifier.
Pas de journal PCM ou WAV nominatif en clair. L’import décode en mémoire avec
limite de 90 s et ne change pas le fichier fourni. Réécoute PortAudio en mémoire.
Suppression avec `secure_delete`, expiration au lancement / génération ; les
sauvegardes externes, mémoire virtuelle et stockage du poste restent à sécuriser
par la collectivité. DPAPI ne garantit pas l’effacement physique sur SSD.

Le service exige une autorisation datée valide avant collecte, déchiffrement,
extraction ou comparaison. La révocation ne bloque pas la suppression. Les
seuils ne déclenchent aucune identité sans référence de calibration renseignée.
Ce champ consigne des essais externes ; il ne démontre pas qu’ils sont corrects.
La collectivité a confirmé que son cadre juridique n’est pas encore validé et
qu’elle ne dispose pas d’échantillons autorisés distincts : l’option est restée
désactivée dans toutes les recettes municipales, sans personne réellement enrôlée.
Les références lient hash exact ONNX, dimension et prétraitement PCM mono16k.
Pas de mélange d’espaces d’embeddings ni de réentraînement depuis les corrections.
La diarisation, les horaires et les identités humaines de séance sont conservés :
les correspondances enrichissent seulement les propositions du brouillon.

L’extraction de références est actuellement un thread CPU avec annulation aux
frontières de fenêtres ; la segmentation native d’une prise bornée peut retarder
l’annulation. Pas de processus mémoire isolé dédié à l’enrôlement dans ce lot.
Un crash natif de l’extracteur reste donc un risque à qualifier ; les blocs
chiffrés et les séances SQLite restent sur disque.

## Licences vérifiées le 21 octobre 2026

- [WeSpeaker, fiche officielle des poids](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34) : Apache-2.0.
  Réutilisation de l’ONNX adapté déjà acquis, hash
  `38622d7a9b6f72f612f3371f49e2edb00cb60bdb3c24aa27535ad4a70a88e9a2`.
  Conserver licence, provenance et description des métadonnées ajoutées.
- [sherpa 1.13.8](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/LICENSE) : Apache-2.0.
- [Qwen Instruct GGUF local](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF) : Apache-2.0,
  conversion Unsloth conservée dans les notices existantes.
- [Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) : CC-BY-4.0,
  acquisition conditionnée à l’accord amont déjà obtenu. Attribution, licences
  des dépendances et preuves de provenance du lot Windows restent obligatoires.

Ces déclarations ne constituent pas une validation globale de redistribution
commerciale. Voir `licenses.md`, `audio-gpu-licenses.md`, les manifestes et les
notices du lot. Aucun nouveau modèle téléchargé. Analyse de licéité/AIPD et
procédures d’accès à définir avec la collectivité ; la biométrie est une donnée
personnelle d’identification ([CNIL](https://www.cnil.fr/fr/definition/biometrie)).

## Limites de qualification

### Recette municipale réelle du 21 octobre

Preuves : `output/automatic-report-20261021/470f7221d5eb4cd0974963bf81f4e64d/`.
Copie de séance de 336,039 secondes et 36 passages déjà corrigés humainement.
Transcription réutilisée après comparaison de l’audio ; ni Whisper ni
Community-1 relancés. Les noms du brouillon proviennent des attributions
humaines existantes, jamais d’une reconnaissance nominative.

| Essai CPU Qwen | Temps écoulé | Résultat et limites |
| --- | ---: | --- |
| Première version, 4 appels neufs | 919,109 s | 13 citations de repli, aucune reformulation retenue ; résultat insuffisant |
| Contexte long avec citations générées | 512,624 s | JSON tronqué ; échec conservé, aucun brouillon remplacé |
| Format compact, extraction + contrôle neufs | 443,608 s | 189,077 s + 250,155 s d’appels natifs ; 7 candidats, dont plusieurs déformations malgré un contrôle Qwen favorable |
| Réécriture depuis les seules sources | 92,427 s | Extraction/contrôle de base en cache ; deux appels neufs de 50,331 s et 38,941 s |
| Dernier assemblage, règles renforcées | 43,795 s | Extraction, contrôle initial et réécriture en cache ; nouveau contrôle de 40,609 s ; 4 reformulations, 3 citations de repli |

Ces durées sont des temps muraux mesurés, pas du temps CPU cumulé. Aucun essai
à froid complet du contrat final en quatre appels n’est annoncé. Un relevé
ponctuel d’un processus natif a observé un pic de 6 262 382 592 octets ; il ne
qualifie pas le maximum de toute la chaîne ou d’une réunion longue.

Le résultat livré est `delivery-final/` : PDF et DOCX marqués **BROUILLON NON
RELU**, aucune relecture créée, export officiel toujours bloqué. Deux des quatre
reformulations portent une alerte de source faible. **23 passages sur 36 ne
sont pas repris** et restent inventoriés. Ce décompte n’est ni une mesure de
couverture des thèmes ni une preuve de fidélité. Les règles ciblées sur les
erreurs observées ne garantissent pas les formulations inédites ; l’avis du
même Qwen a effectivement laissé passer des inversions de contexte.

Les contrôles SQL comparent intégralement les données conservées (transcription,
annuaire, participants, votes, décisions, historique, registre, anciens brouillons).
Les nouvelles révisions n’ont pas de relecture. WAV et annotations BFMTV ont
les mêmes empreintes que le lot précédent. L’empreinte physique de la base
municipale diffère de celle prise avant le précédent correctif audio : elle
n’est pas annoncée identique à ce relevé ancien. Le contenu conservé est
comparé à la première copie de ce lot ; les scripts de génération vérifient
en outre l’empreinte avant/après chaque recette.

Le parcours applicatif est utilisable en recette ; **la couverture et la fidélité
du compte rendu ne sont pas qualifiées**. Aucun gain de précision n’est annoncé.

Tests mathématiques de rejet et de voix proches ≠ précision sur personnes.
Un essai d’embeddings sur deux groupes du municipal a extrait en CPU des
fenêtres disjointes du même enregistrement : cohérence acoustique, **sans
enrôler de personne ni stocker de vecteur**, sans mesure de précision nominative.
Cet essai dépend du regroupement préalable et n’est pas un test interséances.
La capture réelle de nouvelles références autorisées, la calibration, les
locuteurs proches réels, les nouveaux inconnus et les réunions longues avec
vérité terrain restent à faire. Le test de blocs sur trois heures de texte
est un test de couverture technique, pas une réunion longue réellement écoutée.
Pas de recompilation ni de validation sur PC Windows vierge pour ce lot.

La protection DPAPI lie le coffre au compte Windows. Une simple copie sur
un autre compte ou un autre poste ne constitue pas une migration des références ;
prévoir réenrôlement ou une procédure de migration habilitée, non fournie ici.
