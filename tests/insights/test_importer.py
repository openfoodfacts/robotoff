import pytest

from robotoff.insights.importer import BrandInsightImporter


class TestBrandInsightImporter:
    @pytest.mark.parametrize('barcode,brand_tag,is_valid', [
        ("5400141651306", "boni", True),
        ("5400142968395", "boni", False),
        ("3406790524499", "boni", False),
        ("025252", "boni", False),
        ("3406790524499", "unknown-brand", True),

    ])
    def test_generate_full_correction(self, barcode, brand_tag, is_valid):
        assert BrandInsightImporter.in_barcode_range(brand_tag, barcode) is is_valid
