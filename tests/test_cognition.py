"""Known-answer tests for the cognitive primitives.

These assert analytic identities, not empirical accuracy. If one fails, the
engine's maths changed and the calibration story is no longer valid.
"""
from __future__ import annotations

from app import cognition


def test_prospect_theory_loss_aversion():
    gain = cognition.prospect_value(1.0)
    loss = cognition.prospect_value(-1.0)
    assert gain > 0 > loss
    assert abs(loss / gain + 2.25) < 1e-9


def test_prospect_theory_diminishing_sensitivity():
    d1 = cognition.prospect_value(1.0) - cognition.prospect_value(0.0)
    d2 = cognition.prospect_value(2.0) - cognition.prospect_value(1.0)
    assert d2 < d1


def test_bass_converges_and_is_monotone():
    M, p, q = 1000.0, .03, .40
    seq = [cognition.bass_cumulative(t, M, p, q) for t in range(1, 120)]
    assert all(b >= a - 1e-9 for a, b in zip(seq, seq[1:]))
    assert abs(seq[-1] - M) / M < .02


def test_mere_exposure_saturates():
    vals = [cognition.mere_exposure_bonus(i) for i in range(0, 60)]
    assert vals[0] == 0
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:]))
    assert max(vals) <= .35 + 1e-9


def test_present_bias_is_quasi_hyperbolic():
    assert cognition.quasi_hyperbolic_discount(0) == 1.0
    d1 = cognition.quasi_hyperbolic_discount(1)
    d2 = cognition.quasi_hyperbolic_discount(2)
    assert 0 < d2 < d1 < 1
    assert cognition.present_bias_weight(1.0) > cognition.present_bias_weight(0.0)


def test_granovetter_threshold_direction_and_bounds():
    t_high_conf = cognition.social_threshold(conformity=.9, risk=.2, optimism=.7)
    t_low_conf = cognition.social_threshold(conformity=.1, risk=.8, optimism=.3)
    assert .05 <= t_high_conf < t_low_conf <= .90
    assert cognition.granovetter_gate(.05, .5) < .1
    assert cognition.granovetter_gate(.95, .5) > .9


def test_dual_process_bounds():
    lo = cognition.dual_process_blend(0)
    hi = cognition.dual_process_blend(100)
    assert .2 <= lo < hi <= .92


def test_trust_repair_decays():
    gap = -0.5
    for _ in range(90):
        nxt = cognition.trust_repair_step(gap, recovery_days=30)
        assert 0 > nxt > gap or abs(nxt) < abs(gap)
        gap = nxt
    assert abs(gap) < 0.03
