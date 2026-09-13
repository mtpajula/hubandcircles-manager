"""WCAG contrast ratio: known values from the WCAG 2 definition."""

import pytest

from manager.color import contrast_ratio, relative_luminance


def test_luminance_extremes():
    assert relative_luminance("#000000") == 0.0
    assert relative_luminance("#ffffff") == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("#000000", "#FFFFFF", 21.0),
        ("#FFFFFF", "#000000", 21.0),  # symmetric
        ("#777777", "#FFFFFF", 4.48),  # the classic "just fails AA" grey
        ("#9A6414", "#FFFFFF", 4.99),  # fixture gravel primary, checked by hand
    ],
)
def test_contrast_ratio(a, b, expected):
    assert contrast_ratio(a, b) == pytest.approx(expected, abs=0.01)
