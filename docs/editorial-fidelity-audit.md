# Passe de fidélité rédactionnelle — 22 octobre 2026

## Périmètre et preuve

Corpus inchangé : séance `58709d31-6b8f-434e-ac75-73871d745298`,
36 passages, 336,039 secondes. Base de départ :
`output/editorial-report-20261022/8dff6d5d126847028ad24943e45f9ade/municipal-run-04/session-copy/`.
L'ancien document de comparaison est **livrables-v4**, pas un essai antérieur.
Toutes les nouvelles révisions sont réalisées sur une sauvegarde SQLite séparée :
`output/fidelity-20261022/retained-5d5d5b0e/`.

L'audit de l'agent porte sur la **transcription conservée**, les citations exactes
et leurs horaires. Il ne comporte pas de nouvelle écoute certifiée de l'audio.
Les noms des deux intervenants proviennent des attributions humaines existantes.
Aucune référence humaine exhaustive ne permet de mesurer un gain de fidélité.

## Causes observées

- Un titre de classement généré était réinjecté comme sujet de rédaction. Des
  intitulés interprétatifs pouvaient induire une analyse absente des propos.
- Chaque phrase héritait des références du paragraphe entier. Une source citée
  apparaissait couverte même si une partie importante n'était pas reformulée.
- L'audit Qwen accepte parfois des ajouts ou des inversions de sens. Son accord
  n'est donc pas une preuve indépendante de fidélité.
- Des conclusions ajoutées après « ce qui… », ou des propositions participiales,
  pouvaient contaminer une proposition initiale correcte.
- Les limites « pas forcément » et « pas à chaque fois », ainsi que les pronoms
  désignant l'ancienne équipe, étaient mal conservés.
- Une allusion « votre mentor » pouvait devenir une relation personnelle établie,
  voire être rattachée par erreur à l'auteur de l'intervention.

## Modifications retenues : contrat éditorial v5

1. Inventaire **avant rédaction** par sujet et voix, conservant les passages
   attendus et les sources non classées. Rapprochement après contrôles, avec les
   sources non citées et les noms évoqués non repris. Ces indicateurs ne sont
   pas des mesures de couverture sémantique.
2. Rédaction en paragraphes au discours indirect. Le titre de classement n'est
   plus fourni au rédacteur comme preuve. L'essai de sortie obligatoire phrase
   par phrase a dégradé le style et n'est pas activé dans le parcours principal.
3. Contrôles distincts sur les phrases et certains ajouts détachables. Les ajouts
   rejetés restent dans le rapport ; une proposition fidèle voisine peut subsister.
   Les sources et leurs horaires restent liés à chaque affirmation et phrase.
4. Refus ciblés des erreurs réellement observées : fréquence historique ajoutée,
   « histoire classique » transformée en histoire institutionnelle, changement
   d'équipe, inversion de « gestion courante », accusation ou violation renforcée,
   affiliation personnelle affirmée, référent de communication attribué aux
   associations, explications ou qualifications ajoutées, identifiants techniques
   échappant dans la prose.
5. Reprises contrôlées de quelques **expressions explicites**, avec les mêmes
   citations, contrôles de sources et audit machine que les propositions Qwen :
   comparaison de communication municipale/régionale avec personnalité citée ;
   vente qualifiée de gestion courante ; pratique historique non systématique ;
   demande de réponse et absence de réponse ; légitimité des élus minoritaires ;
   choix associatifs explicitement assumés ; omission occasionnelle de chiffres
   en conseil municipal ; défense de sa gestion par les valeurs revendiquées.
   Une omission dans un exposé oral ne devient pas une omission dans un acte
   juridique. La défense reste attribuée et n'est pas une certification de probité.
   Ces gabarits sont signalés par leur
   méthode dans l'inventaire : ce ne sont pas des reformulations attribuées à Qwen.
   Ils ne s'appliquent pas en l'absence des marqueurs requis ou en reliant deux voix.
6. La demande au maire devient une demande d'explication, sans inventer le
   contenu d'un programme politique absent. Présentation des sujets selon leur
   premier passage ; ordre des affirmations selon leurs sources. Le renvoi vague
   à « l'intervention précédente » est retiré lorsqu'un regroupement thématique
   lui ferait désigner un autre paragraphe.
7. Présentation versionnée des civilités : `madame maximi` → `Madame Maximi`,
   `moniseur sineux` → `Monsieur Sineux`. Aucune nouvelle identité ou prénom
   n'est déduit. Les libellés stockés, anciennes révisions et annotations restent
   inchangés. Le schéma accepte ce style optionnel ; une nouvelle attribution
   continue d'invalider les anciennes liaisons de noms.
8. Notes brèves dans le brouillon ; diagnostic, incertitudes de transcription,
   refus et citations intégrales dans le rapport séparé. Les empreintes vocales
   demeurent désactivées. L'export officiel exige toujours une relecture humaine.

Le cache reprend les candidats les plus récents avant les anciens fichiers
amorces. Chaque résultat reste soumis à la vérification de son identité exacte
(consigne, schéma, modèle et binaire). Un cache périmé ne peut autoriser une sortie.

## Repères de contrôle ciblés

