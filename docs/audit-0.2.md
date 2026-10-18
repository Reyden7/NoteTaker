# Audit qualité avant modification des moteurs — 16 octobre 2026

## Cas réel conservé

Séance « Conseil municipal 16/10/2026 », débat MP3 fourni par l'utilisateur.
Durée originale 3 054,733 s, stéréo 44,1 kHz ; SHA-256
`2083569d042c0f53b93a9fa383485dbe9edf6346a2fd8b64f0eddc9de0f88323`.
Un instantané cohérent de la base, les sorties et statistiques sont conservés
localement dans `output/quality-02/baseline`, sans écriture dans la séance.
La copie MP3 importée possède la même empreinte que l'original.

Mesures de la version 0.1 effectivement utilisée : **195 identifiants**, 576
tours diarisation, 1 485 passages Whisper, 506 passages incertains et 145 de
moins d'une seconde. 61 identifiants ont moins de 5 s de texte attribué. Le
brouillon contient 88 404 caractères, 11 sections, 29 alertes ; PDF de **54 pages**.
Whisper CPU 859,440 s, sherpa et masque 302,926 s, Qwen 1 476,445 s, d'après
les résultats de jobs conservés (pas une nouvelle mesure indépendante).

La prise microphone de 9,899 s était également cochée avant le MP3 : la
dérivation analysée dure 3 064,632 s. Les comparaisons utiliseront cette même
dérivation pour éviter un décalage artificiel ; une recette sur MP3 seul doit
être identifiée distinctement. L'ordre du jour contient « tester le logiciel ».
Ce n'est pas une liste des sujets du débat.

## Causes établies dans le code

1. **Absence de résumé narratif.** `llama_adapter.select_sources` interdit tout
   texte libre et classe seulement des identifiants dans l'ordre du jour saisi.
   `pipeline.assemble_draft` recopie ensuite tous les textes, y compris les
   passages non classés, et répète des titres lorsque le seuil de longueur est
   atteint. Il n'y a ni découverte de sujets, ni synthèse intermédiaire, ni
   regroupement global ni objectif de concision. Le nombre de pages est une
   conséquence de cette conception, pas un simple problème de mise en page.
2. **Votes surdétectés.** L'expression `VOTE_TEXT` contient notamment « contre »,
   « voix », « approuv… », « adopt… ». Elle retire ces passages de la synthèse
   et les transforme en alertes, sans reconnaître un acte de scrutin. L'export
   ajoute en outre une rubrique vote à compléter même en l'absence de scrutin.
3. **Police PDF insuffisante.** ReportLab emploie les polices standard, dont
   Helvetica, sans TTF Unicode embarqué ni contrôle des glyphes. Certains
   caractères du texte n'y sont pas représentables. Les références techniques
   sont imprimées intégralement dans les PDF/DOCX.
4. **Alignement trop grossier.** Un unique locuteur est choisi par couverture
   majoritaire pour tout un segment Whisper. Les timestamps de mots sont
   calculés mais jetés par le worker. Un changement de voix à l'intérieur d'un
   passage ne peut donc pas être représenté précisément. Un simple masque de
   chevauchement ajoute de l'incertitude sans séparer les paroles simultanées.
5. **Diagnostic et reprise insuffisants.** Pas de métriques de regroupement,
   normes/durées des embeddings ou confiance conservées. Relancer remplace la
   transcription active ; l'instantané antérieur existe dans edit_history,
   mais l'interface ne permet pas de le restaurer. Les boutons fusion, scission
   et noms existent déjà ; leur utilité est pénalisée par les 195 groupes.

## Diarisation : ce qui est établi et ce qui reste à mesurer

L'appel sherpa est **global sur tout le fichier**, avec `num_clusters=-1` et
un seuil fixe 0,5. Les identifiants ne sont pas remis à zéro à chaque bloc par
NoteTaker. Le code natif 1.13.8 normalise déjà les vecteurs en L2, calcule la
distance cosinus et applique une liaison **complète**. Il serait donc faux
d'attribuer la fragmentation à une absence de normalisation.

