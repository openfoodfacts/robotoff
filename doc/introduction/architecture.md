# Architecture

![Robotoff Architecture](../assets/architecture.svg)

Robotoff is made of several services:

- the public _API_ service
- the _scheduler_, responsible for launching recurrent tasks (downloading new dataset, processing insights automatically,...) [^scheduler]
- the _workers_, responsible for all long-lasting tasks

[^scheduler]: See `scheduler.run`

Robotoff allows to predict many information (also called _insights_), mostly from the product images.

Each time a contributor uploads a new image on Open Food Facts, the text on this image is extracted using Google Cloud Vision, an OCR (Optical Character Recognition) service. Robotoff receives a new event through a webhook each time this occurs, with the URLs of the image and the resulting OCR (as a JSON file).

We use the image to detect the grade of the nutriscore (A to E) with a computer vision model (object detection).

The OCR JSON is used to extract many types of insights:

- labels
- stores
- packager codes
- packaging
- product weight
- expiration date
- brand
- ...

We use simple string matching algorithms to find patterns in the OCR text to generate new insights [^insights]. These insights are stored in the PostgreSQL database.

[^insights]: see `models.ProductInsight`

These new insights are then accessible to all annotation tools (Hunger Games, mobile apps,...), that can validate or not the insight. If the insight is validated, it's applied immediately and the product is updated through Product Opener API. Otherwise, no update is performed. In all cases, the insight is marked as annotated, so that it is not suggested to another annotater.
Some insights with high confidence are applied automatically, 10 minutes after import.

Robotoff is also notified by Product Opener every time a product is updated or deleted [^product_update]. This is used to delete insights associated with deleted products, or to update them accordingly.

[^product_update]: see `workers.tasks.product_updated` and `workers.tasks.delete_product_insights`


## Other services

Robotoff also depends on the following services:

- a single node Elasticsearch instance, used to:
  - infer the product category from the product name, using an improved string matching algorithm. [^predict_category]
  - perform spellcheck on ingredient lists [^spellcheck_ingredients]
- a Tensorflow Serving instance, used to serve object detection models (currently, only nutriscore).
- MongoDB, to fetch the product latest version without querying Product Opener API.


[^predict_category]: see `robotoff.elasticsearch.predict`

[^spellcheck_ingredients]: see `robotoff.spellcheck.elasticsearch.es_handler.ElasticsearchHandler`
