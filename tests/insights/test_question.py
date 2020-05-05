import pytest

from robotoff.insights.question import get_display_image


@pytest.mark.parametrize(
    "source_image,output",
    [
        ("/366/194/903/0038/1.jpg", "/366/194/903/0038/1.400.jpg"),
        ("/366/194/903/0038/20.jpg", "/366/194/903/0038/20.400.jpg"),
        ("/366/194/903/0038/20.400.jpg", "/366/194/903/0038/20.400.jpg"),
        ("/366/194/903/0038/20test.jpg", "/366/194/903/0038/20test.jpg"),
    ],
)
def test_get_display_image(source_image: str, output: str):
    assert get_display_image(source_image) == output
