from robotoff import settings
from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation
from robotoff.types import ServerType


def test_crop_image_url(monkeypatch):
    monkeypatch.delenv("ROBOTOFF_SCHEME", raising=False)  # force defaults to apply
    logo_annotation = LogoAnnotation(
        image_prediction=ImagePrediction(
            type="label",
            model_name="test-model",
            model_version="1.0",
            image=ImageModel(
                barcode="123",
                image_id="1",
                source_image="/123/1.jpg",
                width=20,
                height=20,
                server_type=ServerType.off.name,
            ),
        ),
        bounding_box=(1, 1, 2, 2),
        barcode="123",
        source_image="/123/1.jpg",
    )

    assert logo_annotation.get_crop_image_url() == (
        f"{settings.BaseURLProvider.robotoff()}/api/v1/images/crop"
        + f"?image_url={settings.BaseURLProvider.image_url(ServerType.off, '/123/1.jpg')}&y_min=1&x_min=1&y_max=2&x_max=2"
    )
