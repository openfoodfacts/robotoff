import json
import logging
import unittest

from robotoff import settings
from robotoff.utils.text import KeywordProcessor

logger = logging.getLogger(__name__)


class TestKeywordExtractor(unittest.TestCase):
    def setUp(self):
        logger.info("Starting...")
        with open(
            settings.TEST_DATA_DIR / "flashtext/keyword_extractor_test_cases.json"
        ) as f:
            self.test_cases = json.load(f)

    def tearDown(self):
        logger.info("Ending.")

    def test_extract_keywords(self):
        """For each of the test case initialize a new KeywordProcessor.
        Add the keywords the test case to KeywordProcessor.
        Extract keywords and check if they match the expected result for the test case.

        """
        for test_id, test_case in enumerate(self.test_cases):
            keyword_processor = KeywordProcessor()
            keyword_processor.add_keywords_from_dict(test_case["keyword_dict"])
            keywords_extracted = keyword_processor.extract_keywords(
                test_case["sentence"]
            )
            self.assertEqual(
                keywords_extracted,
                test_case["keywords"],
                "keywords_extracted don't match the expected results for test case: {}".format(
                    test_id
                ),
            )

    def test_extract_keywords_case_sensitive(self):
        """For each of the test case initialize a new KeywordProcessor.
        Add the keywords the test case to KeywordProcessor.
        Extract keywords and check if they match the expected result for the test case.

        """
        for test_id, test_case in enumerate(self.test_cases):
            keyword_processor = KeywordProcessor(case_sensitive=True)
            keyword_processor.add_keywords_from_dict(test_case["keyword_dict"])
            keywords_extracted = keyword_processor.extract_keywords(
                test_case["sentence"]
            )
            self.assertEqual(
                keywords_extracted,
                test_case["keywords_case_sensitive"],
                "keywords_extracted don't match the expected results for test case: {}".format(
                    test_id
                ),
            )

    def test_extract_keywords_case_insensitive_with_string_length_change(self):
        sentence = "Word İngredients LTD İmages nutriments i̇ngredients PROTEİNS"
        keyword_processor = KeywordProcessor(case_sensitive=False)
        keyword_processor.add_keyword("İngredients", "ingredients")
        keyword_processor.add_keyword("nutriments", "nutriments")
        keyword_processor.add_keyword("PROTEİNS", "proteins")
        extracted_keywords = keyword_processor.extract_keywords(
            sentence, span_info=True
        )
        self.assertEqual(
            extracted_keywords,
            [
                ("ingredients", 5, 16),
                ("nutriments", 28, 38),
                ("ingredients", 39, 51),
                ("proteins", 52, 60),
            ],
        )


if __name__ == "__main__":
    unittest.main()
