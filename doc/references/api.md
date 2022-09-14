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

## Collection

### Prediction Collection [/predictions/]
Get all the predictions [GET]

The page, count, value_tag to the predictions must be supplied.

- Parameters:
  - page (int) - the page number to return (default: 1)
  - count (int) - number of results to return (default: 25)
  
  - barcode (str, optional) - the barcode of the product.
  - value_tag (str) - the value_tag of the insight
  - keep_types (List[str], optional) -  a list of insight types

- Response 200 (application/json)

```
{
	'count': 2,
	'predictions': [{
		'id': 33,
		'barcode': '0000000000002',
		'type': 'brand',
		'data': {
			'sample': 1
		},
		'timestamp': '2022-09-13T15:24:11.764995',
		'value_tag': 'en:beers',
		'value': None,
		'source_image': None,
		'automatic_processing': None,
		'server_domain': 'api.openfoodfacts.localhost',
		'predictor': None
	}, {
		'id': 32,
		'barcode': '0000000000001',
		'type': 'category',
		'data': {},
		'timestamp': '2022-09-13T15:24:11.758110',
		'value_tag': 'en:seeds',
		'value': None,
		'source_image': None,
		'automatic_processing': None,
		'server_domain': 'api.openfoodfacts.localhost',
		'predictor': None
	}],
	'status': 'found'
}
```

### Image Prediction Collection [/images/prediction/collection/]

Get all image predictions [GET]

The page, count must be supplied

- Parameters:
  - page (int) - the page number to return (default: 1)
  
  - count (int) - number of results to return (default: 25)
  - barcode (str, optional) - the barcode of the product.
  - with_logo (bool, optional) - whether to return with or without logos (default=False)
  - type (str, optional) -  an insight types
  - server_domain (str, optional) -   server domain. Default to 'api.openfoodfacts.org'

- Response 200 (application/json)

```
{
	'count': 1,
	'images': [{
		'id': 10,
		'type': 'category',
		'model_name': 'universal-logo-detector',
		'model_version': 'tf-universal-logo-detector-1.0',
		'data': {
			'objects': [{
				'label': 'brand',
				'score': 0.2,
				'bounding_box': [0.4, 0.4, 0.6, 0.6]
			}]
		},
		'timestamp': '2022-09-13T15:40:46.071377',
		'image': {
			'id': 11,
			'barcode': '123',
			'uploaded_at': '2022-09-13T15:40:46.072360',
			'image_id': 'image-01',
			'source_image': '/images/01.jpg',
			'width': 400,
			'height': 400,
			'deleted': False,
			'server_domain': 'api.openfoodfacts.localhost',
			'server_type': 'off'
		},
		'max_confidence': None
	}],
	'status': 'found'
}
```

### Image Collection[/images/]

Get all images [GET]

The count, page must be supplied

- Parameters
  - page (int) - the page number to return (default: 1)
  - count (int) - number of results to return (default: 25)
  - barcode (str, optional) - the barcode of the product.
  - with_predictions (bool, optional) - whether to return images with or without predictions (default=False)

  - server_domain (str, optional) -   server domain. Default to 'api.openfoodfacts.org'

- Response 200 (application/json)

  ```
  {
	'count': 1,
	'images': [{
		'id': 14,
		'barcode': '123',
		'uploaded_at': '2022-09-13T16:11:39.272087',
		'image_id': 'image-01',
		'source_image': '/images/01.jpg',
		'width': 400,
		'height': 400,
		'deleted': False,
		'server_domain': 'api.openfoodfacts.localhost',
		'server_type': 'off'
	}],
	'status': 'found'
  }
  ```

### Logo Annotation Collection[/annotation/collection/]

Get all images [GET]

The count, page, value tag must be supplied

- Parameters
  - page (int) - the page number to return (default: 1)

  - count (int) - number of results to return (default: 25)
  - barcode (str, optional) - the barcode of the product.
  - value_tag (str) - the value_tag of the product.
  - keep_types (List[str], optional) -  a list of insight types
  - server_domain (str, optional) -   server domain. Default to 'api.openfoodfacts.org'


- Response 200 (application/json)

  ```
  {
	'count': 1,
	'annotation': [{
		'id': 9,
		'image_prediction': {
			'id': 16,
			'type': 'object_detection',
			'model_name': 'universal-logo-detector',
			'model_version': 'tf-universal-logo-detector-1.0',
			'data': {
				'objects': [{
					'label': 'brand',
					'score': 0.2,
					'bounding_box': [0.4, 0.4, 0.6, 0.6]
				}]
			},
			'timestamp': '2022-09-13T16:17:04.447213',
			'image': {
				'id': 18,
				'barcode': '295',
				'uploaded_at': '2022-09-13T16:17:04.447316',
				'image_id': 'image-03',
				'source_image': '/images/03.jpg',
				'width': 400,
				'height': 400,
				'deleted': False,
				'server_domain': 'api.openfoodfacts.localhost',
				'server_type': 'off'
			},
			'max_confidence': None
		},
		'index': 0,
		'bounding_box': [0.4, 0.4, 0.6, 0.6],
		'score': 0.7,
		'annotation_value': 'ab agriculture biologique',
		'annotation_value_tag': 'cheese',
		'taxonomy_value': 'en:ab-agriculture-biologique',
		'annotation_type': 'dairies',
		'username': None,
		'completed_at': None,
		'nearest_neighbors': {
			'logo_ids': [111111, 222222],
			'distances': [11.1, 12.4]
		}
	}],
	'status': 'found'
  }
  ```
### Unanswered question Collection[/questions/unanswered/]

Get all images [GET]

The count, page must be supplied

- Parameters
  - page (int) - the page number to return (default: 1)
  - count (int) - number of results to return (default: 25)
 
  - type (str, optional) -  an insight type
  - server_domain (str, optional) -   server domain. Default to 'api.openfoodfacts.org'

- Response 200 (application/json)

```
 {
	'count': 5,
	'questions': [
		['en:soups', 3],
		['en:apricot', 2]
	],
	'status': 'found'
}
```

