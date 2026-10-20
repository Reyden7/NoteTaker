# Diagnostic Parcoursup — 20 octobre 2026

## Protocole courant : comparaison-v2

L’utilisateur a fourni `C:/Users/quent/Desktop/correction.txt` en réponse à la
demande de correction après écoute. Le fichier est archivé **octet pour octet**
dans `output/diagnostic-parcoursup/2026-10-20-01/comparaison-v2/` ; sa provenance,
son SHA-256 et les six fragments absents de cette révision sont inventoriés.
103 passages humains restent, contre 109 dans A. Aucun original n’est remplacé.
Les repères horaires sont conservés, sans ré-alignement acoustique des mots
corrigés. L’agent n’a toujours pas d’entrée audio et ne revendique aucune écoute.
La copie humaine distingue notamment Arthur (premier arrivé/premier servi),
Bruno (tirage au sort) et la réponse de Manès sur les notes. Le patronyme de Bruno
reste incertain. La référence narrative originale est préservée, avec ses limites.

Le premier A du protocole v1 a échoué après **900,409 s natives**, pour dépassement
de délai : **3 526,922 s CPU** (user + kernel), sortie partielle conservée.
Il n’est pas une synthèse complète ni un résultat comparable aux essais v2.
Le modèle énumérait de longs blocs de références de fragments : la nouvelle
sérialisation regroupe uniquement les fragments consécutifs du même libellé
d’auteur, sans sélection ni réécriture du texte. Le catalogue complet des IDs
et horaires reste à côté des entrées ; T001, T002… sont propres à chaque variante.
Ils ne doivent jamais être comparés entre variantes sans ce catalogue.

Toutes les variantes v2 utilisent **la même instruction, le même schéma, les
mêmes paramètres natifs**, budget de 3 000 tokens, processus neuf, zéro réponse
réutilisée. A contient 109 passages / 18 tours ; B 103 / 13 ; C 161 / 28.
C contient **exactement B**, précédé de 58 fragments originaux supplémentaires,
non corrigés à l’écoute. Seule cette extension change entre B et C.
La fenêtre reste 17:31.960–20:37.580. L’extension disponible est surtout antérieure ;
aucun contexte transcrit après 20:37.580 n’existe dans les 670 sources figées.
Le WAV s’étend à 20:40.017 mais ne crée pas de nouvelles paroles transcrites.
Cette limite empêche de conclure sur le bénéfice d’un contexte corrigé des deux côtés.

Les textes A/B diffèrent aussi par la segmentation corrigée et les libellés,
pas seulement l’orthographe : l’effet mesuré est celui de cette correction globale.
Les rubriques portent des références aux tours ; `resolve_sources.py` permet
de rattacher les citations littérales aux fragments. Ce rattachement mécanique
ne prouve pas que la source soutient tout le sens d’une affirmation.

La référence indépendante opérationnalisée v2 est préparée avant lecture des
réponses v2 : onze points narratifs, affinés par la copie humaine, plus deux
compléments du verbatim. Les jugements comparatifs sont ceux de l’analyste Codex
sur ces sources humaines, pas de nouvelles notes aveugles attribuées par un humain.
Le même Qwen ne sert jamais de juge ou de vérité terrain.

```powershell
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.import_human
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.reference_v2
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.run_compact --case A-original
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.run_compact --case B-corrigee-humaine
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.run_compact --case C-corrigee-contexte
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.analyse_refus --human-revision
```

Chaque création refuse d’écraser un résultat existant. Les commandes ci-dessus
documentent les appels réellement utilisés ; réexécuter demande un nouveau
dossier explicitement versionné, pas la suppression des anciens résultats.

## Historique conservé : préparation provisoire et protocole v1

Expérience hors application. Aucun code sous `src/`, migration, base de séance,
brouillon, empreinte vocale ou contrôle d'export n'est modifié. Les scripts
importent le runtime local existant uniquement pour un appel natif par condition.
Ils n'appellent ni le pipeline de synthèse, ni ses contrôles de rédaction, ni Qwen
comme juge de ses propres résultats. Les sorties restent des artefacts expérimentaux.