La liaison complète et le seuil non calibré rendent chaque groupe sensible
aux observations atypiques. L'extraction native écarte les trames de
chevauchement détectées, mais accepte des échantillons de parole cumulée très
courts (10 trames, environ 0,17 s). Les groupes courts, le bruit, la variabilité
du plateau et le modèle ERes2Net entraîné sur 3D-Speaker sont des causes
plausibles de fragmentation. Leur contribution respective **n'est pas encore
démontrée**, faute d'embeddings/annotations de référence dans la version 0.1.
Changer seulement le seuil pour obtenir six serait une correction non justifiée.

Sources du moteur audité :

- [Clustering 1.13.8 : L2, cosinus et liaison complète](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/sherpa-onnx/csrc/fast-clustering.cc)
- [Segmentation, exclusion des chevauchements et embeddings courts](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/sherpa-onnx/csrc/offline-speaker-diarization-pyannote-impl.h)
- [Documentation des modèles et du sens du seuil](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/models.html)

## Corrections et comparaison à entreprendre

### Complément établi en inspectant les textes, avant correction de l'IPC

Les résultats ASR et SQLite contiennent **1 734 U+FFFD**, donc une corruption
antérieure au PDF. Le worker compilé imprime du JSON avec accents littéraux ;
le parent impose UTF-8 mais utilise `errors='replace'`. PyInstaller ne garantit
pas que PYTHONIOENCODING configure stdout comme le Python de développement.
La lecture permissive a masqué l'erreur et perdu les caractères. La correction
doit imposer l'encodage du flux, employer un protocole JSON ASCII sans perte et
refuser les octets invalides. Les anciens U+FFFD ne sont pas réparables par une
police ou une substitution heuristique : il faut retranscrire l'original et
conserver séparément les corrections/historiques antérieurs.

Le premier essai de synthèse hiérarchique sur douze passages historiques a
effectivement reproduit ces caractères déjà présents et retenu des présentations
sans intérêt. Il n'est pas une réussite de qualité ; le résumé corrigé doit
être éprouvé sur le nouveau texte et filtrer ces banalités.

### Essais de synthèse réellement rejetés pendant le développement

Une première exécution complète a été interrompue après son premier bloc :
l'extraction demandant simultanément résumé et preuve recopiait encore la
transcription. Les essais suivants ont montré des identifiants de sources
erronés et des copies qui subsistaient malgré un exemple de reformulation.
Ils sont conservés séparément dans `output/quality-02/summary-attempt-01`,
`paraphrase-probe-01` et `paraphrase-probe` ; ils ne comptent pas comme recettes
réussies. Un essai réel distinct sur deux informations a ensuite produit des
reformulations, avec des imperfections grammaticales (`rephrase-study`).

La chaîne évaluée sépare donc extraction, reformulation sur contexte court et
vérification. Les unités compactes gardent leurs positions exactes dans les
interventions d'origine. Une citation inexacte ou attribuée à une autre voix
est rejetée ; une citation exacte n'établit toujours pas la fidélité du résumé.
Le refus de preuves faibles peut réduire la couverture et exige de relire aussi
les éléments rejetés. Aucun score de couverture n'est déduit du nombre de sujets.

Une régression sémantique a aussi été observée sur la fixture du worker
compilé : le coût global des travaux de bibliothèque est devenu celui de la
toiture. Le vérificateur initial l'a accepté. `scripts/probe_verifier.py` a
réellement testé un contrôle de portée plus strict : il rejette ce détail
ajouté mais classe aussi une paraphrase fidèle comme incertaine. Ce contrôle
n'a pas été intégré à partir de ce résultat insuffisant. La preuve est
`evidence/quality-02-verifier.json` ; aucun taux global n'en est déduit.

La première reformulation du débat a encore classé des descriptions comme
propositions et repris des détails non établis par les citations. Cette passe
a été arrêtée et conservée dans `output/quality-02/rewrite-with-preliminary-note`.
La reprise utilise seulement les citations exactes et le thème à titre de
contexte ; la note préliminaire et sa catégorie erronée ne conditionnent plus
la reformulation. Les dix-huit extractions inchangées restent réutilisées avec
leurs durées initiales. Les temps de développement rejetés ne sont pas présentés
comme une recette réussie ni masqués dans un gain de performances.

