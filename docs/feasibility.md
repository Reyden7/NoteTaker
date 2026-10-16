# Étude de faisabilité

## Décision de phase 0

Faisabilité partiellement démontrée sur Windows 11 x64. Les moteurs ASR et LLM
fonctionnent réellement sur CPU avec leurs fichiers locaux. Après demande
de l'utilisateur, une alternative sherpa de diarisation a aussi été exécutée
sur deux voix synthétiques. La phase 0 reste ouverte : la qualification des
chevauchements, des voix naturelles et du fonctionnement intégral hors ligne
n'est pas remplie. La commercialisation et l'installateur ne sont
pas validés.

## Résultats mesurés

Les valeurs exactes et dernières exécutions sont dans `evidence/phase0-probes.json`.
Fixture : voix SAPI française Microsoft Hortense Desktop, texte fictif,
PCM16 mono 16 kHz, 13,59 secondes. Un essai initial avait mal interprété les
accents du script PowerShell 5 ; il est conservé dans le rapport du premier
essai et a été corrigé par un BOM UTF-8 avant les mesures retenues.

Whisper small int8 CPU a transcrit les quatre phrases, y compris « 12 000 euros »
et l'absence de résultat de vote. La génération Qwen3 4B Q4_K_M a produit un
JSON validé, cité `s0`, gardé `vote_id: null` et signalé le vote à vérifier.
Ce sont des essais indépendants sur entrées courtes. Le LLM reçoit un segment
de texte fixé ; il ne s'agit pas encore d'une chaîne séance → export intégrée.
Aucun WER/DER de terrain n'est établi et un seul exemple ne prouve pas
l'absence d'hallucinations dans d'autres cas.

La sonde collecte durée murale et maximum observé de la somme des RSS de
l'arbre de processus (échantillonnage 50 ms, mémoire partagée potentiellement
comptée plusieurs fois). Ce n'est ni une mesure VRAM ni une borne mémoire exacte.
La première mesure ne suivait que le trampoline Python ; elle est invalide
pour la RAM ASR et a été remplacée par la mesure de l'arbre.

La capture n'a pas été testée au microphone. Seuls l'inventaire PortAudio et
un test de persistance de segments PCM avec arrêt réel du processus sont
effectués. La continuité audio, le VU-mètre, les pauses et la récupération du
segment actif restent à développer et tester.

## Installateur unique et volume

Les poids actuels occupent déjà environ 2,98 Go décimaux. Le lot final doit
ajouter Python, Qt, PyTorch, CT2, llama.cpp, codecs, polices et éventuelles
bibliothèques CUDA/cuDNN. Les poids quantifiés se compressent peu ; aucune
taille finale honnête ne peut être donnée avant assemblage et compression.

La [documentation Inno Setup sur DiskSpanning](https://jrsoftware.org/ishelp/topic_setup_diskspanning.htm)
impose `DiskSpanning=yes` si la taille compressée dépasse 4 200 000 000 octets.
Cela produit des fichiers `.bin` en plus du `.exe` et ne respecte donc pas la
demande de fichier unique. L'édition 64 bits d'Inno ne permet pas à elle seule
de supposer cette limite supprimée.

La première option à éprouver est un lot compact : un seul modèle ASR,
un seul GGUF, une seule copie de chaque runtime CPU, et uniquement les backends
GPU réellement validés et nécessaires. Si le lot ne tient pas sous la limite,
il faut mesurer des modèles plus petits ou qualifier un autre format de
bootstrapper autonome avant de figer le choix. Aucun téléchargement client,
installateur multipartie ou renommage d'archive ne constituera une solution
acceptée. Ce risque bloque aujourd'hui la promesse de Setup unique complet.

## Blocages et levées attendues

| Point | Preuve actuelle | Action requise |
|---|---|---|
| Community-1 | HTTP 401 pour config à révision fixée | Compte de build autorisé, acceptation des conditions par son titulaire, acquisition puis inférence locale sans jeton |
| Diarisation Windows | Sherpa CPU distingue deux voix synthétiques ; Community-1 non acquis | Qualifier sherpa sur corpus français naturel 2/3 voix et chevauchements ; figer le lot natif |
| Whisper GPU | Crash natif faute de cuDNN 9 | Constituer le lot CUDA 12/cuDNN 9 autorisé et refaire la tâche sur GPU |
| Redistribution | Audit initial et inventaires disponibles | Notices exactes, sous-dépendances, source/offres LGPL et EULA de chaque DLL |
| Setup unique | Limite Inno officielle et modèles ~2,98 Go | Assembler et mesurer le lot compressé avant validation du packaging |
| Hors ligne intégral | Zéro tentative socket Python pour l'ASR | VM déconnectée, capture réseau système et cycle complet sans outils de dev |

La piste sherpa évite la pile PyTorch dans le lot candidat. Son moteur et ses
modèles ajoutent quelques dizaines de Mo plutôt que cette pile volumineuse.
Cela améliore la possibilité d'un Setup compact ; cela ne prouve pas que le
lot final avec tous les backends retenus respectera la limite Inno.

La pile CPU autonome est plausible mais le matériel de développement ne prouve
ni les minima 8 Go ni la compatibilité Windows 10. Il n'existe pas encore de
résultat de VM vierge, installation, mise à jour ou désinstallation.
