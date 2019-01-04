FORMAT: 1A

# Robotoff

Robotoff provides a simple API allowing consumers to fetch predictions and annotate them.


# Group Categories

Category-related predictions and annotation management.

## Categories prediction [/categories/predictions]

### Get a prediction [GET]

Fetch a new category prediction.

+ Parameters
    + campaign (str, optional) - Annotation campaign. If not provided, the default campaign will be used.
      Use `matcher` to get the string matching predictions.
    + lang (str, optional) - Language in which the results must be returned, currently only the category name is
      affected.
    + country (str, optional) - Only return predictions with products from a specific country (ex: `en:france`)
    + category (str, optional) - Only return predictions with a specific category (ex: `en:hams`)

+ Response 200 (application/json)

            {
                "prediction": {
                    "confidence": null,
                    "id": "en:potatoes",
                    "name": "Pommes de terre"
                },
                "product": {
                    "brands": "Fleurs des Champs ",
                    "categories_tags": [],
                    "image_url": "https://static.openfoodfacts.org/images/products/26062136/front_fr.8.400.jpg",
                    "product_link": "https://fr.openfoodfacts.org/product/26062136",
                    "product_name": "Pommes de Terre"
                },
                "task_id": "aea5127e-5dc4-4db3-8b2b-7174834a54d0"
            }


## Product categories prediction [/categories/predictions/{barcode}]

+ Parameters
    + barcode: Product barcode


### Get a category prediction for the product [GET]

Fetch a new category prediction for the given product.

+ Parameters
    + lang (str, optional) - Language in which the results must be returned, currently only the category name is
      affected.

+ Response 200 (application/json)

            {
                "prediction": {
                    "confidence": null,
                    "id": "en:potatoes",
                    "name": "Pommes de terre"
                },
                "product": {
                    "brands": "Fleurs des Champs ",
                    "categories_tags": [],
                    "image_url": "https://static.openfoodfacts.org/images/products/26062136/front_fr.8.400.jpg",
                    "product_link": "https://fr.openfoodfacts.org/product/26062136",
                    "product_name": "Pommes de Terre"
                },
                "task_id": "aea5127e-5dc4-4db3-8b2b-7174834a54d0"
            }


## Categories annotations [/categories/annotate]

### Submit an annotation [POST]

Submit an annotation, given the `task_id`. The request type must be `application/x-www-form-urlencoded`.

+ task_id (str, required) - ID of the task
+ annotation (int, required) - Annotation of the prediction: 1 to accept the prediction, 0 to refuse it, and -1 
  for "unknown".
+ save (int, optional) - Send the update to Openfoodfacts if `save=1`, don't send the update otherwise. This 
  parameter is useful if the update is performed client-side.

+ Response 200 (application/json)

            {
                "status": "saved"
            }
