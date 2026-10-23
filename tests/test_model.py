"""Tests for the Erlang C model, using hand-calculated reference values
and properties any correct implementation must respect.
"""

import math

import pytest

from src.model import (
    average_speed_of_answer,
    capacity_contacts,
    erlang_b,
    erlang_c,
    interval_cost,
    required_agents,
    service_level,
    traffic_intensity,
)


# --- Reference values (classic tables / manual calculation) ---

def test_erlang_b_no_agents():
    assert erlang_b(5.0, 0) == 1.0


def test_erlang_c_one_agent_one_erlang():
    # a = 1, n = 1: every contact waits.
    assert erlang_c(1.0, 1) == pytest.approx(1.0)


def test_erlang_c_reference_a2_n3():
    # Classic table value: Erlang C(2, 3) = 4/9 = 0.4444.
    assert erlang_c(2.0, 3) == pytest.approx(4.0 / 9.0, rel=1e-6)


def test_erlang_c_unstable_queue():
    # n <= a: the queue grows without bound, waiting is certain.
    assert erlang_c(8.0, 8) == 1.0
    assert erlang_c(8.0, 5) == 1.0


def test_erlang_c_against_independent_implementation():
    # Log-space implementation, independent of the recursion used in
    # src/model.py. Both paths must agree.
    def erlang_c_log(a, n):
        log_num = n * math.log(a) - math.lgamma(n + 1) + math.log(n / (n - a))
        terms = [k * math.log(a) - math.lgamma(k + 1) for k in range(n)]
        m = max(terms + [log_num])
        denom = sum(math.exp(t - m) for t in terms) + math.exp(log_num - m)
        return math.exp(log_num - m) / denom

    for a, n in [(0.5, 1), (2.0, 3), (8.0, 12), (25.0, 30), (100.0, 110)]:
        assert erlang_c(a, n) == pytest.approx(erlang_c_log(a, n), rel=1e-9)


def test_erlang_c_decreases_with_agents():
    values = [erlang_c(8.0, n) for n in range(9, 20)]
    assert all(a > b for a, b in zip(values, values[1:]))


# --- Service level ---

def test_service_level_zero_target():
    # With a 0s target, SL = 1 - P(wait).
    a, n, aht = 4.0, 6, 300.0
    assert service_level(a, n, aht, 0.0) == pytest.approx(1.0 - erlang_c(a, n))


def test_service_level_grows_with_target_time():
    sl_10 = service_level(4.0, 6, 300.0, 10.0)
    sl_60 = service_level(4.0, 6, 300.0, 60.0)
    assert 0 < sl_10 < sl_60 < 1


def test_asa_reference():
    # a=2, n=3, AHT=300s: ASA = P(wait) * AHT / (n - a) = (4/9)*300/1.
    assert average_speed_of_answer(2.0, 3, 300.0) == pytest.approx(400.0 / 3.0, rel=1e-6)


def test_asa_unstable_queue():
    assert average_speed_of_answer(8.0, 8, 300.0) == math.inf


# --- Staffing ---

def test_required_agents_reference():
    # a = 8 Erlangs, AHT 300s, target 80% in 20s.
    # Checked against an Erlang C table: with 11 agents SL ≈ 76.4% (< 80%);
    # with 12 agents SL ≈ 85.5% (>= 80%). Expected answer: 12.
    n = required_agents(8.0, 300.0, 0.80, 20.0)
    assert n == 12
    assert service_level(8.0, 11, 300.0, 20.0) < 0.80
    assert service_level(8.0, 12, 300.0, 20.0) >= 0.80


def test_required_agents_stable_minimum():
    # Never returns fewer agents than needed for a stable queue.
    n = required_agents(8.0, 300.0, 0.50, 600.0)
    assert n > 8.0


def test_required_agents_no_demand():
    assert required_agents(0.0, 300.0, 0.80, 20.0) == 0


def test_required_agents_invalid_target():
    with pytest.raises(ValueError):
        required_agents(8.0, 300.0, 1.5, 20.0)


# --- Capacity, traffic and cost ---

def test_traffic_intensity():
    # 60 contacts of 300s in 30 min (1800s) = 10 Erlangs.
    assert traffic_intensity(60, 300, 1800) == pytest.approx(10.0)


def test_capacity():
    # 12 agents x 1800s / 300s = 72 contacts.
    assert capacity_contacts(12, 300, 1800) == pytest.approx(72.0)


def test_interval_cost():
    # 12 agents at 25/hour, 30 min = 12 * 25 * 0.5 = 150.
    assert interval_cost(12, 25.0, 1800) == pytest.approx(150.0)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        service_level(4.0, 6, 0.0, 20.0)
    with pytest.raises(ValueError):
        capacity_contacts(5, -1, 1800)
    with pytest.raises(ValueError):
        interval_cost(5, -10.0, 1800)
