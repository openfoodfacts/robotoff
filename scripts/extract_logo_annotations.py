from robotoff.models import db, LogoAnnotation
from robotoff import settings
import json

annotations = {}
with db:
    for logo_annotation in (
        LogoAnnotation.select(LogoAnnotation.id, LogoAnnotation.taxonomy_value)
        .where(LogoAnnotation.taxonomy_value.is_null(False))
        .iterator()
    ):
        annotations[logo_annotation.id] = logo_annotation.taxonomy_value
with (settings.DATASET_DIR / "annotations.jsonl").open("w") as f:
    json.dump(annotations, f)
