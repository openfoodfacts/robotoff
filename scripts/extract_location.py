from pathlib import Path

import click
import pandas as pd

from robotoff.insights.ocr.core import ocr_iter
from robotoff.insights.ocr.dataclass import OCRResult
from robotoff.insights.ocr.location import AddressExtractor, load_cities_fr, get_locale


# Questions:
# * What is FullTextAnnotations vs TextAnnotations?
# * Why add all text elements at the end of text_annotations separated by ||?


@click.command()
@click.argument("ocr_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("cities_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_path", type=click.Path(dir_okay=False),
                default="location_results.df.pkl")
def main(ocr_path, cities_path, output_path):
    print("main")
    cities_path = Path(cities_path)
    cities = load_cities_fr(cities_path)
    location_extractor = AddressExtractor(cities)

    results = []
    i = 0
    for source, ocr_json in ocr_iter(ocr_path):
        ocr_result = OCRResult.from_json(ocr_json)

        res = {}
        res["source"] = source
        res["text"] = ocr_result.text_annotations_str_lower
        res["prepared_text"] = location_extractor.prepare_text(
            ocr_result.text_annotations_str_lower)
        res["locale"] = get_locale(ocr_result)
        res.update(location_extractor.extract_location(ocr_result))

        results.append(res)
        i += 1
        if i % 1000 == 0:
            print(i)
            pd.DataFrame(results).to_pickle(output_path)


if __name__ == "__main__":
    main()
