# Utiliser NoteTaker 0.2.1 en recette

Version de travail CPU pour une recette locale. La commercialisation et le
Setup final ne sont pas validés.

## Démarrer

Ouvrir `dist\directory-01\NoteTaker\NoteTaker.exe`. Conserver tout le dossier NoteTaker :
les dépendances et modèles sont à côté de l’exécutable. Il n’y a aucun premier
téléchargement. Depuis les sources : `powershell -File scripts\run.ps1`.

Les données sont sous `%LOCALAPPDATA%\NoteTaker`. L’option `--data-dir` permet
un autre dossier ; utiliser le même dossier aux lancements suivants pour
retrouver les séances. Deux interfaces sur le même dossier sont refusées.

## Annuaire municipal sans biométrie

Le bouton **Annuaire des intervenants**, à gauche, fonctionne même avant la
création d'une séance. Cliquer **Nouvelle fiche**, saisir prénom, nom, fonction
permanente et commune, puis **Enregistrer la fiche**. Prénom et nom sont requis.
Les fiches peuvent être corrigées, archivées puis réactivées. Utiliser la
recherche (accents et casse ignorés), le filtre de commune et le filtre
actives/archivées. Les homonymes restent des fiches distinctes.

La fonction permanente décrit la fiche, par exemple « Adjointe aux finances ».
Un rôle comme « Présidence de séance », « Secrétaire » ou « Invitée » se renseigne
dans la séance, sans changer cette fonction. L'historique de la fiche conserve
les versions avant correction et les opérations d'archivage/réactivation.

Le bouton **Futur assistant d'enrôlement vocal** est volontairement grisé.
Aucune capture de référence, empreinte ou identification biométrique n'est
disponible. Cet annuaire civil est stocké localement dans la base de travail,
sous les permissions du compte Windows ; il n'est pas un coffre chiffré.

## Préparer les présences et procurations

1. Ouvrir la séance, puis l'onglet **Participants** et **Ajouter depuis l'annuaire**.
   Cocher les personnes utiles ; la sélection reste mémorisée pendant une recherche.
2. Choisir **À renseigner**, **Présent**, **Absent**, **Excusé** ou **Représenté**.
   Une personne ajoutée n'est pas déclarée présente automatiquement.
3. Renseigner le rôle propre à la séance si nécessaire. Pour une personne
   représentée, sélectionner un autre participant déclaré présent comme mandataire,
   puis préciser la référence/période du pouvoir si utile.
4. Enregistrer. Une auto-représentation, un mandataire absent/non sélectionné
   ou une procuration associée à un autre statut est refusé. Corriger ou retirer
   le pouvoir avant de retirer son mandataire. La régularité juridique des pouvoirs
   reste à contrôler ; aucun quorum, nombre de voix ou résultat de vote n'est calculé.

Les informations de l'annuaire sont copiées lors de l'ajout à la séance. Modifier
une fiche permanente ne réécrit pas les séances préparées ni leurs anciens PV.
L'archivage d'une fiche conserve ses participations existantes ; réactiver la
fiche pour la sélectionner dans une nouvelle séance. Les anciennes notes libres
de présence restent dans **Séance** ; elles ne sont ni interprétées ni converties
automatiquement en présences structurées. Les deux sont conservées dans le PV municipal.

## Attribuer manuellement une intervention à l'annuaire

Dans **Transcription et voix**, sélectionner un passage, puis une personne dans
**Attribution manuelle depuis les participants de la séance**. Choisir **Ce
passage uniquement** ou **Toutes les interventions de cette voix**, puis cliquer
**Attribuer à cette personne**. Une attribution de groupe demande confirmation.
Les passages sans voix identifiée doivent être attribués séparément : ils
peuvent appartenir à plusieurs personnes.

Le texte corrigé reste conservé. La fiche permanente n'est pas modifiée et aucun
profil vocal n'est créé. Une attribution modifiée ou une nouvelle analyse garde
la version antérieure dans **Restaurer une transcription précédente**. Les noms
libres et les outils de scission/fusion restent disponibles. Une modification
des présences ou attributions impose une nouvelle relecture du brouillon.

## Première ouverture d'une ancienne base

