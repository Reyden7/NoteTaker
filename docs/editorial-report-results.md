# Compte rendu automatique par sujet — recette du 22 octobre 2026

## Conclusion

Le parcours produit un nouveau brouillon éditable sans approbation des fiches.
Les citations longues et les diagnostics internes sont séparés du document de
lecture. Plusieurs arguments auparavant absents ou seulement cités sont repris.
**La fidélité reste insuffisamment qualifiée** : des généralisations demeurent,
la comparaison avec Laurent Wauquiez n’est pas restituée et certaines nuances
du débat doivent encore être reprises. Ce document n’est pas prêt à devenir un
procès-verbal municipal sans correction et relecture humaine.

Les tests logiciels ne mesurent pas cette fidélité. Aucun score de précision,
gain sémantique quantifié ou nombre de corrections humaines n’est annoncé.

## Données et méthode

Preuves locales : `output/editorial-report-20261022/8dff6d5d126847028ad24943e45f9ade/`.
Livrables retenus : `livrables-v4/Compte-rendu-BROUILLON.pdf` et `.docx`.
Ancienne version conservée :
`output/automatic-report-20261021/470f7221d5eb4cd0974963bf81f4e64d/delivery-final/`.

Même séance `58709d31-6b8f-434e-ac75-73871d745298`, mêmes **36 passages** et même
audio municipal de **336,039 secondes**. SHA-256 du WAV :
`9ca9933350c0b0e57f50347d49b58b7f7f9ae33b3e174cc6f99e593cebb59da2`.
Whisper et les moteurs de diarisation n’ont pas été relancés ou modifiés.
Qwen 4B Instruct local et le binaire CPU existant sont conservés. Aucun modèle
téléchargé, aucune identification vocale nominative activée.

La comparaison ci-dessous est une analyse des textes et des références conservées,
effectuée par l’agent de développement. Ce n’est **ni une nouvelle écoute humaine
certifiée ni une référence humaine indépendante** du contenu municipal. Les noms
de voix proviennent des attributions manuelles déjà enregistrées.

## Causes et corrections

- Le contrat v3 imposait trois à six paragraphes et sélectionnait en une étape
  contenu, sujet et sources. Il donnait « La personne… » comme exemple. Les refus
  devenaient des citations brutes dans le document ; les raisons techniques se
  retrouvaient dans `to_verify`, donc à l’impression.
- Le contrat v4 reconstruit les tours adjacents d’une même voix, conserve chaque
  segment et son horaire, puis planifie et rédige par sujet. Une consolidation
  et une reprise bornées traitent doublons et passages oubliés. Les classements
  proposés ne modifient jamais les annotations humaines.
- Des ancres textuelles conservatrices séparent questions portant sur un objet
  nommé, demande d’explicitation, défense de gestion et intention de vote explicite.
  Deux formulations simples sont produites par règles depuis les sources
  (demande de précisions et intention), **pas présentées comme une extraction Qwen**.
  Aucun résultat ou vote favorable n’est déduit de « je vais la voter ».
- Les phrases sont contrôlées séparément avant regroupement : une extrapolation
  ne supprime plus automatiquement sa voisine étayée. Les sous-phrases ambiguës
  restent dans le rapport. Les contrôles de source, auteur, nombres et modalités
  existants sont conservés, complétés par les cas réellement observés.
- Un avis Qwen favorable a encore accepté des détails absents. Les garde-fous
  ciblés ont notamment écarté déficit, absence de toute faute, accusations
  présentées comme avérées, gouvernement substitué à l’équipe municipale,
  critique intensifiée et rattachements ambigus aux associations.
- Les notes Qwen peuvent elles-mêmes contenir une interprétation non étayée :
  elles restent dans le rapport détaillé. Le document contient des vigilances
  courtes par sujet, les sources complètes sont accessibles depuis l’application.
- Le bouton de rapport sélectionnait le **plus ancien** job, alors que la base
  renvoie les jobs par ordre décroissant. Il ouvre désormais le dernier traitement
  automatique réussi, y compris après un essai échoué. Un test UI le reproduit.

