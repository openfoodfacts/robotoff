import datetime

import pytest

from robotoff.prediction.ocr.expiration_date import (
    MAX_YEARS_IN_FUTURE,
    MAX_YEARS_IN_PAST,
    find_expiration_date,
    is_plausible_expiration_date,
)
from robotoff.types import PredictionType

TODAY = datetime.date(2026, 7, 24)


@pytest.mark.parametrize(
    "date,expected",
    [
        # in-window dates are plausible
        (datetime.date(2026, 6, 14), True),
        (datetime.date(2027, 1, 1), True),
        (TODAY, True),
        # boundaries (inclusive)
        (datetime.date(TODAY.year + MAX_YEARS_IN_FUTURE, 1, 1), True),
        (datetime.date(TODAY.year - MAX_YEARS_IN_PAST, 12, 31), True),
        # just outside the window
        (datetime.date(TODAY.year + MAX_YEARS_IN_FUTURE + 1, 1, 1), False),
        (datetime.date(TODAY.year - MAX_YEARS_IN_PAST - 1, 12, 31), False),
    ],
)
def test_is_plausible_expiration_date(date, expected):
    assert is_plausible_expiration_date(date, today=TODAY) is expected


def test_is_plausible_expiration_date_defaults_to_today():
    # A date in the current year must always be plausible, whatever the year the
    # test runs in (guards against the previous hardcoded-window regression).
    today = datetime.date.today()
    assert is_plausible_expiration_date(datetime.date(today.year, 1, 1)) is True


def test_find_expiration_date_keeps_current_and_future_years():
    # Regression test for the hardcoded [2015, 2025] window that silently
    # dropped every expiration date from 2026 onwards. Build the year relative
    # to the current date so this test stays valid in future years.
    next_year = datetime.date.today().year + 1
    predictions = find_expiration_date(
        f"À consommer de préférence avant 14.06.{next_year}"
    )
    assert len(predictions) == 1
    prediction = predictions[0]
    assert prediction.type == PredictionType.expiration_date
    # value is normalized to ISO 8601
    assert prediction.value == f"{next_year}-06-14"


def test_find_expiration_date_drops_implausible_years():
    # A year far in the past is OCR noise and must be discarded.
    old_year = datetime.date.today().year - (MAX_YEARS_IN_PAST + 10)
    assert find_expiration_date(f"lot 14.06.{old_year}") == []
