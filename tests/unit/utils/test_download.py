from unittest.mock import patch

import pytest
import requests

from robotoff.utils.download import AssetLoadingException, get_asset_from_url


@patch("robotoff.utils.image.requests.get")
def test_get_asset_from_url(mock_get):
    # Mock the response from requests.get
    mock_response = mock_get.return_value
    mock_response.content = b"fake image content"
    mock_response.status_code = 200

    # Call the function with an image URL
    url = "https://example.com/image.jpg"
    result = get_asset_from_url(url)

    # Check that requests.get was called with the correct URL
    mock_get.assert_called_once_with(url, auth=None)

    # Check that the content of the response is the same as the mock content
    assert result.content == b"fake image content"

    # Check that the status code of the response is the same as the mock
    # status code
    assert result.status_code == 200

    # Test when r.ok returns False
    mock_response.status_code = 404
    mock_response.content = b""
    mock_response.ok = False
    with pytest.raises(AssetLoadingException):
        get_asset_from_url(url)

    # Test when there is an error during HTTP request
    mock_get.side_effect = requests.exceptions.SSLError
    with pytest.raises(AssetLoadingException):
        get_asset_from_url(url)

    # Check that the function returns None when error_raise is False
    image = get_asset_from_url(url, error_raise=False)
    assert image is None
