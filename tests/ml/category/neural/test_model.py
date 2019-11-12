from robotoff.ml.category.neural.model import predict_from_product


def test_predict_from_product_missing_product_name():
    product = {
        'code': "XXX",
        'languages_codes': ['fr']
    }
    predictions = predict_from_product(product)
    assert predictions is None


def test_predict_from_product_non_fr_lang():
    product = {
        'code': "XXX",
        'languages_codes': ['en'],
        'product_name': "test",
    }
    predictions = predict_from_product(product)
    assert predictions is None
