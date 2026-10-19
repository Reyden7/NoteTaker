# Synthèse thématique 0.2.3

## Pourquoi le compte rendu 0.2.2 restait fragmenté

La chaîne précédente sélectionnait au plus quatre notes par bloc chronologique,
reformulait chaque note dans une phrase courte, contrôlait ses citations puis
regroupait ses IDs par thème. `assemble_summary` imprimait ensuite chaque note
dans son propre paragraphe, précédée de « Position », « Argument », etc. Le
regroupement ne rédigeait donc pas un texte transversal. Le plafond de 250
caractères et la reformulation à partir des seules citations courtes pouvaient
faire perdre le contexte interrogatif, personnel ou rapporté. Une citation
exacte et une même voix ne suffisaient pas à établir le sens de la reformulation.

Le brouillon du dernier test contient sept intitulés et 18 affirmations. Son
analyse qualitative met en évidence des récits personnels et accusations
reformulés comme descriptions générales. Ce constat de code et de formulation
ne constitue pas une mesure annotée de fidélité ou un taux d'erreur.

## Nouvelle chaîne locale

`engines/topic_summary.py` est appelé par le worker `task=summary`. Les helpers
de citations, de contexte, JSON contraint, cache vérifié et lancement llama CPU
de `hierarchical_summary.py` sont réutilisés. L'ancienne chaîne demeure lisible
pour les anciennes preuves et tests ; elle n'est plus le moteur de rédaction
de l'interface. Le modèle, sa quantification et ses licences ne changent pas.

1. Regrouper prudemment les tours d'une voix dans des unités conservant les
   positions exactes des passages. Découper en fenêtres de quatre minutes
   maximum, indépendamment limitées à 8 000 caractères, avec contexte partagé.
2. Sélectionner citations et notes de tous les intervenants, sans nouveau nom.
   Résoudre les références par citation exacte dans la même voix. Une référence
   ambiguë est rejetée, jamais devinée dans la séance entière.
3. Classifier le propos original dans une passe dédiée, à partir des citations
   et des tours voisins. Distinguer propos direct, question, avis d'autrui
   cité/critiqué et récit personnel, avec des catégories françaises explicites.
   Une citation clairement interrogative ne peut pas recevoir le genre
   proposition ; sans marque de recommandation, ce genre n'est pas proposé au
   modèle. Puis reformuler dans un autre appel, avec les citations et la nature
   contextuelle du propos, sans transmettre les détails factuels des passages
   voisins. La rédaction ne peut pas emprunter une date ou un fait au contexte.
   Citations, voix et IDs restent inchangés. Le test réel puis la fixture du
   bundle ont confirmé la nécessité de séparer ces tâches : le modèle confondait
   encore style indirect et avis cité d'autrui. Les sorties refusées sont conservées.
4. Vérifier les notes dans une autre passe : soutien du sens, modalité, auteur
   de l'avis et relation. Les règles déterministes refusent notamment question
   devenue assertion, anecdote devenue proposition et avis rapporté attribué
   sans précaution au locuteur. Un verdict incertain écarte la note.
5. Établir un catalogue de thèmes global, sans les titres provisoires des notes.
   Puis affecter chaque ID à un sujet par une clé obligatoire du schéma JSON.
   Les facettes d’un même projet et les passages éloignés peuvent ainsi être
   réunis. Contrôler absence de doublon/omission. Une limite de
   contexte provoque un refus explicite, pas une réduction silencieuse des sources.
6. Rédiger un paragraphe cohérent par sujet depuis son dossier d'arguments et
   citations, en articulant raisons, réserves, propositions et désaccords étayés.
   Un accord exige plusieurs voix et une expression explicite ; une proximité
   d'opinion ne devient pas un consensus. Aucune décision ou résultat de vote
   n'est généré. Chaque phrase référence ses notes ; les notes non reprises
   sont comptabilisées par différence d’ensembles, avec un statut de non-sélection
   ou de fiabilité insuffisante. Aucun motif éditorial n’est inventé par le code.
   Les notes sont présentées par voix ; les phrases peuvent réunir plusieurs notes.
   Une reprise sans alias est permise seulement par une anaphore contrôlée,
   depuis la même voix unique dans la phrase précédente, avec liaison de voix
   stockée et recontrôlée après correction.
