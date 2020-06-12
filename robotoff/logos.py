from typing import List

from robotoff import settings
from robotoff.models import ImageModel, LogoAnnotation
from robotoff.utils import get_logger, http_session


logger = get_logger(__name__)


def add_logos_to_ann(image: ImageModel, logos: List[LogoAnnotation]) -> int:
    if not logos:
        return 0

    image_url = settings.OFF_IMAGE_BASE_URL + image.source_image

    data = {
        "image_url": image_url,
        "logos": [{"bounding_box": logo.bounding_box, "id": logo.id} for logo in logos],
    }
    r = http_session.post(
        "https://robotoff.openfoodfacts.org/api/v1/ann/add", json=data, timeout=30
    )

    if not r.ok:
        logger.warning(f"error while adding image to ANN ({r.status_code}): {r.text}")
        return 0

    return r.json()["added"]


def save_nearest_neighbors(logos: List[LogoAnnotation]) -> int:
    logo_ids_params = ",".join((str(logo.id) for logo in logos))
    r = http_session.get(
        f"https://robotoff.openfoodfacts.org/api/v1/ann/batch?logo_ids={logo_ids_params}",
        timeout=30,
    )

    response = r.json()
    results = {int(key): value for key, value in response["results"].items()}

    logo_id_to_logo = {logo.id: logo for logo in logos}
    missing_logo_ids = set(logo_id_to_logo.keys()).difference(set(results.keys()))

    if missing_logo_ids:
        logger.warning(f"Missing logo IDs in response: {missing_logo_ids}")

    saved = 0
    for logo_id, logo_results in results.items():
        if logo_id in logo_id_to_logo:
            logo = logo_id_to_logo[logo_id]
            distances = [n["distance"] for n in logo_results]
            logo_ids = [n["logo_id"] for n in logo_results]
            logo.nearest_neighbors = {
                "distances": distances,
                "logo_ids": logo_ids,
            }
            logo.save()
            saved += 1

    return saved
