# Utiliser NoteTaker 0.1

Version de travail CPU pour une recette locale. La commercialisation et le
Setup final ne sont pas validés.

## Démarrer

Ouvrir `dist\NoteTaker\NoteTaker.exe`. Conserver tout le dossier NoteTaker :
les dépendances et modèles sont à côté de l’exécutable. Il n’y a aucun premier
téléchargement. Depuis les sources : `powershell -File scripts\run.ps1`.

Les données sont sous `%LOCALAPPDATA%\NoteTaker`. L’option `--data-dir` permet
un autre dossier ; utiliser le même dossier aux lancements suivants pour
retrouver les séances. Deux interfaces sur le même dossier sont refusées.

## Séance et audio

1. Créer une séance, compléter titre, commune, date, lieu, participants/présences,
   ordre du jour (un point par ligne) et notes. Enregistrer les informations.
2. Dans Audio, sélectionner le microphone, vérifier l’espace libre et faire une
   prise courte. Arrêter puis écouter. Décocher la prise d’essai pour l’exclure
   de l’analyse sans la supprimer.
3. Enregistrer la réunion ; observer le niveau et la durée. La pause n’ajoute
   pas d’audio à la prise. Arrêter et sauvegarder avant les traitements.
4. Après une interruption, rouvrir la séance : la prise apparaît interrupted
   et ses trames récupérables restent utilisables. Une erreur d’intégrité est
   signalée, sans effacer les fichiers. Décocher une prise défectueuse permet
   de traiter les autres prises.

La dernière seconde n’est pas garantie lors d’une coupure électrique. La
qualification matérielle de ce cas reste ouverte.

Un enregistrement externe WAV, MP3 ou M4A peut être importé. Sa copie locale
est vérifiée ; l’original externe est inchangé. Les prises cochées sont
concaténées dans leur ordre d’ajout, sans silence ajouté entre elles. Tous les
codecs possibles de ces conteneurs ne sont pas encore qualifiés.

## Texte et intervenants

Cliquer Transcrire et distinguer les voix. L’UI affiche l’étape et permet
l’annulation ; les champs sont verrouillés pendant le traitement. Sélectionner
un passage pour le corriger ; double-cliquer pour l’écouter à son horodatage.
Les corrections de texte sont autosauvegardées après une courte pause de saisie.

Attribuer les noms manuellement dans le tableau des voix. Choisir l’intervenant
correct pour chaque passage puis confirmer l’attribution. Les regroupements
automatiques ne prouvent aucune identité. Un chevauchement possible doit être
vérifié à l’écoute ; sa qualité de détection reste inconnue en salle réelle.

Pour scinder un passage, placer le curseur entre les interventions et préciser
l’instant de coupure. Pour fusionner des voix, sélectionner la voix puis sa
destination après contrôle audio. Les passages modifiés restent à vérifier.
Une nouvelle analyse conserve un instantané de la version précédente mais
remplace la transcription courante après confirmation ; cet historique n’a
pas encore d’interface de restauration dédiée.

## Projet de procès-verbal

Qwen classe les extraits corrigés selon l’ordre du jour. La première version
produit des extraits sourcés éditables, pas encore une synthèse libre du débat.
Vérifier les échanges à classer puis corriger titres, textes, références et
éléments à vérifier dans l’éditeur du projet.

Saisir séparément les décisions et votes connus. Un résultat saisi exige les
quatre nombres (pour, contre, abstention, non-participation) et sa source. Un
résultat inconnu reste À compléter avec les nombres vides. Aucun résultat,
quorum, majorité ou adoption n’est calculé automatiquement.

Sauvegarder, cliquer J’ai relu cette révision, saisir le nom du relecteur et
confirmer après vérification des textes, sources, intervenants, décisions et
votes. Une modification pertinente impose une nouvelle relecture. Cette action
autorise l’export ; elle ne vaut pas adoption officielle du PV.

## Exports et sauvegarde

Exporter PDF ou DOCX après relecture. Les deux portent la mention de projet
non officiel. Une copie et son instantané restent dans la séance ; le brouillon
et les exports sont distincts.

Pour une sauvegarde de cette version, fermer NoteTaker puis copier tout le
dossier de données sur un support local protégé, base et sessions incluses.
Ne pas copier uniquement SQLite pendant que l’app est ouverte. L’assistant
de sauvegarde/restauration portable reste à développer ; certaines références
audio sont encore absolues, donc conserver le chemin d’origine.
