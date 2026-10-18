# Recette d’une réunion réelle de 10 à 20 minutes

**État de la réunion municipale : NON VALIDÉ.** Un débat télévisé français de
51 minutes a depuis été fourni et a révélé les défauts de la version 0.1.
L'audit et la comparaison 0.2 sont décrits dans `audit-0.2.md` et
`benchmark-0.2.md`. Ce corpus ne valide ni une capture micro de réunion longue,
ni la fidélité des voix et des résumés sans référence humaine annotée.
La procédure suivante reste à exécuter dans les conditions d'une mairie.

## Préparation

Choisir au moins trois personnes informées de la prise et de son usage local.
Préparer deux ou trois points d’ordre du jour. Un opérateur notera quelques
changements de parole, chiffres/noms, décisions et résultats explicitement
connus. Ne pas créer de résultat pour un point sans vote.

Prévoir des tours de parole simples puis des interruptions, brèves paroles
simultanées et bruit ambiant représentatifs. Conserver les données dans le
dossier local ; aucun envoi au développeur n’est automatique.

## Enregistrement ou import

1. Créer une séance de recette distincte avec l’ordre du jour et les trois noms.
2. Sélectionner le vrai microphone, enregistrer et écouter une prise courte.
   La décocher pour l’exclure de l’analyse de la réunion.
3. Enregistrer 10 à 20 minutes. Observer niveau, espace libre et incidents ;
   essayer une pause/reprise et noter son instant.
4. Arrêter, écouter début/milieu/reprise/fin, fermer puis rouvrir la séance et
   vérifier que données et prises sont conservées.

Pour un appareil externe, importer WAV/MP3/M4A et conserver le fichier externe
comme référence. Noter format, durée et canaux puis écouter la dérivation.

## Analyse et contrôle

1. Lancer le CPU, relever temps de traitement, mémoire et incidents.
2. Comparer des passages aux notes et à l’écoute : noms, nombres, négations,
   changements de voix, interruptions et paroles simultanées.
3. Corriger textes et voix, scinder les passages si nécessaire ; compter les
   corrections et mesurer le temps opérateur.
4. Vérifier les avertissements de chevauchement : faux positifs et passages
   simultanés non signalés. Ne pas valider ce critère sans références écoutées.
5. Générer le brouillon, contrôler classement et références, saisir les décisions
   et votes connus. Un point sans résultat doit rester à compléter.
6. Tenter l’export avant relecture : refus attendu. Relire, confirmer dans la UI,
   exporter DOCX et PDF puis vérifier contenu, accents, nombres et pagination.
7. Modifier un texte ou un vote : un nouvel export doit demander une relecture.

## Fiche à remplir après exécution

| Critère | État initial | Preuve à relever |
|---|---|---|
| Trois voix françaises naturelles | Non validé | Fichier, durée, participants d’essai |
| Capture 10–20 min, pause et reprise | Non validé | Durées et plages écoutées |
| Normalisation multicanal | Non validé sur réunion réelle | Canaux, durée et écoute |
| Attribution des voix | Non validé | Erreurs horodatées et corrections |
| Chevauchements et bruit | Non validé | Faux positifs/négatifs annotés |
| Transcription française naturelle | Non validé | Référence corrigée, noms/chiffres/négations |
| Classement Qwen et couverture | Non validé | Sources mal classées et échanges non classés |
| Aucun vote absent inventé | Non validé sur séance réelle | Comparaison sources/saisies/exports |
| Relecture et deux exports | Non validé sur séance réelle | Révision, opérateur, fichiers contrôlés |
| Temps et confort de correction | Non validé | Temps d’analyse, Qwen et opérateur |

Ne pas annoncer de WER ou DER sans transcription de référence et annotation
temporelle des locuteurs adaptées aux chevauchements. Cette recette terrain
ne remplace pas la qualification de l’installateur sur Windows vierge déconnecté.
