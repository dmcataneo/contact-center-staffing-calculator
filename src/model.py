"""Staffing model for a service queue, based on Erlang C.

Model assumptions (important for reading the results):
- A single queue, with identical agents 100% dedicated to it.
- Random contact arrivals (Poisson process).
- Exponentially distributed handle times.
- No abandonment: every contact waits until it is answered.
- No breaks, meetings or other unavailability (shrinkage).
- No multiple channels or priorities.

In practice the real team needs to be larger than the model result,
because of breaks, absences and training. A common market adjustment
(shrinkage) is 20% to 35% on top of the calculated number.
"""

from __future__ import annotations

import math


def erlang_b(traffic_erlangs: float, agents: int) -> float:
    """Blocking probability in the Erlang B model (stable recursion).

    Used as an intermediate step for Erlang C. Not the calculator's
    main result.
    """
    if agents < 0:
        raise ValueError("agents must be >= 0")
    if traffic_erlangs < 0:
        raise ValueError("traffic_erlangs must be >= 0")
    b = 1.0
    for n in range(1, agents + 1):
        b = (traffic_erlangs * b) / (n + traffic_erlangs * b)
    return b


def erlang_c(traffic_erlangs: float, agents: int) -> float:
    """Probability that a contact waits in queue (P(wait > 0)).

    Requires agents > traffic_erlangs (stable queue). If agents <=
    traffic_erlangs, the queue grows without bound and the probability
    of waiting is 1.
    """
    if agents <= 0:
        raise ValueError("agents must be > 0")
    if traffic_erlangs < 0:
        raise ValueError("traffic_erlangs must be >= 0")
    if agents <= traffic_erlangs:
        return 1.0
    b = erlang_b(traffic_erlangs, agents)
    rho = traffic_erlangs / agents
    return b / (1.0 - rho * (1.0 - b))


def service_level(
    traffic_erlangs: float,
    agents: int,
    aht_seconds: float,
    target_seconds: float,
) -> float:
    """Fraction of contacts answered within target_seconds (Erlang C).

    SL = 1 - P(wait) * exp(-(agents - a) * t / AHT).
    """
    if aht_seconds <= 0:
        raise ValueError("aht_seconds must be > 0")
    if target_seconds < 0:
        raise ValueError("target_seconds must be >= 0")
    pw = erlang_c(traffic_erlangs, agents)
    if agents <= traffic_erlangs:
        return 0.0
    return 1.0 - pw * math.exp(-(agents - traffic_erlangs) * target_seconds / aht_seconds)


def average_speed_of_answer(
    traffic_erlangs: float, agents: int, aht_seconds: float
) -> float:
    """Average time a contact waits in queue, in seconds.

    Returns math.inf when the queue is unstable (agents <= traffic).
    """
    if aht_seconds <= 0:
        raise ValueError("aht_seconds must be > 0")
    if agents <= traffic_erlangs:
        return math.inf
    pw = erlang_c(traffic_erlangs, agents)
    return pw * aht_seconds / (agents - traffic_erlangs)


def required_agents(
    traffic_erlangs: float,
    aht_seconds: float,
    target_service_level: float,
    target_seconds: float,
    max_agents: int = 500,
) -> int:
    """Smallest number of agents that hits the service-level target.

    Queue stability (agents > traffic) is the minimum condition; the
    service-level target decides how far above that you need to go.
    """
    if not 0 < target_service_level < 1:
        raise ValueError("target_service_level must be between 0 and 1")
    if aht_seconds <= 0:
        raise ValueError("aht_seconds must be > 0")
    if traffic_erlangs <= 0:
        return 0
    n = max(1, math.floor(traffic_erlangs) + 1)
    while n <= max_agents:
        if service_level(traffic_erlangs, n, aht_seconds, target_seconds) >= target_service_level:
            return n
        n += 1
    raise ValueError(
        f"Target unreachable with up to {max_agents} agents for "
        f"traffic of {traffic_erlangs:.2f} Erlangs"
    )


def traffic_intensity(contacts: float, aht_seconds: float, interval_seconds: float) -> float:
    """Traffic intensity in Erlangs for one interval."""
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be > 0")
    return contacts * aht_seconds / interval_seconds


def capacity_contacts(agents: int, aht_seconds: float, interval_seconds: float) -> float:
    """Contacts `agents` can handle in the interval (100% occupancy)."""
    if aht_seconds <= 0 or interval_seconds <= 0:
        raise ValueError("aht_seconds and interval_seconds must be > 0")
    return agents * interval_seconds / aht_seconds


def interval_cost(agents: int, hourly_cost: float, interval_seconds: float) -> float:
    """Staffing cost of the interval: agents x hourly cost x fraction of an hour."""
    if hourly_cost < 0:
        raise ValueError("hourly_cost must be >= 0")
    return agents * hourly_cost * (interval_seconds / 3600.0)
