from robotoff import settings
from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation


def test_crop_image_url(monkeypatch):
    monkeypatch.delenv("ROBOTOFF_SCHEME", raising=False)  # force defaults to apply
    logo_annotation = LogoAnnotation(
        image_prediction=ImagePrediction(
            type="label",
            model_name="test-model",
            model_version="1.0",
            image=ImageModel(
                barcode="123",
                image_id="image_id",
                source_image="/image",
                width=20,
                height=20,
            ),
        ),
        bounding_box=(1, 1, 2, 2),
    )

    assert logo_annotation.get_crop_image_url() == (
        f"https://robotoff.{settings._robotoff_domain}/api/v1/images/crop"
        + f"?image_url={settings.OFF_IMAGE_BASE_URL}/image&y_min=1&x_min=1&y_max=2&x_max=2"
    )
