import pytest

from robotoff.brands import BRAND_PREFIX_STORE, in_barcode_range


@pytest.mark.parametrize('barcode,brand_tag,is_valid', [
    ("5400141651306", "boni", True),
    ("5400142968395", "boni", False),
    ("3406790524499", "boni", False),
    ("3406790524499", "unknown-brand", False),
    ("3660523327656", "jeff-de-bruges", True),
    ("2968248002546", "thomas", False),
    ("3350240540277", "maison-prunier", True),

])
def test_in_barcode_range(barcode, brand_tag, is_valid):
    brand_prefix = BRAND_PREFIX_STORE.get()
    assert in_barcode_range(brand_prefix, brand_tag,
                            barcode) is is_valid
