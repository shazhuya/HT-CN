import pytest

from htcn.harmonic.models import HarmonicPoint


def test_harmonic_point_is_semantic_and_immutable() -> None:
    point = HarmonicPoint(label="X", index=12, price=100.5)
    assert point.label == "X"
    assert point.index == 12
    assert point.price == 100.5
    with pytest.raises(Exception):
        point.price = 101.0  # type: ignore[misc]


def test_harmonic_point_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        HarmonicPoint(label="", index=1, price=10.0)
    with pytest.raises(ValueError):
        HarmonicPoint(label="A", index=-1, price=10.0)
    with pytest.raises(ValueError):
        HarmonicPoint(label="A", index=1, price=0.0)
