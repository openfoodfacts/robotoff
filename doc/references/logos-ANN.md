# Logo-ANN

About 1600 products are added every day to the database.
Each product having multiple logos on its packaging, thousands of new logos are added every day to the valuable sources of information.
These logos are often useful to get important data on products (origin, brand, quality, label, etc...). 

A logo automatic detection from images and a logo manual classification features are implemented to Robotoff.
The first step is to extract logos from products images of the database.
The second one is to vectorize each logo thanks to a computer vision model.
The third and last one is to search for each logo its nearest neighbors in an index containing all the embedded logos.

## Logos extraction

When a new image is added to the database, Robotoff applies an object detection model to extract logos from it.[^logos_extraction]
This model, named "universal-logo-detector" [^universal-logo-detector], is an ONNX model trained by Open Food Facts on numerous data from the database.
For each input image, it returns bounding boxes that represent the detection zone of each logo of the image and the category of the logo, namely "brand" or "label".
To know more about this model, see the [robotoff-models release](https://github.com/openfoodfacts/robotoff-models/releases).

## Logos embedding

After the detection of a logo, in the same function [^logos_extraction], Robotoff uses a computer vision model to vectorize it.
The model we use is [CLIP-vit-base-patch32](https://huggingface.co/docs/transformers/model_doc/clip), a model developed and trained by OpenAI.
Only the vision part of the model is used here, as the objective is only to vectorize the logos.
The choice of CLIP-vit-base-patch32 was made after this [benchmark](https://openfoodfacts.github.io/robotoff/research/logo-detection/embedding-benchmark/).
The model is loaded with [Triton](https://developer.nvidia.com/nvidia-triton-inference-server) and is used only for inference.

With the logo crop of the initial image as input, CLIP returns an embedding and Robotoff stores it in its postgresql database.[^clip_embedding]

## Approximate Nearest Neighbors Logos Search

Each generated embedding is stored in an ElasticSearch index for nearest neighbor search. 
ElasticSearch allows for approximate nearest neighbor (ANN) search with an HNSW (Hierarchical Navigable Small World) index, which leads to fast and accurate search (see [ANN benchmark](https://openfoodfacts.github.io/robotoff/research/logo-detection/ann-benchmark/)). 

After storing the embedding in the index, a search for its nearest neighbors is performed and the IDs of these neighbors are stored in the Robotoff PostgreSQL database. 
The nearest neighbor search is available via an API [^api_ann_search] available (here)[https://robotoff.openfoodfacts.org/api/v1/ann/search/185171?count=50] and used by (Hunger Games)[https://hunger.openfoodfacts.org/], the annotation game connected to Robotoff.


[^logos_extraction]: see `robotoff.workers.tasks.import_image.run_logo_object_detection`
[^universal-logo-detector]: see `models.universal-logo-detector`
[^clip_embedding]: see `robotoff.workers.tasks.import_image.save_logo_embeddings`
[^api_ann_search]: see `robotoff.app.api.ANNResource`