La migration vers le schéma v4 est transactionnelle. Avant la mise à niveau,
une sauvegarde SQLite cohérente est créée dans `migration-backups`, sous le dossier
de données. Les anciennes séances, corrections, révisions et exports sont conservés.
Une séance sans nouveaux participants structurés garde son ancien contexte de
relecture. Sauvegarder aussi tout le dossier de données pour protéger les audios.
Ne pas rouvrir la base v4 avec un ancien exécutable : celui-ci refuse un schéma
plus récent. Un retour arrière se fait sur une copie distincte avec la sauvegarde
compatible, application fermée, sans écraser les nouvelles modifications.

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
Une nouvelle analyse conserve un instantané de la version précédente. Utiliser
« Restaurer une transcription précédente » pour retrouver textes, noms et
références ; la version remplacée est elle aussi conservée. « Diagnostic des
intervenants » affiche durées attribuées, passages courts et incertains. Ces
compteurs ne prouvent pas que chaque regroupement correspond à une personne.

Si une ancienne transcription contient `�`, relancer l'analyse depuis les prises
originales. Une police ne reconstitue pas les caractères perdus. Les corrections
historiques restent consultables/restaurables pour comparaison ; aucune réparation
linguistique automatique ne les remplace.

## Projet de procès-verbal

Choisir le document à préparer : transcription intégrale, compte rendu synthétique
ou PV municipal. La transcription ne passe pas par Qwen. La synthèse emploie
des blocs, reformulations, vérification des citations et regroupement thématique ;
elle est encore en qualification. Les attributions incertaines restent signalées.
Consulter les extraits sources depuis chaque point et écouter leur contexte.
La mention « opinion rapportée — auteur à confirmer » distingue notamment la
voix du présentateur qui reformule les propos d'un invité. Vérifier qui défend
la position ; attribuer un nom à la voix ne résout pas à lui seul cette question.
Corriger titres, textes, références et éléments à vérifier dans l'éditeur.
Les anciennes révisions de brouillon sont consultables et restaurables ; pour
restaurer des références anciennes, restaurer au besoin la transcription associée.

Saisir séparément les décisions et votes connus. Un résultat saisi exige les
quatre nombres (pour, contre, abstention, non-participation) et sa source. Un
résultat inconnu reste À compléter avec les nombres vides. Aucun résultat,
quorum, majorité ou adoption n’est calculé automatiquement.

Sauvegarder, cliquer J’ai relu cette révision, saisir le nom du relecteur et
confirmer après vérification des textes, sources, intervenants, décisions et
votes. Une modification pertinente impose une nouvelle relecture. Cette action
autorise l’export ; elle ne vaut pas adoption officielle du PV.
Le mode PV municipal demande en plus la confirmation explicite du rôle de
secrétaire de séance. Une décision/action simplement rapportée par l'IA doit
être vérifiée puis saisie dans les champs métier avant d'être considérée confirmée.

## Exports et sauvegarde

Exporter PDF ou DOCX après relecture. Les deux portent la mention de projet
non officiel. Une copie et son instantané restent dans la séance ; le brouillon
et les exports sont distincts.

Pour une sauvegarde de cette version, fermer NoteTaker puis copier tout le
dossier de données sur un support local protégé, base et sessions incluses.
Ne pas copier uniquement SQLite pendant que l’app est ouverte. L’assistant
de sauvegarde/restauration portable reste à développer ; certaines références
audio sont encore absolues, donc conserver le chemin d’origine.

## Examiner le premier débat avec la recette 0.2

Depuis le dépôt, exécuter :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\run-quality-review.ps1
```

Le lanceur ouvre le dernier exécutable de développement avec le dossier privé
`output/quality-02/instruct-2507/review-session`. La séance s'intitule
« Débat télévisé — recette 0.2 non validée ». La séance originale
« Conseil municipal 16/10/2026 » et ses corrections ne sont pas remplacées.
Les neuf groupes sont des prédictions à vérifier, sans noms humains supposés.

Le brouillon contient huit thèmes et 36 reformulations sourcées, encore à
corriger. Examiner les extraits et leur contexte, les opinions rapportées et
les informations absentes avant de confirmer la révision. Les aperçus PDF/DOCX
du benchmark sont non validés ; l'export normal reste bloqué tant qu'aucune
relecture explicite n'est enregistrée. Ne pas livrer ces données privées avec
le futur installateur.
