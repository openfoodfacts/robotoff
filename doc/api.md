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

See [here](https://github.com/openfoodfacts/robotoff/blob/master/robotoff/doc/questions.md) for more information about 
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
