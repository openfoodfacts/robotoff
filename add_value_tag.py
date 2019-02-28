from robotoff.models import ProductInsight, db


print("Starting migration")

updated = 0
with db:
    with db.atomic():
        product: ProductInsight
        for product in ProductInsight.select().iterator():
            if product.type == 'label':
                value_tag = product.data['label_tag']
            elif product.type == 'category':
                value_tag = product.data['category']
            elif product.type == 'packager_code':
                value_tag = product.data['text']
            else:
                continue

            product.value_tag = value_tag
            product.save()
            updated += 1

            if updated % 1000 == 0:
                print("{} products updated".format(updated))


print("Migration finished, updated {} fields".format(updated))
