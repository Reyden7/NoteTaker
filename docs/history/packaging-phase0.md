# Livraison à construire après qualification

Livrable contractuel : un seul `NoteTaker-Setup.exe`, incluant tout le nécessaire,
sans premier téléchargement ni Python installé sur le poste client.

Aucun `.spec`, `.iss` ou script prétendant fabriquer ce produit n'est fourni
à ce stade : les backends, le lot légal et sa taille ne sont pas encore figés.
La future chaîne devra appliquer les contrôles ci-dessous avant compilation.

1. Valider des verrous avec hashes pour UI et chaque worker, modèle et DLL.
2. Produire les bundles PyInstaller onedir isolés ; exclure scripts de build,
   accès cloud, DLL ASIO non approuvées, serveurs et exécutables inutilisés.
3. Vérifier l'intégrité de tous les fichiers et les notices de redistribution.
4. Mesurer le volume compressé : Inno impose plusieurs fichiers au-delà de
   4 200 000 000 octets, ce qui viole la contrainte du fichier unique.
5. Embarquer les redistribuables Visual C++ autorisés et les polices nécessaires.
6. Compiler puis signer programme, workers, installateur et désinstallateur.
7. Tester installation, cycle complet CPU, GPU compatible, échecs DLL/VRAM,
   mise à jour, migrations, restauration et désinstallation sur Windows propres.
8. Bloquer réseau système et observer les tentatives pendant toutes les étapes.

Les archives ne doivent pas être supprimées lors de la désinstallation. Les
modèles et binaires du programme seront en lecture seule ; les données sous
LocalAppData ou dans le dossier d'archives choisi. L'espace requis doit intégrer
la copie temporaire, les modèles extraits, les mises à jour et les longues prises.
