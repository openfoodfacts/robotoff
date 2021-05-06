"""Run the file with main function in terminal to load Le Wagon model from google drive directly in the app.
It can take several minutes.
The model size shouldn't be less than 1G0 (sould be 1,44 GO).
"""

import requests

def download_file_from_google_drive(id, destination):
    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value

        return None

    def save_response_content(response, destination):
        CHUNK_SIZE = 32768

        with open(destination, "wb") as f:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)

    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params = { 'id' : id }, stream = True)
    token = get_confirm_token(response)

    if token:
        params = { 'id' : id, 'confirm' : token }
        response = session.get(URL, params = params, stream = True)

    save_response_content(response, destination)



if __name__ == "__main__":
    file_id = '1TTzoKQ_G_NxOeU742DyJ8eQwNZbwn3mD'
    destination = 'bestridge.joblib'
    download_file_from_google_drive(file_id, destination)
