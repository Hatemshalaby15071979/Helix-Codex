"""The CX risk label must point in the same direction as the KPIs.

``weighted_score`` is a goodness score, but ``classify_risk_level`` compared it
directly to risk bands whose 0.8 threshold means *critical*, and both population
aggregators averaged the goodness score into a field named ``overall_risk_score``.
A customer with better KPIs therefore received a worse label and a worse
population score. Measured before the fix on tenant-shaped input: weighted 0.998
-> "critical", weighted 0.699 -> "high".
"""

from __future__ import annotations

from engines.cx.src.risk_scorer import create_risk_scorer

HEALTHY = {"csat": 0.98, "sla": 0.99, "fcr": 0.97, "aht": 0.01}
FAILING = {"csat": 0.15, "sla": 0.20, "fcr": 0.10, "aht": 0.95}


def _population(kpis, count=5):
    return [{"customer_id": str(index), **kpis} for index in range(count)]


def test_perfect_kpis_are_low_risk():
    result = create_risk_scorer().score_customers(_population(HEALTHY))
    assert result.customer_risks[0]["risk_level"] == "low"
    assert result.customer_risks[0]["risk_score"] < 0.1


def test_failing_kpis_are_critical():
    result = create_risk_scorer().score_customers(_population(FAILING))
    assert result.customer_risks[0]["risk_level"] == "critical"
    assert result.customer_risks[0]["risk_score"] > 0.5


def test_population_risk_is_not_inverted():
    healthy = create_risk_scorer().score_customers(_population(HEALTHY))
    failing = create_risk_scorer().score_customers(_population(FAILING))
    assert healthy.overall_risk_score < failing.overall_risk_score
    assert healthy.risk_distribution.get("critical", 0) == 0
    assert failing.risk_distribution.get("critical", 0) == 5