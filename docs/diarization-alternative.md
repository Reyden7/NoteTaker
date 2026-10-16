# Alternative à Community-1

L'utilisateur a choisi d'étudier une autre solution plutôt que d'acquérir
Community-1 via un compte soumis à conditions. La candidate essayée est
**sherpa-onnx 1.13.8 + segmentation pyannote 3.0 ONNX + 3D-Speaker ERes2Net base**.
Elle fonctionne réellement en CPU sous Windows dans l'environnement de développement.

## Droits vérifiés

Le moteur sherpa et la fiche originale des poids ERes2Net sont sous Apache 2.0.
La segmentation pyannote 3.0 est sous MIT ; l'archive de conversion contient
le texte MIT avec copyright CNRS. La documentation officielle sherpa décrit
la combinaison et publie les fichiers ONNX depuis ses releases. Les références
figurent dans `licenses.md` et les métadonnées des releases dans
`evidence/diarization-alternative-upstream.json`.

Le modèle embedding exact est
`3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx` (39 593 761 octets).
Il est entraîné sur de la parole chinoise ; il ne faut pas extrapoler sa qualité
au français depuis la seule réussite technique. Le README du dépôt de code
3D-Speaker ne suffisait pas à conclure sur les poids : leur fiche ModelScope a
été consultée séparément et archivée avec son champ de licence.

Les anciennes releases n'ont pas de SHA-256 publié par GitHub. Les deux hashes
calculés lors du premier accès sont épinglés dans le script d'acquisition et
consignés dans `diarization_models_manifest.json`. Le lot final devra conserver
les fichiers exacts, leur chaîne de provenance et les notices, puis être approuvé.
Ce contrôle ne remplace pas une signature amont absente.

## Test réellement exécuté

Fixture locale : quatre tours A/B/A/B, deux voix SAPI installées distinctes,
texte de discussion municipale fictif, PCM16 mono 16 kHz, 49,59 secondes.
La seconde voix peut être anglophone et parler le texte français avec cet accent.
Le nombre de groupes n'a **pas** été forcé : regroupement automatique, seuil 0,5.

La sortie a trouvé deux locuteurs et la majorité de chaque tour correspond
à speaker_0 / speaker_1 / speaker_0 / speaker_1. Temps mural observé : 6,266 s ;
RSS agrégée maximale échantillonnée : 252 854 272 octets, avec 4 threads.
Les mesures complètes et les plages produites sont dans
`evidence/diarization-alternative-probe.json`. Le test refuse un backend GPU
non qualifié et le routeur lance ensuite le CPU. Ce refus de capacité n'est
pas présenté comme un essai d'inférence CUDA.

Le worker n'a fait aucune tentative de socket Python selon le crochet d'audit.
Ce contrôle n'observe pas les sockets natives ONNX ; la machine n'était pas
déconnectée. Le résultat démontre l'inférence sur fichiers locaux, pas encore
le cycle complet du produit sans réseau.

## Conditions avant choix définitif

Tester deux puis trois voix naturelles françaises, microphones de salle,
échos, voix proches, changements de distance et réunions longues. Les tours
simultanés nécessitent un test explicite et la vérification de la conservation
des attributions multiples. Si l'API globale élimine des chevauchements,
elle devra être complétée par un détecteur de chevauchement ou remplacée.
L'interface devra afficher une attribution incertaine et permettre les corrections.

Aucune identité de personne n'est reconnue ; les noms seront saisis par
l'opérateur. Les vecteurs de regroupement restent limités à la séance et ne
doivent pas constituer des profils vocaux permanents. La qualité de diarisation
n'est pas établie par ce seul essai et aucun DER de terrain n'est annoncé.

## Intégration dans la version 0.1

Le parcours applicatif utilise cette candidate en CPU dans un worker séparé.
Les tours sont rapprochés des passages Whisper ; faible couverture, plusieurs
voix candidates et chevauchement possible restent visibles comme incertitudes.
Un masque supplémentaire emploie les classes powerset du même modèle de
segmentation ONNX pour signaler des intervalles de parole simultanée possibles.
Ce mécanisme n'est pas une séparation de sources et ne reconstruit pas les
paroles que Whisper aurait manquées.

L'opérateur peut écouter le passage, changer/confirmer la voix, saisir les
noms, scinder un passage et fusionner des groupes. L'ancienne attribution et
les corrections sont tracées ; aucun profil vocal permanent n'est créé.
Si sherpa échoue, la transcription Whisper est conservée avec attributions
incertaines et l'audio original reste disponible.

La chaîne des trois moteurs a été exécutée sur la fixture synthétique existante
et le worker sherpa compilé a exécuté l'inférence CPU. La panne de diarisation
et la conservation de l'ASR/audio sont vérifiées par injection de faute.
**Voix naturelles françaises à trois intervenants, chevauchements réels,
bruit et DER restent NON VALIDÉS.** La procédure est dans `field-test.md`.