| Passage audio | Vérification à conserver |
|---|---|
| 00:14.900–00:31.780 | « Déjà vu » des délibérations et « pas forcément en grand débat » ne décrivent pas une histoire générale de la collectivité. |
| 00:31.800–00:50.000 | 200 000 € de recettes comparés par Mme Maximi à 300 000 € pour rallumer l'éclairage : pas un déficit comptable établi. |
| 01:29.900–01:58.980 | Laurent Wauquiez, panneaux et comparaison avec la région ; pas de mentorat ou de position politique établi par le logiciel. |
| 01:59.240–02:22.180 | Critique de l'annonce avant délibération ; pas de constat juridique indépendant. |
| 02:22.180–02:47.040 | Demande au maire de préciser ses intentions pour la ville ; aucune politique concrète à inventer. |
| 02:47.920–03:05.100 | RESS non développé ; absence de réponse alléguée et légitimité des élus à poser des questions. |
| 03:43.960–03:54.060 | La vente des 22 véhicules est qualifiée de gestion courante ; l'inversion de cette position est refusée. |
| 03:54.060–04:27.080 | Dates des ventes précédentes ; conférences de presse et délibérations **avec débat** non systématiques. Pas d'absence générale de délibérations. |
| 04:27.080–05:21.620 | Défense contre une insinuation, probité revendiquée et choix associatifs assumés : pas de certification objective de gestion. Le référent de « opération de com' » ne doit pas devenir le soutien aux associations. |

## Tests et état de qualification

**436 tests réussis en 14,17 s**, dont les régressions de portée, d'inversion,
de conservation des sources, de noms versionnés et de reprise du cache.
Preuve : `output/fidelity-20261022/retained-5d5d5b0e/tests-final-source.xml`.
Les réponses simulées dans les tests unitaires sont des fixtures explicitement
identifiées ; elles ne mesurent pas la qualité de Qwen. Les recettes natives et
leurs fichiers de sortie sont conservés séparément.

Les essais intermédiaires `919af43a` et `final-05cd82e9` sont archivés. Le premier
a été interrompu. L'essai phrase par phrase a abouti mais n'a pas été retenu.
La première rédaction en paragraphes du répertoire `retained-5d5d5b0e/livrables`
a révélé encore des inversions ; elle reste conservée comme preuve, sans être
présentée comme le livrable corrigé. La reprise `livrables-final` interrompue
est également conservée. `livrables-controlees` conserve l'avant-dernier résultat
ayant permis d'identifier les dernières corrections de contexte. La livraison
à relire est dans **`a-relire`**, copie vérifiée des exports du dernier job
`0792ebe9-678a-4d19-84ae-323ce463610a`. Aucun nom de répertoire ne constitue une
validation officielle du document.

## Résultat de la recette finale

- **9 rubriques et 17 affirmations** : 11 reprises déterministes de sources
  explicites, 6 propositions Qwen retenues. Le résultat n'est pas attribué à
  une amélioration générale de Qwen. Les essais phrase par phrase ont été écartés.
- PDF : **2 pages** ; DOCX : **2 pages dans Word**. Toutes les pages rendues
  ont été inspectées, sans débordement visible. Le rendu LibreOffice a échoué
  (`soffice.exe` absent) ; Word a servi uniquement à la vérification locale en
  lecture seule, avec conservation du SHA-256 du DOCX.
- **251,294 secondes écoulées avec cache**, dont trois inférences de contrôle
  neuves : 95,969 / 80,579 / 71,432 s. Les rédactions intermédiaires exactes ont
  été réutilisées. Ce n'est ni un temps complet à froid ni un gain de vitesse
  mesuré ; temps CPU cumulé et pic mémoire non mesurés dans cette passe.
- Comparaison SQL : données des séances, voix, textes, prises, annuaire,
  participants, annotations, historique et registre inchangés. Anciens brouillons
  conservés et aucune nouvelle validation humaine. Export officiel refusé.
  Fichiers de référence et audio normalisé inchangés par SHA-256.
- **21 sources rattachées, 7 à reprendre, 3 formules de séance et 5 non classées**.
  Ces comptes de liens ne mesurent pas la couverture du sens : une source citée
  peut contenir un argument non repris. La matrice conserve cette distinction.

Le rapport `a-relire/Rapport-audit-et-comparaison.md` compare chacun des neuf
anciens paragraphes au nouveau résultat. `comparaison-paragraphes.md/.json`
conserve tous les textes et les citations/horaires par phrase ;
`delivery-checks.json` contient les contrôles de conservation et de rendu.
Le lanceur `a-relire/Ouvrir-recette-fidelite.cmd` ouvre la copie et son brouillon
calculé, sans remplacement du bundle installé.

Deux arguments importants restent à reprendre après écoute : la contestation
conditionnelle des insinuations à 04:27.080–04:46.280 et la critique de la
communication envers les citoyens à 05:21.900–05:32.800. Le second était présent
dans l'ancien document : sa disparition est explicitement signalée, sans annoncer
une amélioration globale de couverture. Le rapport propose une formulation à
relire, sans la réintroduire ou l'approuver automatiquement.

Pas de changement des moteurs audio, des modèles, des références du laboratoire,
des protections de relecture ou des exports officiels. Aucun téléchargement,
aucune migration SQLite et aucun nouveau bundle installable dans cette passe.

## Limites

Les contrôles sont ciblés ; ils ne constituent pas un système général de preuve
du sens. Une citation peut encore couvrir davantage de texte que la phrase
rédigée. Les gabarits explicites ne couvrent pas toutes les formes de discussion.
Les propos ambigus et les arguments non repris demeurent consultables, sans
être réintroduits automatiquement par supposition. La date et le titre de la
copie de recette sont des métadonnées techniques : leur adéquation à la réunion
doit être vérifiée avant un usage municipal. Aucune validation officielle ni
mesure du nombre de corrections humaines nécessaires n'est annoncée.
