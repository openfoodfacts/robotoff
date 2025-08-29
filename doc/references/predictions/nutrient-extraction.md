# Nutrition extraction

[Dataset on Hugging Face](https://huggingface.co/datasets/openfoodfacts/nutrient-detection-layout) - [Model on Hugging Face](https://huggingface.co/openfoodfacts/nutrition-extractor) - [Are you looking to integrate it in your app?](https://openfoodfacts.github.io/robotoff/references/api/#tag/Predict/paths/~1predict~1nutrition/get)

We developped a ML model to automatically extract nutrition information from photos of product packaging where nutrition facts are displayed.

This model detects the most common nutrition values (proteins, salt, energy-kj,...), either for 100g or per serving. We use LayoutLMv3, an architecture used in Document AI to perform various tasks on structured documents (bills, receipts, reports,...). The model expects the input image, the tokens (=words) and the spatial position of each token on the image.
As the model requires token text and position as input, an OCR must be performed beforehand. We use Google Cloud Vision to extract text content from the image.

LayoutLMv3 architecture can perform several tasks, we frame the problem as a token classification task. The model must predict the class of each token, among a predefined set of classes. We follow the IOB format for entity classes. Here is a complete list of the token classes detected by the model:

- O
- B-ENERGY_KJ_SERVING
- I-ENERGY_KJ_SERVING
- B-CARBOHYDRATES_100G
- I-CARBOHYDRATES_100G
- B-CHOLESTEROL_SERVING
- I-CHOLESTEROL_SERVING
- B-ENERGY_KCAL_100G
- I-ENERGY_KCAL_100G
- B-SALT_SERVING
- I-SALT_SERVING
- B-SALT_100G
- I-SALT_100G
- B-SERVING_SIZE
- I-SERVING_SIZE
- B-CALCIUM_100G
- I-CALCIUM_100G
- B-SODIUM_SERVING
- I-SODIUM_SERVING
- B-FIBER_100G
- I-FIBER_100G
- B-IRON_SERVING
- I-IRON_SERVING
- B-IRON_100G
- I-IRON_100G
- B-POTASSIUM_100G
- I-POTASSIUM_100G
- B-CALCIUM_SERVING
- I-CALCIUM_SERVING
- B-TRANS_FAT_100G
- I-TRANS_FAT_100G
- B-SATURATED_FAT_100G
- I-SATURATED_FAT_100G
- B-PROTEINS_SERVING
- I-PROTEINS_SERVING
- B-SATURATED_FAT_SERVING
- I-SATURATED_FAT_SERVING
- B-VITAMIN_D_100G
- I-VITAMIN_D_100G
- B-ENERGY_KJ_100G
- I-ENERGY_KJ_100G
- B-FAT_100G
- I-FAT_100G
- B-PROTEINS_100G
- I-PROTEINS_100G
- B-VITAMIN_D_SERVING
- I-VITAMIN_D_SERVING
- B-ADDED_SUGARS_SERVING
- I-ADDED_SUGARS_SERVING
- B-CHOLESTEROL_100G
- I-CHOLESTEROL_100G
- B-SUGARS_100G
- I-SUGARS_100G
- B-CARBOHYDRATES_SERVING
- I-CARBOHYDRATES_SERVING
- B-ADDED_SUGARS_100G
- I-ADDED_SUGARS_100G
- B-SODIUM_100G
- I-SODIUM_100G
- B-FIBER_SERVING
- I-FIBER_SERVING
- B-SUGARS_SERVING
- I-SUGARS_SERVING
- B-ENERGY_KCAL_SERVING
- I-ENERGY_KCAL_SERVING
- B-FAT_SERVING
- I-FAT_SERVING
- B-TRANS_FAT_SERVING
- I-TRANS_FAT_SERVING
- B-POTASSIUM_SERVING
- I-POTASSIUM_SERVING

Nutrients that are not in this list are detected as `O` [^other_nutrient_detection].

## Dataset

Random images selected as nutrition images were picked for annotation. Using the list of labels above, more than 3500 images were manually annotated. To learn more about the dataset, have a look at the description of the dataset on [Hugging Face](https://huggingface.co/datasets/openfoodfacts/nutrient-detection-layout).

## Robotoff integration

### Pre-processing, inference and post-processing

The model was exported to ONNX and is served by Triton server. The model integration in Robotoff can be found in `robotoff.prediction.nutrition_extraction` module. The `predict` function [^predict_function] takes as input the image (as a Pillow Image) and the Google Cloud Vision OCR result (as a `OCRResult` object).

When extracting nutrient information from an image, we perform the following steps:

- extract the words and their coordinates from the OCR result
- preprocess the image, the words and their coordinates using the LayoutLMv3 preprocessor, that takes care of preprocessing the data in the right format for the LayoutLMv3 model
- perform the inference: the request is sent to Triton server through gRPC
- postprocess the results

Postprocessing includes the following steps:

- gather pre-entities from individual labels. There is one pre-entities for each input token.
- aggregate entities: the 'O' (OTHER) entity is ignored, and pre-entities with the same entity class are merged together.
- post-process entities: we post-process the detected text to correct some known limitations of the model,
  and we extract the value (ex: `5`) and the unit (ex: `g`) from the entity text.


The `predict` function returns a `NutritionExtractionPrediction` dataclass that has two fields:

- `nutrients` contains postprocessed entities that were considered valid during post-processing (the `valid` field described below is therefore not present).
- `entities` contains the raw pre-entities, the aggregated entities and the post-processed entities (respectively in the `raw`, `aggregated` and `postprocessed` fields). This field is useful for debugging and understanding model predictions.

Postprocessed entities contain the following fields:

- `entity`: the nutrient name, in Product Opener format (ex: `energy-kcal_100g` or `salt_serving`)
- `text`: the text of the entity (ex: `125 kJ`)
- `value`: the nutrient value. It's either a number or `traces`
- `unit`: the nutrient unit, either `g`, `mg`, `µg`, `kj`, `kcal` or `null`. Sometimes the nutrient unit is not present after the value, or the OCR didn't detect the corresponding word. You can either infer a plausible unit given the entity (ex: `g` for proteins, carbohydrates,...) or ignore this entity.
- `score`: The entity score. We use the score of the first pre-entity as the aggregated entity score.
- `start`: the word start index of the entity, with respect to the original OCR JSON
- `end`: the word end index of the entity, with respect to the original OCR JSON
- `char_start`: the character start index of the entity, with respect to the original OCR JSON
- `char_end` : the character end index of the entity, with respect to the original OCR JSON
- `valid`: whether the extracted entity is valid. We consider an entity invalid if we couldn't extract nutrient value from the `text` field, or if there are more than one entity for a single nutrient. For example, two `proteins_100g` entities are both considered invalid, but one `proteins_100g` and one `proteins_serving` are considered valid.

### Integration

For every new uploaded image, the model is run on this image [^extract_nutrition_job]. As for all computer vision models, we save the model prediction in the `image_prediction` table.
If some entities were detected, we create a `Prediction` in DB using the usual import mechanism [^import_mechanism], under the type `nutrient_extraction`.

We only create an insight if the model detected a nutrient whose value is different than what's registered on the product (this includes nutrients with missing value) [^nutrient_extraction_import]. We only consider nutrient values entered for the same quantity (100g or serving) as what's indicated in Open Food Facts. It means that for a product with `nutrition_data_per=serving` and missing `proteins_serving`, we won't generate an insight if the model detected the protein quantity per 100g (`proteins_100g`). 

We consider images from the most recent image to the oldest one, and stop the process as soon as a valid candidate insight is found. This ensures that the nutrient prediction is made on the most recent image available. Indeed, nutrition values can change over time, and we want to avoid creating insights based on possibly outdated images.

If a `nutrient_extraction` insight was already validated for a product, we only create a new insight if the associated image is more recent than the image that was used to create the last validated insight.

[^other_nutrient_detection]: Using a fixed set of classes is not the best approach when we have many classes. It however allows us to use LayoutLM architecture, which is very performant for this task, even when the nutrition table is hard to read due to packaging deformations or alterations. To detect the long-tail of nutrients, approaches using graph-based approach, where we would map a nutrient mention to its value, could be explored in the future.

[^predict_function]: In `robotoff.prediction.nutrition_extraction` module

[^extract_nutrition_job]: See function `robotoff.workers.tasks.import_image.extract_nutrition_job`

[^import_mechanism]: See [this page](../../explanations/predictions.md) for more details 

[^nutrient_extraction_import]: See `NutrientExtractionImporter.generate_candidates` for implementation
