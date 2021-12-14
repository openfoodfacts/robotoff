import pytest
from falcon import testing

from robotoff.app.api import api


@pytest.fixture()
def client():
    return testing.TestClient(api)


def test_get_random_question(client):
    response = self.simulate_get("/api/v1/questions/random")
    assert response.json == {}
