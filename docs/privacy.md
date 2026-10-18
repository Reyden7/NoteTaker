# Principes de confidentialité et de validation

Le produit traite les séances localement. Il n'effectue aucune transmission
au développeur, télémétrie, récupération de modèle ou authentification cloud.
Les variables d'environnement hors ligne et de désactivation des métriques
sont imposées avant les imports des moteurs. Elles complètent les chemins
locaux obligatoires ; elles ne remplacent pas un audit réseau des bibliothèques
natives et de l'installateur sur VM déconnectée.

Les groupes acoustiques restent limités à une séance. Leurs noms sont attribués
manuellement, depuis du texte libre ou, en 0.2.1, un annuaire civil réutilisable.
Cet annuaire contient prénom, nom, fonction et commune, sans échantillon vocal
ni empreinte permanente. Les vecteurs temporaires nécessaires à la diarisation
ne deviennent pas une base nominative interséances. Le futur assistant vocal est
indisponible ; ses étapes d'intégration restent bloquées avant validation de
l'interface et, pour toute collecte biométrique, du cadre juridique approprié.
Les chevauchements et incertitudes doivent rester visibles.

Les participants d'une séance gardent un instantané de leur fiche et de leurs
présences/rôles/pouvoirs. L'archivage d'une fiche ne supprime pas cet historique.
La base civile et ses sauvegardes restent sous les permissions Windows, sans
chiffrement applicatif à cette étape. Les habilitations avancées, rétention et
coffre prévus dans le plan ne sont pas encore implémentés.

Une sortie de modèle est un brouillon. Les votes proviennent d'une saisie
structurée, les absences restent à compléter, et l'opérateur relit la révision
avant export. Aucune signature, adoption ou approbation officielle n'est déduite
d'une inférence ou d'un clic technique de génération.

Les journaux de production devront contenir uniquement identifiants techniques
non nominatifs, codes d'erreur et mesures de ressources. Pas de texte de séance,
chemins nominatifs, jetons ou audio. Les sorties détaillées des sondes de phase 0
contiennent seulement des fixtures synthétiques et ne constituent pas le système
de journalisation de production. Rétention et accès seront configurables.

Les fichiers locaux et SQLite ne sont pas chiffrés par leur simple stockage.
L'isolation repose initialement sur les comptes et permissions Windows. Le
chiffrement d'archives ou du poste et la gestion des clés restent à étudier.
Les sauvegardes doivent respecter les mêmes protections que les originaux.

Les choix RGPD et de conservation, information des participants, accès,
publication, base légale, responsable du traitement et procédure d'adoption du
PV seront définis avec la collectivité et ses conseils compétents. Aucun délai
de conservation ou contenu juridique obligatoire n'est codé arbitrairement.
