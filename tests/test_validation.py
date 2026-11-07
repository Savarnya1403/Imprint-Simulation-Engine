"""Validation and sensitivity: the checks that are allowed to fail."""
from __future__ import annotations

from app import sensitivity, validation


def test_known_answer_battery_is_green():
    result = validation.known_answer_tests()
    failed = [c["id"] for c in result["checks"] if not c["ok"]]
    assert failed == []
    assert result["score"] == 1.0


def test_backtest_is_labelled_and_complete():
    bt = validation.real_series_backtest()
    assert bt["n_topics"] >= 10
    assert bt["median_mase"] is not None
    assert bt["verdict"]
    assert "not causal" in bt["note"] or "drift" in bt["note"]
    for row in bt["topics"]:
        assert row["mase"] is None or row["mase"] > 0
        assert row["vs_drift"] is None or row["vs_drift"] > 0


def test_battery_reports_limits():
    out = validation.battery(deep=False)
    assert out["summary"]["known_answer_score"] == 1.0
    assert len(out["limits"]) >= 3
    assert "held_out" not in out


def test_sensitivity_recovers_known_shares():
    rec = sensitivity.synthetic_recovery(n_base=16)
    assert rec["ok"], rec
    assert rec["estimated"]["x2"] < 0.15


def test_uncertainty_uses_latin_hypercube_bounds():
    from app import calibration, uncertainty

    draws = uncertainty._lhs_draws(8, __import__("numpy").random.default_rng(0))
    assert len(draws) == 8
    for d in draws:
        assert set(d) == set(calibration.SPECS)
        for k, v in d.items():
            lo, hi, _ = calibration.SPECS[k]
            assert lo <= v <= hi
