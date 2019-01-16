import datetime
import json
import uuid

from robotoff.app.models import batch_insert, ProductInsight

KEEP_TYPE = {
    'packager_codes'
}


def read_insights(json_path, timestamp=None):
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()

    with open(str(json_path), 'r') as f:
        for line in f:
            item = json.loads(line)
            barcode = item['barcode']
            source = item['source']

            for insight_type, insights in item['insights'].items():
                if insight_type not in KEEP_TYPE:
                    continue

                for insight in insights:
                    yield {
                        'id': str(uuid.uuid4()),
                        'barcode': barcode,
                        'type': insight_type,
                        'timestamp': timestamp,
                        'data': {
                            'text': insight['text'],
                            'pattern_type': insight['type'],
                            'source': source,
                        }
                    }


if __name__ == "__main__":
    insight_stream = read_insights('/home/raphael/Projects/openfoodfacts-ocr-analysis/insights_2.jsonl')
    batch_insert(ProductInsight, insight_stream)