Architecture et protocole : [editorial-report-plan.md](editorial-report-plan.md).
Aucune migration SQLite ; nouveau brouillon ajouté à l’historique, sans relecture
créée. Aucune règle d’export officiel assouplie. La présentation compacte ne
concerne que les documents du contrat éditorial v4.

## Comparaison de présentation

| Propriété effectivement observée | Ancien brouillon | Nouveau brouillon |
| --- | ---: | ---: |
| Points ou rubriques | 7, dont 3 passages de citations | 9 rubriques de sujet |
| Phrases avec affirmations sourcées retenues | 4 | 13 |
| Points de repli en citations brutes | 3 | 0 |
| Occurrences de « La personne » dans le DOCX | 4 | 0 |
| Diagnostic technique imprimé | Oui | Non |
| Pages du PDF livré | 3 | 2 |
| Pages du DOCX rendu par Word | 3 | 2 |
| Validation officielle créée | Non | Non |

Ces nombres décrivent la structure du document, **pas la fidélité ou la pertinence
du regroupement**. Neuf rubriques ne prouvent pas une meilleure synthèse : certains
titres restent longs et plusieurs sous-sujets pourraient encore être réunis.
Les noms sont mieux liés aux sources, mais les libellés d’annuaire sont conservés
tels quels, notamment « madame maximi » et « moniseur sineux ». Leur typographie
et cette faute de saisie nécessitent une correction explicite par l’opérateur.

## Couverture des arguments

La liste de contrôle a été préparée depuis la transcription avant l’issue de
l’essai ; elle n’a pas été ajoutée aux annotations humaines ni utilisée comme
un score de vérité terrain.

| Argument à examiner | Ancien document | Nouveau document et réserve |
| --- | --- | --- |
| Ventes présentées comme gestion courante | Peu explicite | Repris pour Sineux ; l’historique formulé par Maximi reste trop général |
| 200 000 euros de recettes comparés à 300 000 euros d’éclairage | Repris | Repris avec les deux montants ; comparaison attribuée, aucun bilan comptable validé |
| Véhicules amortis et tractopelle de 1997 | Année dans une formulation mêlée aux « motions » | Deux phrases, modalité de coût conservée ; expression « motions » écartée à écouter |
| Intention de voter la délibération | Absente | Reprise depuis la formulation explicite, sans « pour », « contre » ni résultat |
| Comparaison de communication avec Laurent Wauquiez | Reprise partiellement | **Absente de la prose finale**, sources s14-0 et s16-0 à reprendre ; pas secondaire par défaut |
| Communication avant délibération | Reprise | Rubrique dédiée ; conserver le statut de critique de l’intervenante |
| Demande d’explication du projet politique | Absente | Rubrique dédiée et demande de précisions ; les scénarios ironiques ne deviennent pas des fonctions réelles |
| Questions sur RESS | Longue citation | Demande de réponse et légitimité de l’opposition reprises ; absence de réponse à l’adjointe insuffisamment explicitée |
| Ventes antérieures et absence de débat systématique | Longue citation | Gestion courante et quatre dates reprises ; **nuance « pas à chaque fois » à réintroduire fidèlement** |
| Défense de la probité et soutien associatif | Longue citation | Deux phrases distinctes, sans « aucune faute » ni soutien associatif présenté comme opération de communication |

**Point connu à corriger dans la première rubrique** : « gestion souvent marquée
par des délibérations peu débattues » généralise « j’ai déjà vu passer des
délibérations, et pas forcément en grand débat ». L’avis Qwen l’a accepté ; cela
illustre précisément la limite des contrôles. Réduire cette généralisation après
écoute, sans modifier la transcription originale.

Le nouvel inventaire comporte **23 passages rattachés à au moins une phrase**,
5 passages de sujet restant à reprendre, 3 formules de séance et 5 passages
non classés. Ce rattachement ne signifie pas que toute l’information d’un
passage est couverte. Inversement, s34-0 n’est pas cité, mais son argument de
gestion courante figure aussi dans s37-0/s38-0 : tous les passages non cités
ne sont pas des omissions sémantiques. Les plages nulles s23-1/s24-0 restent
conservées et ne servent pas de preuve audio valide. Aucun horaire corrigé.

