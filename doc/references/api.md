# API Reference

Robotoff provides a simple API allowing consumers to fetch predictions and annotate them.

All endpoints must be prefixed with `/api/v1`. The full URL is `https://robotoff.openfoodfacts.org/api/v1/{endpoint}`.

Robotoff can interact with all Openfoodfacts products: Openfoodfacts, Openbeautyfacts, etc. and all environments (production, development, pro). The `server_domain` field should be used to specify the product/environment: `api.openfoodfacts.org` for OFF-prod, `api.openfoodfacts.net` for OFF-dev, `api.openbeautyfacts.org` for OBF-prod,...

## Insights

An insight is a fact about a product that has been either extracted or inferred from the product pictures, characteristics,...
If the insight is correct, the Openfoodfacts DB can be updated accordingly.

Current insight types and their description can be found in [robotoff/insights/dataclass.py](https://github.com/openfoodfacts/robotoff/blob/master/robotoff/insights/dataclass.py).

### Random insight [/insights/random]

#### Get a random insight [GET]

Fetch a random insight.

- Parameters:

  - type (str, optional) - the type of insight. If not provided, an insight from any type will be returned.
  - country (str, optional) - Only return predictions with products from a specific country (ex: `en:france`)
  - value_tag (str, optional) - filter by value tag, i.e the value that is going to be sent to Openfoodfacts
  - server_domain (str, optional) - server domain. Default to 'api.openfoodfacts.org'
  - count (int, optional) - number of results to return (default: 1)

- Response 200 (application/json)

### Product insights [/insights/{barcode}]

#### Get all insights for a specific product [GET]

Return all insights associated with a specific product.

- Parameters

  - barcode: Product barcode
  - server_domain (str, optional) - server domain. Default to 'api.openfoodfacts.org'

- Response 200 (application/json)

### Insight detail [/insights/detail/{id}]

#### Get a specific insight [GET]

Return a specific insight.

- Parameters:

  - id: ID of the insight

- Response 200 (application/json)

### Insight annotations [/insights/annotate]

#### Submit an annotation [POST]

Submit an annotation, given the `insight_id`. The request type must be `application/x-www-form-urlencoded`.

- Parameters:

  - insight_id (str, required) - ID of the insight
  - annotation (int, required) - Annotation of the prediction: 1 to accept the prediction, 0 to refuse it, and -1 for "unknown".
  - update (int, optional) - Send the update to Openfoodfacts if `update=1`, don't send the update otherwise. This parameter is useful if the update is performed client-side.

- Response 200 (application/json)

## Questions

See [here](../explanations/questions.md) for more information about
questions.

Current question types:

- `add-binary`

### Product questions [/questions/{barcode}]

#### Get questions for a given product [GET]

- Parameters:

  - lang (str, optional) - the language of the question/value. 'en' by default.
  - count (int, optional) - Number of questions to return. Default to 1.
  - server_domain (str, optional) - server domain. Default to 'api.openfoodfacts.org'
  - barcode: Product barcode

- Response 200 (application/json)

### Random questions [/questions/random]

#### Get random questions [GET]

- Parameters:

  - lang (str, optional) - the language of the question/value. 'en' by default.
  - count (int, optional) - Number of questions to return. Default to 1.
  - insight_types (list, optional) - comma-separated list, filter by insight types.
  - country (str, optional) - filter by country tag.
  - brands (str, optional) - filter by brands, comma-separated list of brand tags.
  - value_tag (str, optional) - filter by value tag, i.e the value that is going to be sent to Openfoodfacts
  - server_domain (str, optional) - server domain. Default to 'api.openfoodfacts.org'

- Response 200 (application/json)

## Predictions

### Ingredient spellcheck [/predict/ingredients/spellcheck]

#### Get spelling corrections [GET]

Generate spellcheck corrections. Either the barcode or the text to correct must be supplied.

- Parameters:

  - text (str, optional) - the ingredient text to spellcheck.
  - barcode (str, optional) - the barcode of the product.

- Response 200 (application/json)

```json
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
```

### Nutrient prediction [/predict/nutrient]

#### Predict nutrient from OCR JSON [GET]

- ocr_url (str, required) - the url of the OCR JSON

- Response 200 (application/json)

```json
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
```
