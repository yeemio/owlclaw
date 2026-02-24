"""Unit tests for time_decay function (mathematical correctness)."""

import math

import pytest

from owlclaw.agent.memory.store_pgvector import time_decay


def test_time_decay_zero_age() -> None:
    """At age 0, weight is 1.0."""
    assert time_decay(0.0) == 1.0
    assert time_decay(0.0, half_life_hours=24.0) == 1.0


def test_time_decay_negative_age() -> None:
    """Negative age is treated as 0 (weight 1.0)."""
    assert time_decay(-1.0) == 1.0


def test_time_decay_at_half_life() -> None:
    """At t = half_life_hours, weight ≈ 0.5 (exp(-0.693) ≈ 0.5)."""
    half = 168.0
    w = time_decay(half, half_life_hours=half)
    assert abs(w - 0.5) < 0.01


def test_time_decay_two_half_lives() -> None:
    """At t = 2 * half_life, weight ≈ 0.25."""
    half = 168.0
    w = time_decay(2 * half, half_life_hours=half)
    expected = 0.25
    assert abs(w - expected) < 0.02


def test_time_decay_monotonic_decrease() -> None:
    """Weight decreases as age increases."""
    half = 24.0
    prev = 1.0
    for hours in [1, 6, 12, 24, 48, 168]:
        w = time_decay(hours, half_life_hours=half)
        assert w <= prev
        assert 0 <= w <= 1
        prev = w


def test_time_decay_formula() -> None:
    """Explicit formula: exp(-0.693 * age / half_life)."""
    age = 84.0
    half_life = 168.0
    expected = math.exp(-0.693 * age / half_life)
    assert time_decay(age, half_life_hours=half_life) == pytest.approx(expected)


def test_time_decay_rejects_non_positive_half_life() -> None:
    with pytest.raises(ValueError, match="half_life_hours must be > 0"):
        time_decay(1.0, half_life_hours=0)
    with pytest.raises(ValueError, match="half_life_hours must be > 0"):
        time_decay(1.0, half_life_hours=-1.0)
