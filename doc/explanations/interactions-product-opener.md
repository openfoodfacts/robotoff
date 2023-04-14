# Interactions with Product Opener

Robotoff mainly interacts with Product Opener (Open Food Facts backend service) through three means:

- it receives updates through a webhook when a product is created/modified/deleted or when an image is uploaded
- it has a direct read/write access to the underlying MongoDB that powers Open Food Facts
- it calls Product Opener API to update/delete products and images and to fetch some information

## Webhook calls

### Product update

Product Opener calls `POST /api/v1/webhook/product` whenever a product is updated, with the following parameters:

- `barcode`: the barcode of product
- `action`:  either `updated` or `deleted`
- `server_domain`: the server domain (ex: `api.openfoodfacts.org`)

After receiving a `product_update` webhook call, Robotoff does the following [^product_update]:

- predict categories and import category predictions/insights
- generate and import predictions/insights from product name (regex/flashtext-based)
- refresh all insights for this product (i.e: import all predictions again, and update insight table accordingly)

### Image uploaded

Product Opener calls `POST /api/v1/images/import` whenever an new image is uploaded, with the following parameters:

- `barcode`: the barcode of product
- `image_url`:  the URL of the image
- `ocr_url`:  the URL of the OCR result (JSON file)
- `server_domain`: the server domain (ex: `api.openfoodfacts.org`)

After receiving a `import_image` webhook call, Robotoff does the following [^image_import]:

- save the image metadata in the `Image` DB table
- import insights from the image
- run logo detection pipeline on the image

Insight import includes the following steps:

- extract and import regex/flashtext predictions and insights from the image OCR
- run the nutriscore object detection model, if the "NUTRISCORE" string was detected in the OCR text. This is to avoid wasting compute resources and preventing false positive results.
- run logo detection pipeline: detect logos using the object detection models, generate embeddings from logo crops and index them in the Elasticsearch ANN index.

## MongoDB interaction

Robotoff often needs to access the latest information about product. As the API is sometimes unresponsive, Robotoff has a direct access to the MongoDB. It is used to fetch the product data in the `products` collection.

Robotoff also has a write access, that allows it to add facets dynamically. This process is done every night; only the `en:missing-nutrition-facts-fibers-present-on-photos` quality facet is currently added by Robotoff.

## Product Opener API

Robotoff also interacts directly with Product Opener through it's API. Everytime an insight is annotated (`annotation=1`), either manually or automatically, Robotoff calls Product Opener API to perform the associated action (update the product, delete an image,...).

Robotoff also depends on static resources from Product Opener:

- taxonomy files (ex: `https://static.openfoodfacts.org/data/taxonomies/categories.full.json`) which are downloaded and cached in RAM
- the JSONL dump: `https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz`. This is used to scan the entire database and update predictions/insights without having to do a full MongoDB scan.
- images/OCR files

[^product_update]: see `update_insights_job` function in `robotoff.workers.tasks.product_updated`
[^image_import]: see `run_import_image_job` function in `robotoff.workers.tasks.import_image`