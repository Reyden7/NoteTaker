# Évaluation humaine indépendante de la synthèse 0.2.5

## État

Douze extraits WAV de 40 secondes et un formulaire vierge sont disponibles dans
`output/direct-summary/reference-humaine`. L'utilisateur a accepté de les
annoter. Ils ne contiennent aucune réponse Qwen. Aucun score de qualité n'est
disponible avant réception et examen des annotations réelles.

La référence et l'évaluation ne constituent jamais une relecture du brouillon
dans NoteTaker. Elles ne permettent pas l'export d'un document non approuvé.

## 1. Annoter avant de consulter les nouvelles synthèses

Écouter le WAV. Les horaires affichés dans le formulaire sont ceux de la
réunion originale ; le début du WAV correspond à `start_ms`. La transcription
automatique et les repères « Voix N » sont des aides à corriger, pas une vérité
terrain. Préciser si une voix ou une phrase est inaudible ou si le contexte
avant/après manque. Ne pas deviner une identité.

Pour chaque extrait, relever :

- Les sujets précis réellement abordés, avec un intitulé neutre.
- Les informations importantes distinctes, leur importance et les mots entendus.
- L'auteur établi à l'écoute, ou « inconnu / incertain ».
- Le type : question, réponse, argument, avis cité, objection, proposition,
  anecdote ou décision explicitement évoquée.
- Les horaires et les segments utiles ; signaler une attribution automatique
  fausse ou une coupure de contexte.
- Les relations explicitement soutenues : réponse à une question, opposition,
  accord ou objection. Une proximité de vocabulaire ne suffit pas.

Le fichier `A_LIRE_ET_ANNOTER.md` peut servir de fiche de travail en texte libre.
Le JSON propose les mêmes rubriques pour une reprise structurée. Renseigner
`reviewer`, `human_checked` et `human_reference_completed` seulement après une
écoute et une annotation effectives. Conserver les versions de la référence.

## 2. Comparer les documents après fixation de la référence

Comparer les deux configurations sur les mêmes passages, noms, ordre du jour
et lexique. Une référence source n'établit pas que la rédaction en restitue le
sens. Lire la phrase et écouter son contexte. Pour chaque information annotée,
indiquer : présente fidèlement, déformée, absente ou impossible à évaluer.
Pour chaque affirmation supplémentaire du document, vérifier séparément son
soutien ; l'absence dans un petit échantillon ne prouve pas qu'elle est inventée.

| Dimension | Vérification humaine | Mesure possible après annotation |
|---|---|---|
| Couverture des thèmes | Le sujet précis est-il effectivement restitué ? | Thèmes fidèlement représentés / thèmes de référence évaluables, sur l'échantillon seulement |
| Informations importantes | Le contenu, la portée et la modalité sont-ils conservés ? | Comptes fidèles, déformés, absents et incertains ; importance déclarée dans la référence |
| Attribution | L'auteur est-il établi et correctement nommé ? | Attributions correctes / attributions évaluables ; inconnues et identités ajoutées comptées à part |
| Inversions | Qui agit, qui subit, négation, question, avis cité ou anecdote ont-ils changé ? | Nombre d'erreurs par catégorie, avec extrait et phrase concernés |
| Regroupement | Les phrases portent-elles sur le même objet et conservent-elles les oppositions ? | Groupes cohérents, mélanges injustifiés et arguments isolés, avec motifs humains |
| Rédaction | Les paragraphes sont-ils compréhensibles, concis et cohérents ? | Appréciation humaine motivée ; ne pas la confondre avec la fidélité |

Conserver les dénominateurs, les cas incertains et les motifs. Ne pas calculer
un taux global sur les 670 passages à partir de ces seuls huit minutes. Les
omissions importantes de toute la réunion exigent une annotation complémentaire
du reste de l'enregistrement. L'avis du même Qwen ne sert jamais de référence.

## 3. Interpréter les temps séparément de la qualité

Le benchmark natif distingue CPU utilisateur/noyau, temps écoulé, appels neufs
et reprises. « À froid » désigne ici des réponses applicatives absentes et des
processus neufs ; le cache disque Windows n'est pas purgé. Le poste n'est pas
isolé des tâches de développement.

Le registre antérieur de 0.2.4 a déjà été préparé et contrôlé : son rejeu de
rédaction seule exclut ce coût. La préparation neuve est une mesure séparée,
sans approbation simulée. Les configurations diffèrent aussi par les paramètres
de décodage et par la longueur de sortie. Une durée plus courte avec moins
d'informations restituées ne démontre pas une amélioration du produit.

## 4. Restitution

Conserver l'identité du relecteur, la date, les empreintes des entrées, les
versions des deux moteurs et les textes évalués. Rapporter les échecs et les
informations non retenues. Tout résultat demeure expérimental tant que les
évaluations nécessaires ne sont pas réalisées. La qualification sur Windows
vierge déconnecté et la qualification commerciale restent distinctes.
