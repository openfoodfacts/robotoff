import ast
from typing import Dict, Optional

from robotoff.insights.annotate import InsightAnnotatorFactory
from robotoff.models import ProductInsight
from robotoff.settings import BaseURLProvider


def run(insight_type: str, dry: bool = True, json_contains_str: Optional[str] = None):
    if json_contains_str is not None:
        json_contains = ast.literal_eval(json_contains_str)
    else:
        json_contains = None

    batch_annotate(insight_type, dry, json_contains)


def batch_annotate(
    insight_type: str, dry: bool = True, json_contains: Optional[Dict] = None
):
    annotator = InsightAnnotatorFactory.get(insight_type)

    i = 0

    query = ProductInsight.select()
    where_clauses = [
        ProductInsight.type == insight_type,
        ProductInsight.annotation.is_null(),
        ProductInsight.annotation.latent == False,  # noqa: E712
    ]

    if json_contains is not None:
        where_clauses.append(ProductInsight.data.contains(json_contains))

    query = query.where(*where_clauses)

    if dry:
        count = query.count()
        print(
            "-- dry run --\n"
            "{} items matching filter:\n"
            "   insight type: {}\n"
            "   filter: {}"
            "".format(count, insight_type, json_contains)
        )
    else:
        for insight in query:
            i += 1
            print("Insight %d" % i)
            print(
                "Add label {} to {}/product/{}"
                "".format(insight.data, BaseURLProvider().get(), insight.barcode)
            )
            print(insight.data)

            annotator.annotate(insight, 1, update=True)
