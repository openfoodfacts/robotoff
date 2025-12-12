# Object detection datasets

Object detection models are used in Robotoff for many tasks, including the detection of logos and nutrition tables.

In this document, we describe the schema used for object detection datasets uploaded on Hugging Face as Parquet files. We now automatically create datasets on Hugging Face using the [labelr CLI](https://github.com/openfoodfacts/labelr) [^labelr-schema].

[^labelr-schema]: the parquet schema used can be [found here](https://github.com/openfoodfacts/labelr/blob/e88cc8e26dccd103d140e3aa4340a78dffa4819b/src/labelr/dataset_features.py#L6).

The [universal-logo-detector](https://huggingface.co/datasets/openfoodfacts/universal-logo-detector) dataset is an example of such dataset.

## Schema

- `image_id`: string, unique identifier of the image. For Open Food Facts images, it's usually in the format `{barcode}_{imgid}` (example: for https://images.openfoodfacts.org/images/products/703/801/000/5459/5.jpg, it would be `7038010005459_5`)
- `image`: the image data. Note that we apply rotation based on EXIF metadata before saving the image (see [Exif rotation](#exif-rotation) section below for more information).
- `ẁidth`: the image width.
- `height`: the image height.
- `meta`: metadata about the image. It's project dependent, but most frequent fields are:
    - `barcode` (Open Food Facts projects only): the barcode of the product.
    - `off_image_id` (Open Food Facts projects only): the `imgid` of the original image.
    - `image_url`: the URL of the image.
- `objects`: a field containing ground-truth annotations, with the following subfields:
    - `bbox`: a list of bounding box. Each bounding box is a list in the format `[y_min, x_min, y_max, x_max]` in relative coordinates (value between 0 and 1), with the top-left corner as origin. Example: `[[0.838, 0.689, 0.935, 0.891]]`.
    - `category_id`: an list of category IDs (integers starting from 0), one for each bounding box. This field has the same length as `bbox`.
    - `category_name`: a list of category names, one for each bounding box. This field has the same length as `bbox`.


## Exif rotation

Hugging Face stores images without applying EXIF rotation, and EXIF data is not preserved in the dataset.

Label Studio provides bounding boxes based on the displayed image (after eventual EXIF rotation), so we need to apply the same transformation to the image.

Note that images were **NOT** EXIF-rotated in object detection datasets uploaded *before* the `universal-logo-detector` dataset, so we need to reupload the dataset with correct orientation before training a new model. This was not an issue prior to `universal-logo-detector` model, as we used to create the ultralytics dataset using `image_url` field directly, and ultralytics use EXIF orientation metadata to rotate the image on the fly.

Now, using the [train-yolo](https://github.com/openfoodfacts/labelr/tree/main/packages/train-yolo) package, we use the dataset stored on Hugging Face (including the image data) as the unique source of truth. It allows to "freeze" the dataset, preventing alteration when an image is deleted on Open Food Facts image server for example, and makes the dataset preprocessing before training much faster.