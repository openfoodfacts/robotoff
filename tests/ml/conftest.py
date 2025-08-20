from pathlib import Path

import pytest

from robotoff.settings import DEFAULT_TRITON_URI
from robotoff.triton import get_triton_inference_stub

ML_TEST_DIR = Path(__file__).parent


def pytest_addoption(parser):
    parser.addoption("--update-results", action="store_true", default=False)
    parser.addoption("--triton-uri", action="store", default=DEFAULT_TRITON_URI)
    parser.addoption("--output-dir", action="store", default="test_results")


@pytest.fixture(scope="session")
def update_results(pytestconfig) -> bool:
    return pytestconfig.getoption("update_results")


@pytest.fixture(scope="session")
def output_dir(pytestconfig) -> Path:
    return ML_TEST_DIR / pytestconfig.getoption("output_dir")


@pytest.fixture(scope="session")
def triton_uri(pytestconfig) -> str:
    return pytestconfig.getoption("triton_uri")


@pytest.fixture(scope="session")
def triton_stub(triton_uri: str):
    return get_triton_inference_stub(triton_uri)
