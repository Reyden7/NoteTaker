# Benchmark reproductible de qualité 0.2

## Référence conservée et périmètre

L'audit `audit-0.2.md` précède les modifications des moteurs. La référence
provient de la séance réelle du 16 octobre, conservée par une sauvegarde SQLite
cohérente et des fichiers de jobs en lecture seule. Les transcriptions, voix,
prompts et audio restent dans `output/quality-02` ou les données privées, exclus
de Git. Les rapports versionnés ne doivent pas contenir le débat complet.

Le MP3 dure 3 054,733 s ; une prise micro cochée de 9,899 s le précède dans la
référence. Tous les essais appariés utilisent **la même dérivation de 3 064,632 s**,
SHA-256 `3e38e6f1e744e07d2250aacca8cc3fe4c81f0a5f913a57549b96bdddde3bb8f9`.
Une recette du MP3 seul constitue un autre essai ; ne pas comparer ses timestamps
directement à ceux de cette référence.

## Étapes

1. `scripts/audit_quality.py --data-dir <données> --title <séance> --audio <MP3>`
   crée une nouvelle référence sans écrire dans la base utilisateur. Conserver
   son dossier, le commit source et la configuration machine.
2. `scripts/benchmark_speakers.py` compare liaison complète/moyenne et plusieurs
   seuils sur les mêmes fenêtres et le même embedding ERes2Net. Le cache local
   contient les vecteurs nécessaires à la reproductibilité, propres à cette
   recette ; il ne constitue pas un profil permanent de personnes.
3. `scripts/acquire_quality_assets.py` est une acquisition explicite réservée
   au build : modèle WeSpeaker public, métadonnées compatibles sherpa et police
   Noto Sans. L'application n'appelle jamais ce script. Les poids originaux
   ne sont pas écrasés ; la copie adaptée ajoute uniquement les métadonnées.
4. `scripts/benchmark_speakers.py --model models/diarization/wespeaker/voxceleb_resnet34-sherpa.onnx --variant wespeaker`
   compare le second embedding sur les mêmes plages nettoyées.
5. `scripts/benchmark_quality.py --stage asr` recalcule Whisper CPU, conserve les
   mots et leurs timestamps. `--stage diarization` réexécute la chaîne complète
   sherpa + refinement, indépendamment du cache de l'étude précédente.
6. `scripts/benchmark_quality.py --stage summary --diarization output/quality-02/wespeaker/complete-0.4.json`
   aligne la nouvelle transcription, produit les synthèses intermédiaires,
   vérifie les citations/attributions puis regroupe les sujets. Les résultats
   intermédiaires sont réutilisables seulement si prompt, schéma, configuration
   et identité locale des fichiers modèle/binaire sont inchangés.
   Lors d'une reprise, le temps mural du worker exclut les inférences déjà
   calculées. Le rapport conserve aussi la somme des durées originales des
   appels natifs du résultat final, y compris ceux réutilisés ; ne pas présenter
   le seul temps de reprise comme le coût d'une synthèse complète.
   Cette recette emploie le post-traitement de confiance étudié sur les mêmes
   embeddings mis en cache. Le fichier `diarization-result.json` conserve la
   chaîne native complète exécutée avant cet ajustement géométrique ; ses
   compteurs d'incertitude ne doivent pas être substitués à ceux de la variante.
7. `scripts/benchmark_report.py --original-audio <MP3>` crée une séance de recette
   distincte et des **aperçus non validés** PDF/DOCX pour contrôle visuel. Il
   vérifie le refus d'export normal sans relecture, ne crée aucun objet de
   relecture et ne modifie pas la séance initiale. Préserver ce nouveau dossier
   avant toute relance du rapport.

Pour une nouvelle exécution complète, préserver l'ancien dossier de résultats
et sélectionner un nouveau répertoire de benchmark dans les scripts ; les
scripts de recette sont actuellement configurés pour ce premier cas réel.
Ne pas écraser une référence ou les corrections de sa séance de recette.

## Mesures et limites

| Mesure | Calcul / référence nécessaire |
|---|---|
| Nombre de voix | Identifiants réellement produits, sans imposer six |
| Parole/identifiant, segments courts et incertains | Durées/compteurs automatiques ; ne prouvent pas l'exactitude |
| Regroupement correct | Référence humaine des voix ; précision/rappel par paires sur extraits annotés |
| Transcription | WER sur textes vérifiés ; sans référence, afficher non mesuré |
| Temps CPU | Durées murales réelles par worker, chargement inclus ; signaler les calculs concurrents |
| Couverture thématique | Liste humaine des sujets et jugement de leur traitement ; compteur automatique insuffisant |
| Informations inventées | Relecture humaine de chaque affirmation ; références existantes et second LLM ne prouvent pas l'absence d'invention |
| Document | Pages, caractères, lecture des PDF/DOCX rendus, glyphes, blancs, références internes |

