import logging
import unittest

from robotoff import settings
from robotoff.utils.text import KeywordProcessor

logger = logging.getLogger(__name__)


class TestFileLoad(unittest.TestCase):
    def setUp(self):
        logger.info("Starting...")

    def tearDown(self):
        logger.info("Ending.")

    def test_file_format_one(self):
        keyword_processor = KeywordProcessor()
        keyword_processor.add_keyword_from_file(
            settings.TEST_DATA_DIR / "flashtext/keywords_format_one.txt"
        )
        sentence = "I know java_2e and product management techniques"
        keywords_extracted = keyword_processor.extract_keywords(sentence)
        self.assertEqual(
            keywords_extracted,
            ["java", "product management"],
            "Failed file format one test",
        )

    def test_file_format_two(self):
        keyword_processor = KeywordProcessor()
        keyword_processor.add_keyword_from_file(
            settings.TEST_DATA_DIR / "flashtext/keywords_format_two.txt"
        )
        sentence = "I know java and product management"
        keywords_extracted = keyword_processor.extract_keywords(sentence)
        self.assertEqual(
            keywords_extracted,
            ["java", "product management"],
            "Failed file format one test",
        )


if __name__ == "__main__":
    unittest.main()
