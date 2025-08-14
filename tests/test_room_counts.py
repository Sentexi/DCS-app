import pytest

from app.logic.assign import _compute_room_counts


def test_even_distribution_two_rooms():
    settings = [(7, 12), (7, 12)]
    counts = _compute_room_counts(17, settings)
    assert counts == [9, 8]


def test_even_distribution_multiple_rooms():
    settings = [(2, 5), (2, 5), (2, 5)]
    counts = _compute_room_counts(10, settings)
    assert sum(counts) == 10
    assert max(counts) - min(counts) <= 1
    for c, (mn, mx) in zip(counts, settings):
        assert mn <= c <= mx
