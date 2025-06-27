# Ingredient detection

[Dataset on Hugging Face](https://huggingface.co/datasets/openfoodfacts/ingredient-detection) - [Model on Hugging Face](https://huggingface.co/openfoodfacts/ingredient-detection) - [Training notes](https://docs.google.com/document/d/1du2iUqgNyEN1RckBIlWnczl9jVl_GeT0jPMx6Dz08_w/edit?usp=sharing)

We developped a sequence tagging model to automatically extract ingredient lists from photos of product packaging.

This model solely relies on the text content of the image, and does not require any spatial information. It is trained to detect ingredient lists in a sequence tagging format, where each token (word) is classified as either part of an ingredient list or not. The model uses the IOB format for entity classes. There is a single `ÌNG` entity class for ingredient lists, and the `O` class for tokens that are not part of an ingredient list.

The model was fine-tuned from [xlm-roberta-large model](https://huggingface.co/FacebookAI/xlm-roberta-large).

## Dataset

The model was trained on ~5000 texts extracted from product packaging, that were annotated semi-automatically. Look at [the dataset page](https://huggingface.co/datasets/openfoodfacts/ingredient-detection) on Hugging Face for more details.

## Robotoff integration

### Inference and post-processing

The model was exported to ONNX and is served by Triton server. The model integration in Robotoff can be found in the `robotoff.prediction.ingredient_list` module.

After the individual token prediction, as often we aggregate the entities by merging the tokens that have the same entity class.

We detect the language associated by the ingredient list using our language detection model (currently based on fasttext), and parse the ingredient list using the Product Opener ingredient parser. This allows us to know how many ingredients in the ingredient list are recognized (or not) by Open Food Facts.

We add 7 fields in the image prediction data field:

- `lang`: the prediction of the language identification model
    - `lang`: the ISO 639-1 code of the language detected in the ingredient list (ex: `fr` for French, `en` for English, `de` for German, etc.)
    - `confidence`: the confidence of the model
- `ingredients_n`: the number of ingredients in the ingredient list
- `known_ingredients_n`: the number of ingredients in the ingredient list that are recognized by Open Food Facts
- `unknown_ingredients_n`: the number of ingredients in the ingredient list that are not recognized by Open Food Facts
- `fraction_known_ingredients`: the fraction of ingredients in the ingredient list that are recognized by Open Food Facts (between 0 and 1)
- `ingredients`: The list of parsed ingredients, as a list of dictionaries with the following fields:
  - `id`: the canonical ingredient ID in Open Food Facts
  - `text`: the ingredient text
  - `ìn_taxonomy`: True if the ingredient is in the Open Food Facts taxonomy, False otherwise
  - other fields returned by the Product Opener ingredient parser API such as `vegan`, `vegetarian`, `percent_max`, `percent_min`, `percent`, `percent_estimate`, `ciqual_food_code`,...
- `bounding_box`: the bounding box of the ingredient list in the image in relative coordinates, as a list of 4 float values (x_min, y_min, x_max, y_max). 

### Integration

For every new uploaded image, the model is run on this image [^extract_ingredients_job]. As for all computer vision models, we save the model prediction in the `image_prediction` table.
If some entities (i.e. ingredient lists) are detected, we create a `Prediction` in DB using the usual import mechanism [^import_mechanism], under the type `ingredient_list`.

We only create an insight if the following conditions are met [^ingredient_detection_import]:

- there is no ingredient list for the language detected in the extracted ingredient list
- 60% or more of the ingredients in the extracted ingredient list are recognized by Open Food Facts as ingredients (using the Product Opener parser)

The insight has a null `value` and the detected language as `value_tag`. An example of the `data` field is given below:

```json
{
    "entities": [
        {
            "end": 455,
            "lang": {
                "lang": "fr",
                "confidence": 0.69290453
            },
            "text": "entier partiellement concentré pasteurisé 81% (origine: France), eau, sucre 6,9%, miel 1,6%, Poids net biscuits poudre 0,66% (farine de blé, sucre, beurre, sel), amidon de maïs, jus de citron concentré, cannelle 0,16%, badiane 280a 0,16%, arôme naturel de cannelle 0,16%, ferments lactiques (dont lait). Peut contenir des traces d'oeuf",
            "score": 0.9999919533729553,
            "start": 120,
            "raw_end": 423,
            "ingredients": [
                {
                    "id": "fr:entier-partiellement-concentre-pasteurise",
                    "text": "entier partiellement concentré pasteurisé",
                    "origins": "en:france",
                    "percent": 81,
                    "in_taxonomy": false,
                    "percent_max": 81,
                    "percent_min": 81,
                    "percent_estimate": 81
                },
                {
                    "id": "en:water",
                    "text": "eau",
                    "vegan": "yes",
                    "vegetarian": "yes",
                    "in_taxonomy": true,
                    "percent_max": 9.04,
                    "percent_min": 7.88,
                    "ciqual_food_code": "18066",
                    "percent_estimate": 8.46
                },
                {
                    "id": "en:sugar",
                    "text": "sucre",
                    "vegan": "yes",
                    "percent": 6.9,
                    "vegetarian": "yes",
                    "in_taxonomy": true,
                    "percent_max": 6.9,
                    "percent_min": 6.9,
                    "percent_estimate": 6.9
                },
                {
                    "id": "en:honey",
                    "text": "miel",
                    "vegan": "no",
                    "percent": 1.6,
                    "vegetarian": "yes",
                    "in_taxonomy": true,
                    "percent_max": 1.6,
                    "percent_min": 1.6,
                    "ciqual_food_code": "31008",
                    "percent_estimate": 1.6
                },
                {
                    "id": "fr:poids-net-biscuits-poudre",
                    "text": "Poids net biscuits poudre",
                    "percent": 0.66,
                    "in_taxonomy": false,
                    "ingredients": [
                        {
                            "id": "en:wheat-flour",
                            "text": "farine de blé",
                            "vegan": "yes",
                            "vegetarian": "yes",
                            "in_taxonomy": true,
                            "percent_max": 0.66,
                            "percent_min": 0.165,
                            "percent_estimate": 0.4125
                        },
                        {
                            "id": "en:sugar",
                            "text": "sucre",
                            "vegan": "yes",
                            "vegetarian": "yes",
                            "in_taxonomy": true,
                            "percent_max": 0.33,
                            "percent_min": 0,
                            "percent_estimate": 0.12375
                        },
                        {
                            "id": "en:butter",
                            "text": "beurre",
                            "vegan": "no",
                            "vegetarian": "yes",
                            "in_taxonomy": true,
                            "percent_max": 0.22,
                            "percent_min": 0,
                            "percent_estimate": 0.061875
                        },
                        {
                            "id": "en:salt",
                            "text": "sel",
                            "vegan": "yes",
                            "vegetarian": "yes",
                            "in_taxonomy": true,
                            "percent_max": 0.22,
                            "percent_min": 0,
                            "ciqual_food_code": "11058",
                            "percent_estimate": 0.061875
                        }
                    ],
                    "percent_max": 0.66,
                    "percent_min": 0.66,
                    "percent_estimate": 0.66
                },
                {
                    "id": "en:corn-starch",
                    "text": "amidon de maïs",
                    "vegan": "yes",
                    "vegetarian": "yes",
                    "in_taxonomy": true,
                    "percent_max": 0.66,
                    "percent_min": 0.16,
                    "ciqual_food_code": "9510",
                    "percent_estimate": 0.41
                },
                {
                    "id": "en:concentrated-lemon-juice",
                    "text": "jus de citron concentré",
                    "vegan": "yes",
                    "vegetarian": "yes",
                    "in_taxonomy": true,
                    "percent_max": 0.66,
                    "percent_min": 0.16,
                    "ciqual_food_code": "2028",
                    "percent_estimate": 0.41
                },
                {
                    "id": "en:cinnamon",
                    "text": "cannelle",
                    "vegan": "yes",
                    "percent": 0.16,
                    "vegetarian": "yes",
                    "in_taxonomy": true,
                    "percent_max": 0.16,
                    "percent_min": 0.16,
                    "percent_estimate": 0.16
                },
                {
                    "id": "fr:badiane-280a",
                    "text": "badiane 280a",
                    "percent": 0.16,
                    "in_taxonomy": false,
                    "percent_max": 0.16,
                    "percent_min": 0.16,
                    "percent_estimate": 0.16
                },
                {
                    "id": "en:natural-cinammon-flavouring",
                    "text": "arôme naturel de cannelle",
                    "vegan": "maybe",
                    "percent": 0.16,
                    "vegetarian": "maybe",
                    "in_taxonomy": true,
                    "percent_max": 0.16,
                    "percent_min": 0.16,
                    "percent_estimate": 0.16
                },
                {
                    "id": "en:lactic-ferments",
                    "text": "ferments lactiques",
                    "vegan": "maybe",
                    "vegetarian": "yes",
                    "in_taxonomy": true,
                    "ingredients": [
                        {
                            "id": "en:milk",
                            "text": "dont lait",
                            "vegan": "no",
                            "vegetarian": "yes",
                            "in_taxonomy": true,
                            "percent_max": 0.16,
                            "percent_min": 0,
                            "percent_estimate": 0.0800000000000267
                        }
                    ],
                    "percent_max": 0.16,
                    "percent_min": 0,
                    "percent_estimate": 0.0800000000000267
                }
            ],
            "bounding_box": [
                1502,
                237,
                1839,
                3831
            ],
            "ingredients_n": 16,
            "known_ingredients_n": 13,
            "unknown_ingredients_n": 3
        }
    ]
}
```

[^extract_ingredients_job]: See function `robotoff.workers.tasks.import_image.extract_ingredients_job`

[^import_mechanism]: See [this page](../../explanations/predictions.md) for more details 

[^ingredient_detection_import]: See `IngredientDetectionImporter.generate_candidates` for implementation


### Annotation

To annotate the insight, use the usual route `POST https://robotoff.openfoodfacts.org/api/v1/insights/annotate`.

The request body depends on whether the user validates the ingredient list as-it or updates it.

If the user updated the ingredient list (for example if a typo was present), pass `annotation=2` and as `data` a JSON object serialized as a string with the `annotation` field set to the updated ingredient list.

If the user validates the ingredient list as-it, pass `annotation=1` and don't pass the `data` field.

Finally, the user rejects the prediction, pass `annotation=0` and don't pass the `data` field.

If the insight is validated, we select the source image as an ingredient image for the detected language (if needed), with the right
cropping and image orientation. If the user submitted an updated ingredient list, we select the image without cropping as we don't
know the correct crop associated with the updated ingredient list.