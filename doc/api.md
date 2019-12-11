FORMAT: 1A

# Robotoff

Robotoff provides a simple API allowing consumers to fetch predictions and annotate them.
All endpoints must be prefixed with `/api/v1` (the full URL being `https://robotoff.openfoodfacts.org/api/v1/{endpoint}`)

# Group Insights

An insight is a fact about a product that has been either extracted or inferred from the product pictures, characteristics,...
If the insight is correct, the Openfoodfacts DB can be updated accordingly.

Current insight types:

- `ingredient_spellcheck`
- `packager_code`
- `label`
- `category`
- `product_weight`
- `expiration_date`
- `brand`
- `store`
- `nutrient`

## Random insight [/insights/random]

### Get a random insight [GET]

Fetch a random insight.

+ type (str, optional) - the type of insight. If not provided, an insight from any type will be returned.
+ country (str, optional) - Only return predictions with products from a specific country (ex: `en:france`)

+ Response 200 (application/json)


## Product insights [/insights/{barcode}]

### Get all insights for a specific product [GET]

Return all insights associated with a specific product.

+ Parameters
    + barcode: Product barcode

+ Response 200 (application/json)


## Insight detail [/insights/detail/{id}]

### Get a specific insight [GET]

Return a specific insight.

+ Parameters
    + insight_id: ID of the insight

+ Response 200 (application/json)


## Insight annotations [/insights/annotate]

### Submit an annotation [POST]

Submit an annotation, given the `insight_id`. The request type must be `application/x-www-form-urlencoded`.

+ insight_id (str, required) - ID of the insight
+ annotation (int, required) - Annotation of the prediction: 1 to accept the prediction, 0 to refuse it, and -1 
  for "unknown".
+ update (int, optional) - Send the update to Openfoodfacts if `update=1`, don't send the update otherwise. This 
  parameter is useful if the update is performed client-side.

+ Response 200 (application/json)



# Group Questions

See [here](https://github.com/openfoodfacts/robotoff/blob/master/doc/questions.md) for more information about 
questions.

Current question types:

- `add-binary`

## Product questions [/questions/{barcode}]

### Get questions for a given product [GET]

+ Parameters
    + barcode: Product barcode

+ lang (str, optional) - the language of the question/value. 'en' by default.
+ count (int, optional) - Number of questions to return. Default to 1.

+ Response 200 (application/json)


## Random questions [/questions/random]

### Get random questions [GET]

+ lang (str, optional) - the language of the question/value. 'en' by default.
+ count (int, optional) - Number of questions to return. Default to 1.
+ insight_types (list, optional) - comma-separated list, filter by insight types.
+ country (str, optional) - filter by country tag.
+ brands (str, optional) - filter by brands, comma-separated list of brand tags.
+ value_tag (str, optional) - filter by value tag, i.e the value that is going to be sent to Openfoodfacts

+ Response 200 (application/json)


# Group Predict

## Ingredient spellcheck [/predict/ingredients/spellcheck]

### Get spelling corrections [POST]

+ text (str, required) - the ingredient text to spellcheck


+ Response 200 (application/json)

        {
            "corrected": "farine de blé",
            "corrections": [
                {
                    "score": 0.0009564351,
                    "term_corrections": [
                        {
                            "correction": "farine",
                            "end_offset": 6,
                            "original": "fqrine",
                            "start_offset": 0
                        }
                    ]
                }
            ],
            "text": "fqrine de blé"
        }


## Nutrient prediction [/predict/nutrient]

### Predict nutrient from OCR JSON [GET]

+ ocr_url (str, required) - the url of the OCR JSON


+ Response 200 (application/json)

        {
            "nutrients": {
                "glucid": [
                    {
                        "nutrient": "glucid",
                        "raw": "glucides 53 g",
                        "unit": "g",
                        "value": "53"
                    }
                ]
            }
        }
