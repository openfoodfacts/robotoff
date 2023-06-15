# Architecture

![Robotoff Architecture](../assets/architecture.svg)

Robotoff is made of several services:

- the public _API_ service
- the _scheduler_, responsible for launching recurrent tasks (downloading new dataset, processing insights automatically,...) [^scheduler]
- the _workers_, responsible for all long-lasting tasks
- a _redis_ instance

Communication between API and workers happens through Redis DB using [rq](https://python-rq.org). [^worker_job]

Jobs are sent through rq messaging queues. We currently have two types of queues:
- High-priority queues, used when a product is updated/deleted, or when a new image is uploaded. All jobs associated with a product are always sent to the same queue, based on the product barcode [^product_specific_queue]. This way, we greatly reduce the risk of concurrent processing for the same product (DB deadlocks or integrity errors).
- Low priority queue `robotoff-low`, which is used for all lower-priority jobs.

We also have two kind of workers, low and high priority workers: `worker_low` and `worker_high` respectively. All types of workers handle high-priority jobs first. Each worker listens to a single high priority queue. Only low priority workers can handle low-priority jobs. This way, we ensure low priority jobs don't use excessive system resources, due to the limited number of workers that can handle such jobs.

[^scheduler]: See `scheduler.run`

[^worker_job]: See `robotoff.workers.queues` and `robotoff.workers.tasks`

[^product_specific_queue]: See `get_high_queue` function in `robotoff.workers.queues`

Robotoff allows to predict many information (also called _insights_), mostly from the product images or OCR.

Each time a contributor uploads a new image on Open Food Facts, the text on this image is extracted using Google Cloud Vision, an OCR (Optical Character Recognition) service. Robotoff receives a new event through a webhook each time this occurs, with the URLs of the image and the resulting OCR (as a JSON file).
We use simple string matching algorithms to find patterns in the OCR text to generate new predictions [^predictions].

We also use a ML model to extract objects from images. [^image_predictions]

One model tries to detect any logo [^logos].
Detected logos are then embedded in a vector space using the openAI pre-trained model CLIP-vit-base-patch32.
In this space we use a k-nearest-neighbor approach to try to classify the logo, predicting a brand or a label.
Hunger game also collects users annotations to have ground truth ([logo game](https://hunger.openfoodfacts.org/logos)).

Another model tries to detect the grade of the Nutri-Score (A to E) 
with a computer vision model.

The above detections generate predictions which in turn generate many types of insights [^insights]:

- labels
- stores
- packager codes
- packaging
- product weight
- expiration date
- brand
- ...

Predictions, as well as insights are stored in the PostgreSQL database.

[^predictions]: see `robotoff.models.Prediction`

[^image_predictions]: see `robotoff.models.ImagePrediction` and `robotoff.workers.tasks.import_image.run_import_image_job`

[^insights]: see `robotoff.models.ProductInsight`

[^logos]: see `robotoff.models.ImageAnnotation` `robotoff.logos`

These new insights are then accessible to all annotation tools (Hunger Games, mobile apps,...), that can validate or not the insight. 

If the insight is validated by an authenticated user, it's applied immediately and the product is updated through Product Opener API [^annotate]. If it's reported as invalid, no update is performed, but the insight is marked as annotated so that it is not suggested to another annotator. If the user is not authenticated, a system of votes is used (3 consistent votes trigger the insight application).

Some insights with high confidence are applied automatically, 10 minutes after import.

Robotoff is also notified by Product Opener every time a product is updated or deleted [^product_update]. This is used to delete insights associated with deleted products, or to update them accordingly.

[^product_update]: see `workers.tasks.product_updated` and `workers.tasks.delete_product_insights_job`
[^annotate]: see `robotoff.insights.annotate`


## Other services

Robotoff also depends on the following services:

- a single node Elasticsearch instance, used to:
  - infer the product category from the product name, using an improved string matching algorithm. [^predict_category] (used in conjunction with ML detection)
  - index all logos to run ANN search for automatic logo classification [^logos]
- a Triton instance, used to serve object detection models (nutriscore, nutrition-table, universal-logo-detector) [^robotoff_ml].
- a Tensorflow Serving instance, used to serve the category detection model. We're going to get rid of Tensorflow Serving once a new categorizer is trained. [^robotoff_ml]
- [robotoff-ann](https://github.com/openfoodfacts/robotoff-ann/) which uses an approximate KNN approach to predict logo label
- MongoDB, to fetch the product latest version without querying Product Opener API.


[^predict_category]: see `robotoff.prediction.category.matcher`

[^robotoff_ml]: see `docker/ml.yml`
