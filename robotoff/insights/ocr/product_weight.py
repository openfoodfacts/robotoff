import functools
import re
from typing import Dict, List

from robotoff.insights.ocr.dataclass import OCRRegex, OCRField, OCRResult


def process_product_weight(match, prompt: bool) -> Dict:
    raw = match.group()

    if prompt:
        prompt_str = match.group(1)
        value = match.group(2)
        unit = match.group(3)
    else:
        prompt_str = None
        value = match.group(1)
        unit = match.group(2)

    if unit in ('dle', 'cle', 'mge', 'mle', 'ge', 'kge', 'le'):
        # When the e letter often comes after the weight unit, the
        # space is often not detected
        unit = unit[:-1]

    text = "{} {}".format(value, unit)
    result = {
        'text': text,
        'raw': raw,
        'value': value,
        'unit': unit,
    }

    if prompt_str is not None:
        result['prompt'] = prompt_str

    return result


def process_multi_packaging(match) -> Dict:
    raw = match.group()

    count = match.group(1)
    value = match.group(2)
    unit = match.group(3)

    if unit in ('dle', 'cle', 'mge', 'mle', 'ge', 'kge', 'le'):
        # When the e letter often comes after the weight unit, the
        # space is often not detected
        unit = unit[:-1]

    text = "{} x {} {}".format(count, value, unit)
    result = {
        'text': text,
        'raw': raw,
        'value': value,
        'unit': unit,
        'count': count
    }

    return result


PRODUCT_WEIGHT_REGEX: Dict[str, OCRRegex] = {
    'with_mention': OCRRegex(
        re.compile(r"(poids|poids net [aà] l'emballage|poids net|poids net égoutté|masse nette|volume net total|net weight|net wt\.?|peso neto|peso liquido|netto[ -]?gewicht)\s?:?\s?([0-9]+[,.]?[0-9]*)\s?(fl oz|dle?|cle?|mge?|mle?|lbs|oz|ge?|kge?|le?)(?![a-z])"),
        field=OCRField.full_text_contiguous,
        lowercase=True,
        processing_func=functools.partial(process_product_weight, prompt=True),
        priority=1),
    'multi_packaging': OCRRegex(
        re.compile(r"(\d+)\s?x\s?([0-9]+[,.]?[0-9]*)\s?(fl oz|dle?|cle?|mge?|mle?|lbs|oz|ge?|kge?|le?)(?![a-z])"),
        field=OCRField.full_text_contiguous,
        lowercase=True,
        processing_func=process_multi_packaging,
        priority=2),
    'no_mention': OCRRegex(
        re.compile(r"([0-9]+[,.]?[0-9]*)\s?(dle|cle|mge|mle|ge|kge)(?![a-z])"),
        field=OCRField.full_text_contiguous,
        lowercase=True,
        processing_func=functools.partial(process_product_weight, prompt=False),
        priority=3),
}


def find_product_weight(ocr_result: OCRResult) -> List[Dict]:
    results = []

    for type_, ocr_regex in PRODUCT_WEIGHT_REGEX.items():
        text = ocr_result.get_text(ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            if ocr_regex.processing_func is None:
                continue

            result = ocr_regex.processing_func(match)
            result['matcher_type'] = type_
            result['priority'] = ocr_regex.priority
            result['notify'] = ocr_regex.notify
            results.append(result)

    return results
