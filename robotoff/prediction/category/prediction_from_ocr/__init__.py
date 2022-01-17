"""
➡️ About the model:

    The ML model used in predictor.py was trained by students of Le Wagon (Data Science bootcamp) during their final project in mars 2021.
    Its purpose is to associate a product category to each list of ingredients (retrieved by OCR).
    The pipeline combines a Ridge Classifier with a TF_IDF (n_grams= 2 and French NLTK stop_words as parameters).
    It obtains the best results (84% accuracy) on text simply cleaned up text from OCR (accents, special characters, spaces, numbers, etc.)

    When the model is wrong, it's sometimes due to the ambiguity of the category. For exemple, soup and one dish meal can be true categories for a same product.
    That's why below a threshold of certainty, the result has been set to return the first two categories predicted.

    To know more about the model and how it was trained : https://github.com/Laurel16/OpenFoodFactsCategorizer.

➡️ About the integration in Robotoff:

    The predict function in predictor.py is:
    1/ called in robotoff/prediction/ocr/category.py (into predict_ocr_categories which return a Prediction).
    2/ the function predict_ocr_categories is then called in robotoff/prediction/ocr/core.py (extract_predictions) and robotoff/insights/extraction.py (get_predictions_from_image).

    Robotoff receives the information that a new image has been imported via this endpoint: "/api/v1/images/import".
    Parameters are: barcode, image_url and ocr_url.
    A task is sent to a worker to perform an action on the image.
    The task import_image is triggered (defined in robotoff/workers/tasks/import_image.py )
    It saves the image, launch object detection and then call get_predictions_from_image which also takes as input barcode/image_url/ocr_url.

➡️ About the command line to test the insights returned from the model:

    Robotoff provides a command line tool to test the generation of insights.
    You need to know the barcode of a product you want to test.
    For exemple: nutella product (https://fr.openfoodfacts.org/produit/3017620422003/nutella-ferrero) with barcode "3017620422003".

    Then run:
    "python -m robotoff generate-ocr-insights 3017620422003 --insight-type category"

    It takes basically a barcode and predicts category insights from the OCR.
    It should output a lot of insights like this one:
    {"insights": [{"type": "category", "data": {"proba": "sweets", "max_confidence": 0.1246}, "value_tag": null, "value": null, "automatic_processing": null, "predictor": "ridge_model-ml"}], "barcode": "3017620422003", "type": "category", "source_image": "/301/762/042/2003/1.jpg"}

    The command line tool is defined in robotoff/robotoff/main.py.
    To see all the command line tools, run "python -m robotoff --help"

"""
