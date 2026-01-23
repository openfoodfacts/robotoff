from unittest.mock import patch, Mock

from robotoff.prediction.langid import predict_lang


@patch("robotoff.prediction.langid.http_session.post")
def test_predict_lang_portuguese(mock_post):
    
    mock_response = Mock()
    mock_response.json.return_value = [
        (["pt", "es"], [0.92, 0.05])
    ]
    mock_post.return_value = mock_response

    result = predict_lang("Informação nutricional")

    assert result[0].lang == "pt"
    assert result[0].confidence > 0.9
