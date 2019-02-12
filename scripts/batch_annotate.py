from robotoff.insights.annotate import InsightAnnotatorFactory
from robotoff.models import ProductInsight


insight_type = 'packager_code'
annotator = InsightAnnotatorFactory.create(insight_type)


i = 0
for insight in ProductInsight.select().where(ProductInsight.type == insight_type,
                                             ProductInsight.annotation.is_null()):
    i += 1
    print("Insight %d" % i)
    if insight.data['matcher_type'] != 'eu_fr':
        continue

    print("Add emb code {} to https://fr.openfoodfacts.org/produit/{}".format(insight.data['text'], insight.barcode))
    print(insight.data)
    annotator.save_annotation(insight)
    insight.annotation = 1
    insight.save()