7. Vérifier les phrases contre leurs sources sur les quatre axes. Les extraits
   de la vérification de paragraphe portent leurs horaires ; l’ordre complet
   des phrases est transmis uniquement comme contexte de relation, jamais
   comme preuve de fait. « Conteste cette affirmation » exige les sources de
   deux voix. Une référence courte non résolue comme « cette prétention » est
   écartée du dossier de rédaction et signalée. Les propos éloignés ne sont
   pas présentés comme des répliques directes par leur seule juxtaposition. Le titre
   nominal a un contrôle dédié : objet étayé, absence d’allégation non étayée
   et absence d’identité/décision inventée. Tous ses verdicts doivent passer.
   Il n’est pas traité comme une phrase prononcée par un intervenant. Les
   catégories de relation des phrases sont dérivées des notes citées, jamais
   forcées à « affirmation » pour une proposition ou une question. Le contexte sert à invalider une interprétation, jamais à
   justifier un détail absent des seuls passages cités. Si une phrase échoue,
   refuser le paragraphe entier et tenter
   une nouvelle rédaction avec le diagnostic. Après deux échecs, signaler le
   sujet non rédigé. Si aucun sujet ne passe, conserver l'ancien brouillon.

La sélection est bornée à six notes par fenêtre : une transcription intégrale
reste nécessaire pour vérifier les omissions et la couverture. La synthèse
n’est jamais annoncée exhaustive.

Les essais natifs ont aussi exposé des faux positifs : un budget global
rattaché à la toiture, une absence d’évaluation ajoutée au récit, une
interrogation suivie d’une assertion et une affiliation de parti absente des
citations. Le code ajoute des refus déterministes sur ces formes observées.
Les montants monétaires doivent reprendre une phrase financière source
littérale entre guillemets, en plus de la vérification sémantique ; sinon la
note ou la phrase est refusée. Ce choix conservateur peut supprimer des
informations financières pourtant reformulables et n’est pas une preuve de
fidélité exhaustive des autres chiffres. Les noms propres nouveaux sont
contrôlés contre les mots cités ; une graphie canonique du lexique n’est
autorisée que si une de ses variantes est effectivement dans la source.
Un modèle peut encore manquer une erreur hors de ces motifs. La relecture
humaine ne peut pas être remplacée par ces règles.

Les contrôles sont des passes distinctes du même modèle : leurs erreurs peuvent
être corrélées. « supported » reste une opinion machine et ne vaut ni vérité
des propos politiques ni validation humaine. Les sorties brutes, refus, motifs
d'omission et citations sont dans le dossier privé du job, jamais dans le payload.
Les essais ont aussi montré des erreurs de classification avec un contexte
chargé de longs UUID et de micro-fragments. Le contexte de reformulation et de
vérification réunit les fragments contigus d'une voix en gardant leurs IDs ; les
champs de voix sont représentés par alias dans le prompt, sans substitution
dans le texte des citations. Les coordonnées stockées ne changent pas. La
représentation plus compacte n'est pas présentée comme un gain mesuré de
fidélité. Le cache exige la même identité de prompt, schéma, budget de sortie,
modèle et binaire avant de réutiliser une réponse.

## Noms, lexique et longueurs

Les prompts de rédaction emploient des alias `{{V1}}`, etc. L'application les
remplace par les libellés confirmés manuellement dans la séance, notamment les
noms issus des participants de l'annuaire. Elle respecte leurs instantanés
historiques. Une voix sans nom confirmé devient « Voix N » ou « Voix inconnue ».
Le modèle ne reçoit aucune identité supposée à attribuer. Ses liens d'alias
doivent correspondre aux voix des notes citées par la phrase.