## Sources et fenêtres

- Référence narrative humaine reçue : fichier Desktop `1) Presentation de louise Montangon.txt`,
  copié avec conservation de l'original. Ce n'est pas un verbatim horodaté ; certaines
  graphies, dont « Bruno Jodir », restent à confirmer, sans correction par supposition.
- A : transcription figée des tests à 670 passages, avec ses attributions sauvegardées.
  Elle contient donc les corrections antérieures déjà présentes ; elle n'est pas
  présentée comme la sortie acoustique brute jamais modifiée de Whisper.
- Fenêtre focale complète : **17:31.960–20:37.580**, soit 185,620 s / 109 passages.
- C : contexte **16:00.000–20:40.016**, 167 passages. Les 109 passages focaux sont
  identiques à B ; seul le contexte s'étend. L'audio disponible dans cet instantané
  se termine à 20:40.017. Les propos suivants de la référence (échec en licence,
  santé mentale) ne sont pas assimilés à des omissions sur ce corpus.

## Correction et écoute

L'outil de cette session a signalé que l'agent ne dispose pas d'entrée audio.
Les corrections préparées sont donc **provisoires**, tirées de la référence narrative
et des erreurs lexicales évidentes. Aucune écoute par l'agent ni validation humaine
du verbatim n'est simulée. Les clauses corrompues, chiffres ambigus et débuts
d'interruption ne sont pas reconstruits de mémoire.

Le fichier `transcription-corrigee-A-VERIFIER.md` et le WAV focal servent à la
vérification réelle. C possède aussi son fichier `transcription-contexte-large-A-VERIFIER.md`
et son WAV élargi. Les propositions et leur provenance sont dans `corrections-proposees.json`.
Après correction réelle, B et C doivent conserver exactement la même fenêtre
focale, les IDs et les horaires. Une preuve `audio-review.json` doit préciser
le relecteur, l'écoute effectivement faite et les SHA-256 des fichiers validés.
Un simple faux reçu n'est jamais un moyen de débloquer une expérience.

## Conditions contrôlées

Les trois variantes utilisent la même instruction, le même schéma JSON générique
(sans réponses attendues ni IDs spécifiques d'une variante), les mêmes paramètres :
Qwen3 4B Instruct-2507 Q4_K_M local, runtime CPU existant, `-ngl 0 -t 4 -c 12288`,
température 0,7 / top-p 0,8 / top-k 20 / min-p 0 / graine 42 / maximum 3500 tokens.
Chaque variante utilise un dossier neuf et un processus natif neuf, zéro réponse
en cache. Le cache disque Windows n'est pas purgé ; le poste n'est pas isolé.

La référence humaine et les réponses des autres essais ne sont jamais soumises
à Qwen. Seuls les libellés et textes corrigés de l'entrée B/C peuvent changer.
Le contexte C aide à comprendre la fenêtre focale ; il ne change pas la fenêtre
évaluée. Les contrôles littéraux sont rapportés après génération **sans supprimer
les sorties**, et ne constituent jamais une validation sémantique.

## Exécution

Depuis la racine du dépôt, environnement local déjà installé :

```powershell
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.run_case --case A-original
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.run_case --case B-correction-proposee
.venv\Scripts\python.exe -m experiments.parcoursup_20261020.run_case --case C-correction-contexte-large
```

B/C refusent de démarrer sans vérification audio réelle identifiant exactement
les entrées. Aucun téléchargement. Le profil conserve wall/CPU natifs,
prompt/schéma/brut, paramètres et empreintes du modèle/runtime/DLLs. Les fichiers
protégés (code de production, sources, ancien résultat, bundle) sont comparés
aux empreintes initiales ; les nouvelles corrections restent dans ce dossier
expérimental et dans `output/diagnostic-parcoursup/2026-10-20-01`.
