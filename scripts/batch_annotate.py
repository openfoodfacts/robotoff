from robotoff.insights.annotate import InsightAnnotatorFactory
from robotoff.models import ProductInsight


insight_type = 'packager_code'
annotator = InsightAnnotatorFactory.create(insight_type)


for insight in ProductInsight.select().where(ProductInsight.type == insight_type,
                                             ProductInsight.annotation.is_null()):
    print("Add emb code {} to https://fr.openfoodfacts.net/produit/{}".format(insight.data['text'], insight.barcode))
    print(insight.data)
    annotator.save_annotation(insight)
    insight.annotation = 1
    insight.save()
