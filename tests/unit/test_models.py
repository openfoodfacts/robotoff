from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation
from robotoff.settings import _robotoff_domain


def test_crop_image_url():
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

    assert (
        logo_annotation.get_crop_image_url()
        == f'https://robotoff.{_robotoff_domain}/api/v1/images/crop?image_url=https://static.{_robotoff_domain}/images/products/image&y_min=1&x_min=1&y_max=2&x_max=2'
    )
