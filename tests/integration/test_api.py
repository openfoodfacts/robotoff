import pytest
from falcon import testing

from robotoff.app.api import api


@pytest.fixture()
def client():
    return testing.TestClient(api)


def test_get_random_question(client):
    response = client.simulate_get("/api/v1/questions/random")
    expected_resp = {"count": 0, "questions": [], "status": "no_questions"}
    assert response.json == expected_resp
