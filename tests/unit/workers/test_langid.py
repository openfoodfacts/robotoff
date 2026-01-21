from robotoff.prediction.langid import predict_lang

def test_portuguese_nutrition_language_detection():
    text = "Valor energético 200 kcal Gorduras 10 g"
    predictions = predict_lang(text)
    assert predictions[0].lang == "pt"
