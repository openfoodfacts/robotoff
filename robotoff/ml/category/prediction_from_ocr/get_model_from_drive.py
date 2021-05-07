"""
Run the file with main function in terminal to load Le Wagon model
from google drive directly in the app. It can take several minutes.

The model size should be 1,44 Go.
"""
import requests

URL = "https://docs.google.com/uc?export=download"


def download_file_from_google_drive(file_id, destination):
    """Download a file from Google Drive."""
    request_params = {"id": file_id}

    session = requests.Session()
    response = session.get(URL, params=request_params, stream=True)

    token = _get_confirm_token(response)
    if token:
        request_params["confirm"] = token
        response = session.get(URL, params=request_params, stream=True)

    _save_response_content(response, destination)


def _get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    return None


def _save_response_content(response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)


if __name__ == "__main__":
    from .constants import RIDGE_PREDICTOR_FILEPATH, RIDGE_PREDICTOR_GOOGLE_DRIVE_ID

    download_file_from_google_drive(
        file_id=RIDGE_PREDICTOR_GOOGLE_DRIVE_ID,
        destination=RIDGE_PREDICTOR_FILEPATH,
    )
