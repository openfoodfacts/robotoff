openapi: 3.0.0
# API Reference

Robotoff provides a simple API allowing consumers to fetch predictions and annotate them.

All endpoints must be prefixed with `/api/v1`. The full URL is `https://robotoff.openfoodfacts.org/api/v1/{endpoint}`.

Robotoff can interact with all Openfoodfacts products: Openfoodfacts, Openbeautyfacts, etc., and all environments (production, development, pro). The `server_domain` field should be used to specify the product/environment: `api.openfoodfacts.org` for OFF-prod, `api.openfoodfacts.net` for OFF-dev, `api.openbeautyfacts.org` for OBF-prod,...

## Insights

An insight is a fact about a product that has been extracted or inferred from the product pictures or characteristics.
If the insight is correct, the Openfoodfacts DB can be updated accordingly.

Current insight types and their description can be found in [robotoff/insights/dataclass.py](https://github.com/openfoodfacts/robotoff/blob/master/robotoff/insights/dataclass.py).

### Random insight [/insights/random]

#### Get a random insight [GET]

Fetch a random insight.

- Parameters:

        - name: lang
          in: query
          description: The language of the question/value
          required: false
          schema:
            type: string
            default: en
        - name: count
          in: query
          description: The number of questions to return
          required: false
          schema:
            type: number
            default: 1
            minimum: 1
        - name: server_domain
          in: query
          description: The server domain
          required: false
          schema:
            type: string
            default: api.openfoodfacts.org
        - name: insight_types
          in: query
          description: Comma-separated list, filter by insight types
          required: false
          schema:
            type: string
        - name: country
          in: query
          description: Filter by country tag
          required: false
          schema:
            type: string
        - name: brands
          in: query
          description: Comma-separated list, filter by brands
          required: false
          schema:
            type: string
        - name: value_tag
          in: query
          description: Filter by value tag, i.e the value that is going to be sent to Openfoodfacts
          required: false
          schema:
            type: string

-  responses:
        "200":
          description: ""
          headers: {}
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - "no_questions"
                      - "found"
                  questions:
                    type: array
                    items:
                      type: object

### Product insights [/insights/{barcode}]

#### Get all insights for a specific product [GET]

Return all insights associated with a specific product.

- Parameters

  - barcode: Product barcode
  - name: server_domain

-  responses:
        "200":
          description: ""
          headers: {}
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - "no_questions"
                      - "found"
                  questions:
                    type: array
                    items:
                      type: object

### Insight detail [/insights/detail/{id}]

#### Get a specific insight [GET]

Return a specific insight.

- Parameters:

  - name: id

-  responses:
        "200":
          description: ""
          headers: {}
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - "no_questions"
                      - "found"
                  questions:
                    type: array
                    items:
                      type: object

### Insight annotations [/insights/annotate]

#### Submit an annotation [POST]

Submit an annotation, given the `insight_id`. The request type must be `application/x-www-form-urlencoded`.

- Parameters:

                insight_id:
                  type: string
                  description: ID of the insight
                annotation:
                  type: integer
                  description: "Annotation of the prediction: 1 to accept the prediction, 0 to refuse it, and -1 for `unknown`"
                  enum:
                    - 0
                    - 1
                    - -1
                update:
                  type: integer
                  description: "Send the update to Openfoodfacts if `update=1`, don't send the update otherwise. This parameter is useful if the update is performed client-side"
                  default: 1
                  enum:
                    - 0
                    - 1
              required:
                - "insight_id"
                - "annotation"
     responses:
        "200":
          description: ""
          headers: {}
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - "no_questions"
                      - "found"
                  questions:
                    type: array
                    items:
                      type: object

## Questions

See [here](../explanations/questions.md) for more information about
questions.

Current question types:

- `add-binary`

### Product questions [/questions/{barcode}]

#### Get questions for a given product [GET]

- Parameters:

   parameters:
        - name: barcode
          in: path
          description: The product barcode
          required: true
          style: simple
          schema:
            type: string
        - name: lang
          in: query
          description: The language of the question/value
          required: false
          schema:
            type: string
            default: en
        - name: count
          in: query
          description: The number of questions to return
          required: false
          schema:
            type: number
            default: 1
            minimum: 1
        - name: server_domain
          in: query
          description: The server domain
          required: false
          schema:
            type: string 
            default: api.openfoodfacts.org

-  responses:
        "200":
          description: ""
          headers: {}
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - "no_questions"
                      - "found"
                  questions:
                    type: array
                    items:
                      type: object

### Random questions [/questions/random]

#### Get random questions [GET]

- Parameters:

          - name: lang
          in: query
          description: The language of the question/value
          required: false
          schema:
            type: string
            default: en
        - name: count
          in: query
          description: The number of questions to return
          required: false
          schema:
            type: number
            default: 1
            minimum: 1
        - name: server_domain
          in: query
          description: The server domain
          required: false
          schema:
            type: string
            default: api.openfoodfacts.org
        - name: insight_types
          in: query
          description: Comma-separated list, filter by insight types
          required: false
          schema:
            type: string
        - name: country
          in: query
          description: Filter by country tag
          required: false
          schema:
            type: string
        - name: brands
          in: query
          description: Comma-separated list, filter by brands
          required: false
          schema:
            type: string
        - name: value_tag
          in: query
          description: Filter by value tag, i.e the value that is going to be sent to Openfoodfacts
          required: false
          schema:
            type: string

-  responses:
        "200":
          description: ""
          headers: {}
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - "no_questions"
                      - "found"
                  questions:
                    type: array
                    items:
                      type: object

## Predictions

### Ingredient spellcheck [/predict/ingredients/spellcheck]

#### Get spelling corrections [GET]

Generate spellcheck corrections. Either the barcode or the text to correct must be supplied.

- Parameters:

  - text:
          type: string
          description: the ingredient text to spellcheck.
  - barcode:
          type: integer
          description: Barcode of the product

-  responses:
        "200":
          description: ""
          headers: {}
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - "no_questions"
                      - "found"
                  questions:
                    type: array
                    items:
                      type: object

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

- ocr_url :
       type: string
       description: the url of the OCR JSON.

- responses:
        "200":
          description: ""
          headers: {}
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - "no_questions"
                      - "found"
                  questions:
                    type: array
                    items:
                      type: object

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
