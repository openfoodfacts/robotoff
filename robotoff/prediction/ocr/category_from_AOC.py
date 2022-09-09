import re
from typing import Dict, Iterable, List, Optional, Union

from robotoff import settings
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.utils import get_logger
from robotoff.taxonomy import Taxonomy, TaxonomyNode, get_taxonomy

from .dataclass import OCRField, OCRRegex, OCRResult, get_text


logger = get_logger(__name__)


def process_category(lang, match) -> Optional[str]:
    '''Function to process the name of the category extracted from the AOC
    recognition. We want it to match categories found in the categories 
    taxonomy database. If nothing is found, we don't return the category.'''

    unchecked_category = str(lang) + ":" + match.group().replace(' ', '-')

    checked_category = get_taxonomy("category").__getitem__(unchecked_category)

    if checked_category is not None:
        return unchecked_category

    return None


'''We must increase the scale of prediction of our REGEX 
Many names of AOC products are written this way : 
"AMARONE della VALPONE"
"Denominazione di Origine Controllata"
'''
AOC_REGEX = {
    "fr": [
        OCRRegex(
            re.compile(r"(?<=appellation\s).*(?=(\scontr[ôo]l[ée]e)|(\sprot[ée]g[ée]e))"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
            processing_func=process_category,
        ),
        OCRRegex(
            re.compile(r"^.*(?=\sappellation d'origine contr[ôo]l[ée]e|\sappellation d'origine prot[ée]g[ée]e)"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
            processing_func=process_category,
        ),
    ],
}


def find_category_from_AOC(content: Union[OCRResult, str]) -> List[Prediction]:
    '''This function returns a prediction of the category of the product 
    by detecting an AOC syntax which allows an easy category 
    prediction with REGEX'''

    predictions = []

    for lang, regex_list in AOC_REGEX.items():
        for ocr_regex in regex_list:
            text = get_text(content, ocr_regex)

            if not text:
                continue

            for match in ocr_regex.regex.finditer(text):
                category_value = ocr_regex.processing_func(lang, match)

                if category_value is not None :

                    predictions.append(
                        Prediction(
                            type=PredictionType.category,
                            value_tag=category_value,
                            predictor="regex",
                            data={"text": match.group(), "notify": ocr_regex.notify},
                        )
                    )

    return predictions
