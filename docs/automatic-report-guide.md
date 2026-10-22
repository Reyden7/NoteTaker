# Obtenir un premier compte rendu

La dernière recette municipale et le lanceur `Ouvrir-la-recette-simple.cmd`
sont dans `output/automatic-report-20261021/470f7221d5eb4cd0974963bf81f4e64d/`.
Le lanceur utilise une copie des séances, avec le brouillon déjà calculé.
Ne pas relancer la génération pour simplement le consulter.

1. Ouvrir la recette depuis ses sources. Cliquer **Importer un enregistrement**.
   Sans séance ouverte, le nom du fichier crée la séance. Pour une autre réunion,
   créer une nouvelle séance dans la colonne de gauche.
2. Cliquer **Générer le compte rendu**. NoteTaker vérifie l’audio et réutilise
   la transcription si le montage est identique ; sinon il appelle les moteurs
   audio existants selon le réglage automatique, CPU ou GPU compatible.
3. Qwen rédige directement depuis les passages attribués, sans demander
   d’approuver des fiches. Les voix sans identité connue restent non identifiées.
4. Choisir un sujet dans la liste, corriger le texte puis **Enregistrer mes
   corrections**. **Écouter les sources** ouvre les citations et passages audio.
   Lire **À vérifier** et, au besoin, **Détails / omissions**.
5. **Exporter le brouillon PDF/DOCX** produit une copie marquée non relue et non
   officielle, sans créer de relecture. Les références structurelles invalides
   restent bloquantes ; l’incertitude n’est pas une approbation.
6. **Relecture et validation** ouvre le mode avancé. Relire, compléter les votes
   réellement constatés et confirmer humainement la révision avant l’export
   soumis au parcours de validation habituel. Aucun clic de génération n’adopte
   un procès-verbal au nom de la collectivité.

Le mode avancé conserve transcription, noms, scission/fusion, annuaire,
participants, registres historiques, citations, décisions, votes et exports.
Un refus de reformulation conserve sa citation exploitable ; les formulations
sans source exacte et les passages non repris restent inventoriés. Un inventaire
de sources n’est pas une mesure de fidélité ou de couverture thématique.

## Références vocales facultatives

**Désactivées par défaut.** L’annuaire civil et le compte rendu fonctionnent
sans biométrie. Avant toute collecte : décision juridique de la collectivité,
information des personnes, droits d’accès et conservation à définir avec le DPO.

Dans **Annuaire et références vocales** : créer la fiche nom/prénom, puis ouvrir
**Autorisation et paramètres**. Enregistrer la référence de décision, le
responsable habilité, l’échéance et la conservation effectivement décidée.
Le formulaire n’est pas une validation de licéité. L’accès repose sur le compte
Windows qui détient la protection DPAPI ; utiliser des comptes individuels.

Choisir une fiche et **Enregistrer / gérer les références vocales**. Sélectionner
le microphone, lire naturellement 30–60 secondes, arrêter, réécouter puis
confirmer l’identité pour extraire. Plusieurs prises sont possibles. Import
WAV/MP3/M4A de 30–90 secondes également possible, sans modifier l’original.
La prise du microphone est chiffrée progressivement ; l’écoute/extraction des
références s’effectue en mémoire, sans WAV temporaire en clair.

Les contrôles signalent saturation, trop peu de parole, changements de voix
et chevauchements possibles. Ils ne prouvent pas l’identité ni une prise sans
bruit : écouter et recommencer si nécessaire. Les références doivent être
réenrôlées après changement incompatible du modèle. Supprimer une prise ou
toutes les références depuis ce dialogue ; la suppression reste possible après
révocation de l’autorisation. Les sauvegardes externes et enregistrements de
réunion possèdent leur propre conservation et doivent aussi être gérés.

La comparaison exige une **référence de calibration indépendante** renseignée
dans les paramètres : seuils par défaut non qualifiés. Aucun nom proposé si
score, marge ou cohérence insuffisants, passage trop court ou chevauchement.
Les noms reconnus sont des **identités proposées à confirmer**, pas des
attributions humaines confirmées. Corriger les noms dans le mode avancé ; ces
corrections ne réentraînent aucun modèle et ne modifient aucune référence.

**La précision nominative sur de nouvelles réunions reste non validée** tant
que des prises autorisées et des références humaines indépendantes n’ont pas
été testées. Le produit et son installateur commercial restent en qualification.

## Limite du brouillon municipal livré

La recette contient quatre reformulations et trois citations conservées
« À vérifier ». Vingt-trois passages ne sont pas repris : consulter leur
inventaire et la transcription avant de compléter le document. La couverture
et la fidélité ne sont pas validées. Les noms affichés sont ceux déjà confirmés
manuellement ; aucune empreinte nominative n’a été créée pour cette recette.
