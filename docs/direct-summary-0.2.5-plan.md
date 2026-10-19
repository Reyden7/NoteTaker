# Synthèse directe expérimentale — plan 0.2.5

Plan établi le 19 octobre 2026 avant implémentation.

## Diagnostic et périmètre

0.2.4 extrait puis classe/normalise/vérifie des fiches, construit un catalogue,
cherche des relations puis rédige et vérifie plusieurs fois les paragraphes.
Les mêmes sources sont réinjectées dans de nombreux prompts. Les titres
provisoires peuvent être trop généraux ou mal rattachés, malgré un avis Qwen
favorable. La préparation neuve laisse les candidats en attente : les neuf
fiches rédigées du précédent essai provenaient de contrôles antérieurs.

Conserver tous les fichiers, modèles, révisions, attributions et contrôles de
0.2.4. Aucun changement Whisper/sherpa. Aucun modèle supplémentaire, service
réseau ou dépendance. Pas de migration SQLite : le schéma reste v5.

## Données

- Un marqueur explicite identifie une copie de test ; refuser le dossier de
  données habituel. Une option d'exécution autorise seule le nouvel onglet.
- Chaque essai a un UUID et un artefact JSON final immuable, son empreinte,
  un instantané complet des sources/noms/ordre du jour/lexique et son profil.
- Inventaire de toutes les sources, y compris blancs/fragments, avec citations,
  résidus, sujets proposés, candidats, rejets, omissions et alertes. Les comptes
  de citations ne sont pas une couverture sémantique.
- Un brouillon expérimental référence son artefact et l'empreinte des entrées.
  Les contrôles existants de sources, révision et relecture restent nécessaires.
  Toute référence altérée, extérieure au dossier ou obsolète est refusée.
- Le registre 0.2.4 n'est ni écrasé ni automatiquement approuvé. Les documents
  existants sans nouvelle provenance gardent leur contrat.

## Moteur et services

1. Contextes de plusieurs minutes, bornés par le budget réel de caractères,
   avec tours de parole et citations remappables jusqu'aux segments audio.
   Aucun premier/dernier N passages sélectionné pour accélérer le calcul.
2. Un appel par contexte produit directement des sujets et phrases sourcées :
   contexte, arguments, divergences, propositions, décisions potentielles.
   Priorité aux points distincts de l'ordre du jour ; un point général unique
   est un cadre, pas une justification pour fusionner tous les échanges.
3. Un plan global réutilise les phrases intermédiaires et leurs IDs pour les
   regrouper/ordonner, sans réécrire une nouvelle fois chaque information.
   Tout candidat non retenu doit recevoir une disposition explicite.
4. Contrôles statiques sur toutes les phrases, puis contrôle Qwen groupé des
   sujets et des affirmations importantes : chiffres, négations, citations
   d'autrui, questions, propositions, relations et attributions incertaines.
   Pas de chaîne systématique classification → réécriture → quatre contrôles
   → réécriture de paragraphe pour chaque fiche.
5. Les décisions potentielles restent des alertes : aucun vote ni acte métier
   n'est déduit. Les noms viennent des attributions enregistrées ; les autres
   voix restent anonymes. Un avis machine n'est jamais une vérité terrain.
6. Un service dédié conserve le résultat et le brouillon sous transaction et
   contrôle de concurrence, sans changer le service de génération habituel.

## Interface de test

Onglet visible seulement avec activation explicite sur copie marquée : lancer,
consulter les paragraphes et sections, alertes prioritaires regroupées par
sujet, inventaire intégral et lecture des sources. L'éditeur habituel et sa
relecture finale demeurent utilisés. Aucun écran ne demande d'approuver
individuellement toutes les fiches de l'ancien registre.

## Profilage et comparaison

Journal par étape/appel : temps écoulé, CPU utilisateur/noyau, appels réellement
exécutés, reprises, volumes d'entrée/sortie, contexte/budgets et empreintes des
poids/runtime. Mesurer le CPU des processus natifs, pas seulement Python.
Un essai à froid applicatif commence avec un répertoire de réponses vide et
sans cache KV ; le cache disque du système n'est pas vidé. Les reprises sont
un mode séparé, jamais annoncées comme de nouvelles inférences.

670 mêmes passages et mêmes attributions, lus depuis l'instantané figé, sur
copies isolées. Les inférences comparées sont séquentielles. Distinguer :

- préparation neuve 0.2.4, avec ses candidats en attente et son éventuelle
  impossibilité de rédiger sans intervention ;
- rédaction 0.2.4 depuis le registre antérieurement contrôlé, préparation et
  coût humain hors mesure, explicitement déclarés ;
- chaîne directe expérimentale complète et reprise de ses intermédiaires.

Comparer temps/appels/sujets/alertes et les échecs conservés. Les qualités de
regroupement, fidélité et omissions importantes exigent une référence humaine.
Préparer un petit corpus d'extraits et un formulaire d'annotation indépendant,
sans préremplissage Qwen, avec identité du relecteur et confirmation explicite.
Tant qu'il n'est pas annoté et évalué, laisser les scores indisponibles.

## Tests et livraison

Tests de conservation exhaustive des sources, segmentation, priorisation de
l'ordre du jour, rejets, noms/voix, risques, inventaire et regroupement sans
perte d'IDs ; provenance/concurrence/altération/relecture/export et widgets.
Profilage réel de sous-processus Windows, puis rejouages natifs documentés.
Conserver le bundle 0.2.4 ; compiler éventuellement un bundle de test distinct.
Les qualifications qualité, Windows vierge déconnecté et commerciales restent
ouvertes, sans déclaration de gain avant mesures et annotations indépendantes.
