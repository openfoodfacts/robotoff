from robotoff.elasticsearch.category.predict import predict_from_product


def test_predict_from_product_missing_product_name():
    product = {"code": "XXX", "languages_codes": ["fr"]}
    assert predict_from_product(product) is None