Conserver la référence 0.1 et l'audio, instrumenter les durées/normes,
construire les groupes sur des fenêtres de parole suffisamment longues et
propres, puis rattacher les segments courts avec confiance ou les laisser
incertains. Comparer plusieurs réglages sans nombre imposé et sans conclure
sur la seule baisse du nombre de groupes. Aligner les mots et conserver
séparément attributions automatiques et corrections/restaurations.

Développer une synthèse hiérarchique avec sujets découverts, arguments attribués,
citations sources vérifiables et contrôle de fidélité distinct. Aucune sortie
LLM ne doit créer un objet décision, action ou résultat de vote confirmé.
Préparer des modes distincts transcription/synthèse et un cadre municipal
dont l'export exige le secrétaire. Embarquer une police redistribuable et
limiter les références visibles à l'éditeur.

Les métriques WER/DER, couverture des sujets, attribution des opinions et
hallucinations nécessitent une référence humaine : **non mesurées à ce stade**.
Le débat télévisé est un cas réel de test, pas une validation générale des
conseils municipaux. Aucun problème n'est déclaré résolu par cet audit.

## Cause supplémentaire observée sur les vraies sorties de mots

La première comparaison du candidat a montré des citations coupées au milieu
de « c'est », « qu'il » et autres élisions. Whisper sépare parfois ces morceaux
et donne une durée nulle à « 'est » ou à un mot comme « a ». L'alignement par
couverture leur donnait systématiquement une voix nulle, créant des ruptures
artificielles et empêchant de retrouver une citation complète d'un même tour.

La correction réunit les morceaux d'une élision avant l'attribution. Un mot
de durée nulle ne rejoint une voix que si les deux voisins de durée positive
portent la même voix ; à une vraie frontière de voix il reste incertain.
Les timings déduits sont conservés et signalés. Sur les mêmes sorties Whisper
et sherpa, les passages passent de 2 350 à 1 822 et les unités de source de
1 172 à 644, sans perte des caractères hors espaces et avec les mêmes neuf
groupes. Preuve : `evidence/quality-02-word-alignment.json`. Ce contrôle de
conservation ne mesure pas l'exactitude des mots ni des personnes.
L'essai candidat antérieur reste dans `instruct-2507-before-word-fix` ; la
comparaison complète reprend sur le nouvel alignement.

## Contrôle de fidélité retenu pour le candidat

Le candidat Instruct rejette le faux budget de toiture tout en conservant une
paraphrase fidèle sur le cas de contrôle. Sur les erreurs textuelles repérées
dans le débat, il rejette la causalité ajoutée et la question créée. Un quatrième
cas a conduit à corriger l'attente initiale du test : se souvenir de son
adolescence n'établit pas qu'une déclaration a été faite pendant l'adolescence.
L'incertitude doit empêcher l'acceptation. Le premier rapport avec cette attente
erronée reste conservé dans `evidence/*initial-oracle.json` ; les rapports
actuels décrivent cette correction, sans la transformer en référence humaine.

Une relance de ce contrôle a mélangé, pendant le développement, les anciens
identifiants avec le nouvel alignement. Elle est exclue et conservée dans
`output/quality-02/verifier-study/invalid-alignment-probe.json`. Le script lit
désormais la requête originale associée aux affirmations testées. Le rapport de
comparaison suit la même règle pour ne pas réinterpréter des identifiants après
un nouveau découpage.

La consigne stricte validée sur ces cas est partagée entre le script et la
vérification réelle. Les dix-huit extractions du candidat restent réutilisées,
avec leurs durées originales, avant la nouvelle vérification. Ce contrôle
automatique demeure faillible ; aucun taux de fidélité globale n'est établi.

Un cas réel supplémentaire a montré l'insuffisance d'une citation isolée :
Whisper écrit « 30 000 lycées », puis les paroles voisines parlent de
« 30 000 personnes sur 200 blocages ». La reformulation transformait la première
mention en nombre d'établissements. Le vérificateur reçoit désormais les tours
voisins avec leurs identifiants de voix, pour refuser une unité ambiguë ou
contredite. Il ne remplace pas ce chiffre par une interprétation. Le contrôle
sans ce contexte est conservé dans `instruct-2507/verification-without-context`.
Un test couvre l'accès à la rectification et la séparation des voix ; la reprise
réelle réutilise les extractions/reformulations sans les présenter comme recalculées.
