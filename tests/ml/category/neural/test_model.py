from robotoff.ml.category.neural.model import predict_from_product


def test_predict_from_product_missing_product_name():
    product = {"code": "XXX", "languages_codes": ["fr"]}
    predictions = predict_from_product(product)
    assert predictions == []
