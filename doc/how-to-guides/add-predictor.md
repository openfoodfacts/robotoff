# How to add a new model/predictor to Robotoff?

You have a shiny new model and you want to add it to Robotoff? Great!

Here is a step-by-step guide to help you.

## Prediction generation

All prediction-related code lives in `robotoff.prediction` module.

If the prediction is OCR-based, it should be in `robotoff.prediction.ocr`, otherwise at the root of the module (you can create a deeper module if necessary). If you want to deploy an ML model, the best place to serve it is on Triton, our ML inference server. You should first convert your model to SavedModel or ONNX format and make it servable through Triton. Inference requests to Triton are sent through gRPC [^triton].

The result of the computation should be a list of `Prediction`s. If you want the insight to be automatically applied, set `automatic_processing=True` when creating the Prediction. You may need to create a new entry in `PredictionType` and `InsightType` in `robotoff.types` depending on your predictor.

## Calling the predictor

If the prediction is not OCR-based, you will either want the predictor to be called:

- when a new image is uploaded: you should add a call to your predictor function in `robotoff.workers.tasks.import_image`
- when the product is updated: you should add a call to your predictor function in `robotoff.workers.tasks.product_updated`

## Importing predictions/insights

The next step is to import the predictions in database and generate insights from these predictions. If you don't know the difference between insights and predictions, [check this page](../explanations/predictions.md).

You should create a new importer class subclassing `InsightImporter` in `robotoff.insights.importer` and add it to the `IMPORTERS` list.

## Trigger actions after insight annotation

To perform some actions when the insight has been annotated and marked as correct (`annotation=1`), you should add a new class subclassing `InsightAnnotator` in `robotoff.insights.annotate` and add it to the `ANNOTATOR_MAPPING` dictionary.

If you need a call to Product Opener API that is not implemented yet, add it to `robotoff.off`.

## Test your predictor

To test your predictor, you can simulate an image import using [POST /api/v1/images/import](https://openfoodfacts.github.io/robotoff/references/api/#tag/Images/paths/~1images~1import/post) endpoint. There is a CLI command that does this for you:

```bash
make robotoff-cli args='import-image-webhook https://images.openfoodfacts.org/images/products/377/001/626/6048/1.jpg'
```

You can check that:

- the predictor is indeed called
- it generates predictions/insights and save them in DB when expected
- no errors occurred (in the logs)

If you add an OCR-only predictor, you should also add unit tests in `tests/unit`. We don't yet have the possibility to perform integration tests on ML models served by Triton though.

That's it, congratulations 🎉!

[^triton]: see `generate_clip_embedding`in robotoff.triton for an example