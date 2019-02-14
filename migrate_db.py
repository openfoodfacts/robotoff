import datetime

from robotoff.insights._enum import InsightType
from robotoff.models import db, ProductInsight, CategorizationTask, batch_insert


def insert_iter():
    categorization_task: CategorizationTask = None
    import_datetime = datetime.datetime.utcnow()

    for categorization_task in CategorizationTask.select():
        if categorization_task.completed_at is not None:
            timestamp = categorization_task.completed_at
        else:
            timestamp = import_datetime

        campaign = categorization_task.campaign

        if campaign is None:
            continue

        yield {
            'id': str(categorization_task.id),
            'barcode': categorization_task.product_id,
            'type': InsightType.category.name,
            'timestamp': timestamp,
            'completed_at': categorization_task.completed_at,
            'annotation': categorization_task.annotation,
            'outdated': categorization_task.outdated,
            'countries': categorization_task.countries,
            'data': {
                'category': categorization_task.predicted_category,
                'confidence': categorization_task.confidence,
                'category_depth': categorization_task.category_depth,
                'type': campaign,
            }
        }


with db:
    with db.atomic():
        batch_insert(ProductInsight, insert_iter())
