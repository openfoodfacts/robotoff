from falcon import testing
import pytest

from robotoff.app.api import api
from robotoff.models import ProductInsight

insight_id = "94371643-c2bc-4291-a585-af2cb1a5270a"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # Set up.
    ProductInsight.create(
        id=insight_id,
        data="{}",
        barcode=1,
        type="category",
        n_votes=0,
        latent=False,
        value_tag="en:seeds",
        server_domain="api.openfoodfacts.net",
        automatic_processing=False,
        unique_scans_n=0,
        reserved_barcode=False,
    )

    # Run the test case.
    yield

    # Tear down.
    ProductInsight.delete().execute()


def client():
    return testing.TestClient(api)


def test_random_question():
    cl = client()
    result = cl.simulate_get("/api/v1/questions/random")

    assert result.status_code == 200
    assert result.json == {
        "count": 1,
        "questions": [
            {
                "barcode": "1",
                "type": "add-binary",
                "value": "Seeds",
                "question": "Does the product belong to this category?",
                "insight_id": insight_id,
                "insight_type": "category",
            }
        ],
        "status": "found",
    }
