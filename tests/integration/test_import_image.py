import numpy as np
import pytest
from PIL import Image

from robotoff import settings
from robotoff.models import LogoEmbedding
from robotoff.workers.tasks.import_image import (
    process_created_logos,
    save_logo_embeddings,
)

from .models_utils import (
    ImagePredictionFactory,
    LogoAnnotationFactory,
    LogoEmbeddingFactory,
    clean_db,
)


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        clean_db()
        # Run the test case.
    yield

    with peewee_db:
        clean_db()


def test_save_logo_embeddings(peewee_db, mocker):
    expected_embeddings = np.random.rand(5, 512).astype(np.float32)
    generate_clip_embedding_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.generate_clip_embedding",
        return_value=expected_embeddings,
    )

    image_array = np.random.rand(800, 800, 3) * 255
    image = Image.fromarray(image_array.astype("uint8")).convert("RGB")
    with peewee_db:
        image_prediction = ImagePredictionFactory()
        logos = [
            LogoAnnotationFactory(image_prediction=image_prediction, index=i)
            for i in range(5)
        ]
        save_logo_embeddings(logos, image)
        logo_embedding_instances = LogoEmbedding.select().where(
            LogoEmbedding.logo_id.in_([logo.id for logo in logos])
        )

        assert len(logo_embedding_instances) == 5
        assert generate_clip_embedding_mock.called
        logo_id_to_logo_embedding = {
            instance.logo_id: instance for instance in logo_embedding_instances
        }

        for i, logo in enumerate(logos):
            assert logo.id in logo_id_to_logo_embedding
            embedding = np.frombuffer(
                logo_id_to_logo_embedding[logo.id].embedding, dtype=np.float32
            ).reshape((1, 512))
            assert (embedding == expected_embeddings[i]).all()


def test_process_created_logos(peewee_db, mocker):
    add_logos_to_ann_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.add_logos_to_ann",
        return_value=None,
    )
    save_nearest_neighbors_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.save_nearest_neighbors",
        return_value=None,
    )
    get_logo_confidence_thresholds_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.get_logo_confidence_thresholds",
        return_value=dict,
    )
    import_logo_insights_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.import_logo_insights",
        return_value=1,
    )

    with peewee_db:
        image_prediction = ImagePredictionFactory()
        logos = [
            LogoAnnotationFactory(image_prediction=image_prediction, index=i)
            for i in range(5)
        ]
        logo_embeddings = [LogoEmbeddingFactory(logo=logo) for logo in logos]
        process_created_logos(
            image_prediction.id, server_domain=settings.OFF_SERVER_DOMAIN
        )
        add_logos_to_ann_mock.assert_called()
        embedding_args = add_logos_to_ann_mock.mock_calls[0].args[0]
        assert sorted(embedding_args, key=lambda x: x.logo_id) == logo_embeddings
        save_nearest_neighbors_mock.assert_called()
        get_logo_confidence_thresholds_mock.assert_called()
        import_logo_insights_mock.assert_called()