Dans Séance, **Lexique local de la séance…** permet les graphies retenues et
variantes, une entrée par ligne : `Médiathèque Simone Veil | Simone Veille`.
Les entrées sont validées et stockées localement dans les métadonnées SQLite.
Le lexique est transmis comme aide orthographique, sans valeur probante ni
identification de voix. Il ne modifie ni la transcription ni les citations.

Le mode **Transcription intégrale** conserve le texte et les horodatages ; aucun
appel Qwen n'est nécessaire. Le **Compte rendu synthétique** utilise les
paragraphes thématiques. Le mode PV municipal garde la relecture par le secrétaire
et les décisions/votes saisis séparément.

Trois budgets maximaux indicatifs par sujet : courte, environ 65 mots ; standard,
environ 120 mots ; détaillée, environ 200 mots. Ce ne sont pas des quotas à remplir, ni une coupe
brutale de texte ou une garantie de nombre de pages. Les omissions de notes
sont auditées et signalées. La longueur est mémorisée par séance ; le mode
transcription désactive ce réglage et reste intégral.

## Traçabilité et modifications humaines

Chaque point conserve `claims` et `sources` et ajoute `narrative` : texte de
phrase, IDs des notes, gabarit à alias, liaisons de voix et verdict machine
provisoire. Le texte imprimé doit correspondre à ces phrases, chaque note du
point doit être rattachée et chaque alias rester lié à une voix source. Les
anciennes révisions sans `narrative` restent prises en charge.

**Consulter les extraits sources…** ouvre désormais une navigation phrase →
note → citation/horodatage → lecture du passage. Les sources non consécutives
restent distinctes. Une modification de nom requiert l'actualisation explicite
déjà introduite en 0.2.2, une prévisualisation et une nouvelle relecture.

Une modification volontaire de prose conserve toutes les références du point
dans une liaison de paragraphe marquée `human_edited_requires_review`. Elle ne
garde aucun verdict machine pour le nouveau texte. Une correction d'affirmation
prévisualise sa recomposition et conserve les autres notes. Les anciennes
révisions gardent le détail antérieur. Une scission/fusion de source remappe les
citations sans perdre les IDs des notes ni leurs liaisons aux phrases.

Les mécanismes de relecture, contexte, votes et exports restent obligatoires.
Aucun texte nouveau n'hérite d'une approbation. Aucun résultat de comparaison
n'est approuvé dans la séance réelle. Le schéma SQLite reste v4 ; le schéma
JSON du document est étendu de façon optionnelle. Utiliser 0.2.3 pour les
nouveaux brouillons : un ancien exécutable peut refuser ces propriétés JSON.

## État des essais

La comparaison réelle est exécutée sur un instantané en lecture seule du
dernier test : 670 passages, dernière parole à 20 min 37,580 s, audio préparé
référencé de 20 min 40,017 s. Le fichier utilisateur n'est pas tronqué pour
obtenir artificiellement 20 minutes. Même transcription et mêmes corrections,
aucun nouveau calcul Whisper/sherpa. Le brouillon 0.2.2 enregistré sert de
référence de forme ; il n'est pas une référence humaine annotée de vérité.

Les résultats finaux et le PDF de comparaison sont consignés après achèvement
dans `evidence/topic-summary-standard.json` et `evidence/topic-comparison-pdf.json`.
Le PDF est un rapport technique distinct de l'export de production, marqué
non validé sur chaque page et accompagné d'une annexe de citations/horodatages.
La validation humaine du nouveau compte rendu reste à effectuer.

Les essais interrompus volontairement ont arrêté uniquement les processus
natifs créés pour ces tests. Leur statut LLAMA_NATIVE_PROCESS_FAILED ne doit
pas être interprété comme un plantage spontané. Les caches stricts permettent
de reprendre les appels inchangés ; les durées de reprise ne sont pas des
benchmarks complets de performance.

