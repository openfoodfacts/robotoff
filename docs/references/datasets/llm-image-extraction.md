# LLM image extraction dataset

Large visual language models (LVLMs) can be used to extract information from images.

In this document, we describe the schema used for LLM image extraction datasets uploaded on Hugging Face as Parquet files. We can automatically create datasets on Hugging Face using the [labelr CLI](https://github.com/openfoodfacts/labelr) [^labelr-schema].

[^labelr-schema]: the parquet schema used can be [found here](https://github.com/openfoodfacts/labelr/blob/main/src/labelr/sample/llm.py#L29).


The [price-tag-extraction](https://huggingface.co/datasets/openfoodfacts/price-tag-extraction) dataset is an example of such dataset.

## Schema

- `image_id`: string, unique identifier of the image. For Open Food Facts images, it's usually in the format `{barcode}_{imgid}` (example: for [https://images.openfoodfacts.org/images/products/703/801/000/5459/5.jpg](https://images.openfoodfacts.org/images/products/703/801/000/5459/5.jpg), it would be `7038010005459_5`)
- `image`: the image data. Note that we apply rotation based on EXIF metadata before saving the image. Images are also often resized to reduce dataset size and speed up training.
- `output`: the expected output text extracted from the image. It's expected to be a valid JSON string conforming to the schema (see [Configuration file](#configuration-file) section below for more information).
- `meta`: metadata about the image. It's project dependent, but most frequent fields are:
   - `barcode` (Open Food Facts projects only): the barcode of the product.
   - `off_image_id` (Open Food Facts projects only): the `imgid` of the original image.
   - `image_url`: the URL of the image.


## Configuration file

To fine-tune a LVLM using the dataset, we also need:

- textual instructions for the vLLM to describe the task to perform on the image.
- a JSON schema describing the expected output format. This schema allows to specify the expected fields, their types, constraints and to provide a detailed description of each field.

Both are stored in a configuration JSON file stored at the root of the dataset repository on Hugging Face, named `config.json`. Two keys are expected in this file: `instructions` and `json_schema`. An example of such file can be found [here](https://huggingface.co/datasets/openfoodfacts/price-tag-extraction/blob/v1.1/config.json).

## Training a vLLM

To train a vLLM with this type of dataset, you can use the [train-unsloth](https://github.com/openfoodfacts/labelr/tree/main/packages/train-unsloth) package from the `labelr` repository.
