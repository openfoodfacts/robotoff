# Logo-ANN

Environ 1600 produits sont ajoutés par jour à la base de données. 
Chaque produit comptant plusieurs logos sur son emballage, ce sont des milliers de logos apparaissant dans Open Food Facts chaque jour. 
Les logos sont souvent très utiles pour obtenir des informations sur le produit (origine, marque, fabrication, etc...). 

Une fonctionnalité de détection automatique et d'annotation des logos est implémentée à Robotoff. 
La première étape consite à extraire les logos des images des produits présentes dans la base de données. 
La deuxième est de vectoriser chaque logo grâce à un modèle de computer vision. 
La troisième et dernière est de chercher pour chaque logo ses plus proches voisins dans un index comportant tous les logos vectorisés.

## Extraction des logos

Lorsque une nouvelle image est ajoutée à la base de données, Robotoff la fait passer par un modèle d'extraction de logos.[^logos_extraction]
Ce modèle, dénommé "universal-logo-detector" [^universal-logo-detector], est un modèle onnx entrainé par Open Food Facts sur de nombreuses données de la base. 
Il retourne pour chaque image des "bounding box" rectangulaires représentant la zone de détection de chaque logo dans l'image ainsi que les catégories des logos en question, à savoir "marque" ou "label".

## Logos embedding

Après qu'un logo ait été détecté, dans la même fonction [^logos_extraction], Robotoff utilise un modèle de computer vision pour le vectoriser.
Le modèle que nous utilisons est [CLIP-vit-base-patch32](https://huggingface.co/docs/transformers/model_doc/clip), un modèle développé et entraîné par OpenAI.
Seulement la partie "vision" du modèle est utilisée ici, n'ayant pour objectif que de vectoriser les logos.
Le choix de CLIP-vit-base-patch32 a été motivé par le benchmark [ici](https://openfoodfacts.github.io/robotoff/research/logo-detection/embedding-benchmark/) détaillé.
Le modèle est chargé avec [Triton](https://developer.nvidia.com/nvidia-triton-inference-server) et est utilisé pour de l'inférence pure.

Sur la base le crop du logo retourné précédemment, CLIP renvoie un embedding et robotoff le stocke dans la base de données postgresql de Robotoff.[^clip_embedding]

## Approximate Nearest Neighbors Logos Search

Chaque embedding généré est stocké dans un index ElasticSearch pour faire de la recherche de plus proches voisins.
ElasticSearch permet de réaliser de l'ANN avec un index HNSW (Hierarchical Navigable Small World) permettant des recherches rapides et précises (cf [ANN benchmark](https://openfoodfacts.github.io/robotoff/research/logo-detection/ann-benchmark/)).

Après avoir stocké le dit embedding dans l'index, une recherche de ses plus proches voisins est réalisée et les ids de ceux-ci sont stockés dans la base de données postgresql de Robotoff.
La recherche des plus proches voisins est disponible via une API [^api_ann_search] disponible (ici)[https://robotoff.openfoodfacts.org/api/v1/ann/search/185171?count=50] et utilisée par (Hunger Games)[https://hunger.openfoodfacts.org/], le jeu d'annotations relié à Robotoff.


[^logos_extraction]: see `robotoff.workers.tasks.import_image.run_logo_object_detection`
[^universal-logo-detector]: see `models.universal-logo-detector`
[^clip_embedding]: see `robotoff.workers.tasks.import_image.save_logo_embeddings`
[^api_ann_search]: see `robotoff.app.api.ANNResource`