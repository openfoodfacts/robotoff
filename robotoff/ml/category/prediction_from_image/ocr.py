import os
import pandas as pd
import requests


def get_data_from_ocr(url):
    """Expects url to a json ocr -from image- """
    result = requests.get(url)
    json = result.json()
    text = json['responses'][0]['fullTextAnnotation']['text']
    return text


def get_data_from_url(url, overlay=False, api_key='helloworld', language='eng'):
    """ OCR.space API request with remote file.
        Python3.5 - not tested on 2.7
    :param url: Image url.
    :param overlay: Is OCR.space overlay required in your response.
                    Defaults to False.
    :param api_key: OCR.space API key.
                    Defaults to 'helloworld'.
    :param language: Language code to be used in OCR.
                    List of available language codes can be found on https://ocr.space/OCRAPI
                    Defaults to 'en'.
    :return: Result in JSON format.
    """

    payload = {'url': url,
               'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    r = requests.post('https://api.ocr.space/parse/image',
                      data=payload,
                      )
    json = r.json()
    result = json['ParsedResults'][0]['ParsedText']
    return result

#test_url = get_data_from_url(url='https://static.openfoodfacts.org/images/products/00390804/1.jpg')
#print(test_url)
