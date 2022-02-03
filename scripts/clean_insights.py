from robotoff.models import ProductInsight
from robotoff.utils import get_logger

logger = get_logger()


def check_tag_field(insight: ProductInsight, field_name: str):
    if field_name in insight.data:
        tag = insight.data[field_name]

        if tag == insight.value_tag:
            insight.data.pop(field_name)
            return True

    return False


def check_field(insight: ProductInsight, field_name: str):
    if field_name in insight.data:
        tag = insight.data[field_name]

        if tag == insight.value:
            insight.data.pop(field_name)
            return True

    return False


def run():
    count = 0
    errors = 0
    insight: ProductInsight

    for insight in ProductInsight.select(
        ProductInsight.data,
        ProductInsight.value,
        ProductInsight.value_tag,
        ProductInsight.source_image,
    ):
        save = False

        if "source" in insight.data:
            data_source_image = insight.data["source"]
            if data_source_image == insight.source_image:
                insight.data.pop("source")
                logger.info("Deleting source field for insight {}".format(insight.id))
                count += 1
                save = True
            else:
                errors += 1

        if insight.type == "label":
            if check_tag_field(insight, "label_tag"):
                save = True

        elif insight.type == "brand":
            if check_tag_field(insight, "brand_tag"):
                save = True

            if check_field(insight, "brand"):
                save = True

        elif insight.type == "store":
            if check_tag_field(insight, "store_tag"):
                save = True

            if check_field(insight, "store"):
                save = True

        elif insight.type == "packaging":
            if check_tag_field(insight, "packaging_tag"):
                save = True

            if check_field(insight, "packaging"):
                save = True

        elif insight.type == "category":
            if check_tag_field(insight, "category"):
                save = True

        if save:
            insight.save()

    logger.info("Updated insights: {}".format(count))
    logger.info("Errors: {}".format(errors))


if __name__ == "__main__":
    run()