Les annotations optionnelles de `benchmark_report.py --reference <JSON>` ont
la forme `{"segments":[{"start_ms":0,"end_ms":1000,"speaker":"voix-humaine-A","text":"texte vérifié"}]}`.
Aligner leurs bornes sur des interventions entières : le score WER actuel
assemble les interventions recouvrant chaque plage. La précision par paires
n'est **pas** un DER temporel, ne traite pas des références multi-voix simultanées
et ne doit pas être publiée sous ce nom. Garder un lot de contrôle distinct
du lot de réglage pour éviter de sélectionner un seuil sur le seul débat.

Sans ces annotations, `human_metrics`, `topic_coverage` et `hallucination_rate`
restent nuls/non mesurés. Ne jamais les remplacer par zéro erreur. Un nombre
de groupes proche des six personnes annoncées n'est pas une validation.

## Contrôle humain à terminer

Écouter des extraits répartis au début, au milieu et à la fin, dont des voix
proches, tours courts et chevauchements. Annoter les personnes sans utiliser
les prédictions comme vérité. Relire les reformulations avec les citations
et leur contexte ; rechercher négations perdues, propos fusionnés, actions ou
décisions induites. Vérifier les passages exclus/rejetés et les sujets absents.
Confirmer ensuite seulement la révision appropriée dans l'interface ; pour le
PV municipal, la confirmation du rôle de secrétaire est obligatoire.

La recette Windows vierge déconnecté reste distincte et non validée.

## Comparaison du modèle de synthèse après l'échec complet 0.2

Le premier parcours complet est conservé, y compris ses aperçus rejetés : le
modèle n'a retenu que huit des 31 informations contrôlées, avec des sources
s'arrêtant vers la douzième minute. Une courte sortie ne prouve pas une synthèse.
Le regroupement doit désormais reprendre chaque information fournie exactement
une fois ; le contrôle refuse omissions et doublons. Cela ne prouve toujours
pas la couverture des sujets absents dès l'extraction.

```powershell
.venv\Scripts\python.exe scripts\acquire_summary_candidate.py
.venv\Scripts\python.exe scripts\probe_verifier.py --field --model models/llm/qwen3-4b-instruct-2507/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
.venv\Scripts\python.exe scripts\benchmark_quality.py --stage summary --diarization output/quality-02/wespeaker/complete-0.4.json --model models/llm/qwen3-4b-instruct-2507/Qwen3-4B-Instruct-2507-Q4_K_M.gguf --run-label instruct-2507
```

La comparaison du candidat repart des mêmes textes/voix ; elle ne réutilise pas
des inférences d'un autre modèle. Le fichier `summary-execution.json` capture
les empreintes du code, du GGUF, du binaire et de l'audio avant le lancement.
Les contrôles de cohérence de citations restent des cas de développement,
pas des annotations humaines ni une mesure WER/DER ou de fidélité globale.

Résultat complet conservé : `evidence/quality-02-comparison-instruct.json`.
Ne pas relancer la création du rapport vers le même dossier privé contenant
les corrections/relectures. Les arguments de destination sont résolus en
chemins absolus pour que l'audio reste accessible à l'application lancée depuis
un autre répertoire. Le lanceur `scripts/run-quality-review.ps1` ouvre la
séance de recette distincte existante, sans recalcul ni approbation.

Le regroupement initial du candidat a été refusé (onze omissions, un doublon),
puis un appel Qwen d'affectation à clés obligatoires l'a réparé. Les 36
informations retenues apparaissent exactement une fois dans les huit thèmes.
Cela ne dit rien des sujets omis avant cette étape ni de la fidélité humaine.
La recette compilée du 18 octobre a en outre révélé qu'un doublon interne à
un thème était refusé par le schéma avant d'atteindre cette réparation. Le
schéma intermédiaire est corrigé ; le contrôle final reste obligatoire. Les
sorties avant correction et leurs empreintes sont conservées séparément.

Les durées observées sont 1 369,168 s pour ASR, 573,678 s pour la chaîne native
de voix, et 3 056,834 s cumulées pour les appels de la synthèse retenue. Les
90,011 s de la dernière reprise excluent les appels en cache. Calculs concurrents,
donc aucune comparaison isolée de performances n'est revendiquée.