Les premiers essais arrêtés sont dans `topic-summary-initial-stopped.json` et
`topic-summary-before-contextual-rewrite.json`. Le premier bundle a effectivement
refusé sa synthèse sur fixture après les erreurs de typage/copie ; preuve
`bundle-topic-before-contextual-rewrite.json`. Les contrôles n'ont pas été levés.

Les tests pytest sont dans `evidence/pytest-topic-summary.xml`. Les sept contrôles
textuels construits pour les erreurs connues ont été réellement passés à Qwen
CPU : cinq reformulations non étayées refusées, deux contrôles fidèles acceptés
(`topic-verifier-controls.json`). Ce ne sont ni un corpus aveugle ni les
annotations humaines du débat ; aucun pourcentage de fidélité réelle n'en est déduit.

La recette sur Windows vierge déconnecté, les autorisations de redistribution
native et le Setup commercial restent non validés. Aucun développement biométrique.


### Contrôle final des rôles et citations

L’inspection de la première comparaison a détecté une inversion encore
acceptée par Qwen : les ministres qui « ne nous écoutent pas » étaient devenus
ceux qui « ne sont pas entendus ». Un contrôle ciblé de ce motif interdit cette
inversion. Le dossier d’arguments peut tenter une seule reformulation réparée
à partir des mêmes citations, avec une nouvelle vérification sémantique sur
les quatre axes ; un refus écarte la note. Cette réparation tardive conserve
le plan thématique déjà établi et tous les identifiants source. Le texte
rejeté et le contrôle de réparation restent audités séparément.

Toute citation entre guillemets français dans le paragraphe doit aussi
reprendre le texte cité, sans transformation de « ils les insultent » en
« insultés ». Une paraphrase peut être indirecte, mais pas déguisée en citation
littérale. Ces contrôles couvrent les erreurs observées, sans prétendre
résoudre l’ensemble des ambiguïtés de rôles ou de discours rapporté.

## Résultat final de la comparaison

Sur les mêmes 670 passages de 20 min 40,017 s : 6 paragraphes, 12 phrases
sourcées, 1 730 caractères (ancien document : 7 points, 2 830 caractères).
Un sujet est refusé et signalé ; 3 notes acceptées ne sont pas reproduites,
dont 2 dans ce sujet. Les 21 candidats rejetés ne constituent pas un dénominateur
permettant de calculer une précision. La dernière reprise a exécuté 5 appels
natifs en 212,362 s ; les autres réponses proviennent du cache strict. Ce
n'est pas une mesure complète à froid. Le PDF final de 8 pages a été rendu
et chaque page inspectée, sans débordement observé. L'annexe conserve les
citations et les horaires, sans conférer une approbation factuelle au document.

Les formulations maladroites, la couverture incomplète, les sujets parfois
trop fins et certains termes incertains de transcription restent à revoir.
Le mot « prélèvement » n'a pas été remplacé par un nom supposé. Aucun gain
de fidélité n'est mesuré. La copie de relecture isolée préserve l'historique ;
son nouveau brouillon reste non approuvé et l'export normal est bloqué.
L'audio original et l'instantané SQLite sont inchangés.

175 tests passent. Le bundle final est compilé ; démarrage/fermeture Qt et
workers CPU réussissent. Whisper/sherpa sont recalculés sur la fixture ; le
dernier contrôle Qwen compilé réutilise 9 réponses natives dont l'identité est
vérifiée, avec 0 nouvel appel. La preuve du précédent calcul Qwen compilé
frais (352,302 s, avant les derniers contrôles conservateurs) est conservée.
`evidence/topic-summary-release.json` lie les empreintes des exécutables, les
modules gelés, les sources, les tests et le PDF inspecté. Les réserves de
commercialisation et de recette Windows vierge déconnecté restent ouvertes.