Quantité réelle de corrections humaines nécessaires : **non mesurée**.
Les exemples ci-dessus sont des priorités de relecture, pas un nombre certifié
de retouches ni un gain de productivité.

## Exécutions, performances et échecs conservés

Le dernier job a pris **210,650 s**, dont quatre appels natifs neufs : rédaction
37,428 s et 22,934 s ; contrôles 99,336 s et 47,700 s. Plan, consolidation,
reprise et plusieurs rédactions/contrôles étaient en cache. **Ce n’est pas un
benchmark complet à froid**, ni du temps CPU cumulé. Le réglage reste CPU,
quatre threads ; la mémoire maximale de toute la chaîne n’a pas été mesurée ici.
La retouche de pagination a réutilisé le brouillon sans aucune inférence.

Les essais antérieurs sont conservés : plan JSON tronqué avec répétitions
(369,728 s), classement abusif en détails secondaires, première sélection du
mauvais identifiant de séance (la copie en contient deux), échos de consigne,
contexte de consolidation trop volumineux et annulations de workers inutiles.
Les reprises utilisent maintenant une séance explicitement nommée et des entrées
compactes, sans les métadonnées natives des mots. Aucun de ces essais refusés
n’est présenté comme une synthèse fonctionnelle ou une amélioration de qualité.

## Tests et conservation

Suite finale : **409 tests réussis en 13,06 s**, `test-final-report-ui.xml`.
Cas nouveaux : sources, voix, inconnus, phrases voisines, chevauchement/intervalle
nul, portée des chiffres, intensité, ironie/proposition, exoneration ajoutée,
clauses négatives, doublons de reprise, intentions, demande générique, rapport
UI courant, échec d’inférence et exports compacts contre exports historiques.
Les inférences des tests unitaires sont des fixtures explicitement fictives ;
les appels natifs du municipal sont consignés séparément.

La recette confirme le blocage de l’export officiel sans revue et l’absence de
nouvelle relecture. Comparaisons SQL intégrales des transcriptions, voix, prises,
annuaire, participants, votes, décisions, registre, historique et anciens brouillons
conformes. WAV municipal et références BFMTV WER/DER ont les empreintes attendues.
Voir `delivery-checks.json` et `protected-inputs.json`.

Rendu réel : deux pages du PDF inspectées, deux pages du DOCX rendues avec Word
en lecture seule puis inspectées. Le rendu LibreOffice demandé par l’outil de QA
est indisponible sur ce poste ; ses erreurs restent dans `qa-docx.stderr.log`.
Word sert uniquement à la QA, jamais de dépendance du produit. Captures de
l’interface et du rapport également inspectées.

## Utilisation et recommandation

Lancer `Ouvrir-la-recette-redaction.cmd` dans le dossier de preuves puis choisir
**RECETTE TECHNIQUE GPU VERS RÉDACTION EXISTANTE — À RELIRE**. Le brouillon est
déjà calculé. Le nom technique de séance est conservé par choix de non-altération
des métadonnées ; le document ne contient plus les codes de diagnostic.
Corriger les textes dans l’éditeur, consulter **Rapport de vérification** et
**Écouter les sources**. L’export brouillon reste immédiat ; l’export soumis à
validation garde la relecture humaine explicite.

Conserver cette version en recette. Les règles ciblées améliorent la maîtrise
des refus mais risquent de suradapter ce seul extrait. **Ne pas ajouter indéfiniment
des expressions régulières à la place d’un moteur sémantique fiable** : évaluer
ensuite un modèle local plus capable avec une référence humaine indépendante,
les mêmes sources et un autre enregistrement représentatif. Ne pas choisir un
modèle sur sa taille ou son seul avis sur ses propres réponses.

Pas de nouvelle compilation d’installateur dans ce lot, pas de validation sur PC
vierge déconnecté et pas de qualification commerciale annoncée.
