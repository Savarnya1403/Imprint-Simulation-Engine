"""Forecast reasoning invariants.

These tests do not assert that the forecast is accurate. They assert that the
reasoning layer is well formed: ordered quantiles, non-negative paths for
non-negative series, a deterministic result, a foundation-first default that
does not silently move the point path, and a labelled fallback when history is
too thin.
"""
from __future__ import annotations

import numpy as np

from app import forecast, forecast_reasoning


def _series(n: int = 48, start: float = 10.0, slope: float = 0.08) -> np.ndarray:
    return start + slope * np.arange(n, dtype=float)


def test_reason_quantiles_are_ordered_and_finite():
    y = _series()
    r = forecast_reasoning.reason(y, 8)
    assert r["available"] is True
    assert len(r["point"]) == 8
    for step in range(8):
        vals = [r["quantiles"][k][step] for k in
                ("p10", "p20", "p30", "p40", "p50", "p60", "p70", "p80", "p90")]
        assert vals == sorted(vals), vals
        assert all(np.isfinite(v) for v in vals)
    assert r["p10"] == r["quantiles"]["p10"]
    assert r["p90"] == r["quantiles"]["p90"]


def test_reason_is_deterministic():
    y = _series()
    a = forecast_reasoning.reason(y, 6, label="synthetic")
    b = forecast_reasoning.reason(y, 6, label="synthetic")
    assert a == b


def test_foundation_first_keeps_the_point_path_when_no_rule_fires():
    y = _series()
    foundation = y[-1] + 0.08 * np.arange(1, 7, dtype=float)
    r = forecast_reasoning.reason(y, 6, foundation_point=foundation)
    assert r["mode"] == "foundation_first_with_critique"
    assert r["foundation_weight"] == 1.0
    # No plausibility, non-negativity or band rule should fire on a clean
    # linear series, so the audited point path is the foundation path.
    assert np.allclose(r["point"], foundation, atol=1e-9)


def test_blend_weight_moves_the_path_only_when_asked():
    y = _series()
    foundation = y[-1] + 0.08 * np.arange(1, 7, dtype=float)
    blended = forecast_reasoning.reason(y, 6, foundation_point=foundation, blend_weight=0.25)
    assert blended["mode"] == "foundation_ensemble_blend"
    assert 0.0 < blended["foundation_weight"] < 1.0
    assert not np.allclose(blended["point"], foundation, atol=1e-9)


def test_non_negative_series_never_goes_negative():
    y = np.maximum(0.0, np.sin(np.arange(36, dtype=float) / 4.0) + 1.0)
    r = forecast_reasoning.reason(y, 12, foundation_point=np.zeros(12))
    assert min(r["point"]) >= 0.0
    assert min(r["p10"]) >= 0.0


def test_short_history_is_labelled_not_faked():
    r = forecast_reasoning.reason([3.0, 3.2], 6)
    assert r["available"] is False
    assert r["confidence"] <= 0.2
    assert len(r["point"]) == 6


def test_fast_ensemble_is_finite_and_non_negative():
    y = _series()
    p = forecast_reasoning.reasoned_fast_forecast(y, 9)
    assert len(p) == 9
    assert np.all(np.isfinite(p))
    assert np.all(p >= 0)


def test_forecast_topic_carries_raw_and_audited_paths():
    out = forecast.forecast_topic("ev-car", 6)
    assert out["forecast"]["point"]
    assert "test_time_augmentation" in out
    assert isinstance(out["test_time_augmentation"].get("views"), list)
    reasoned = out["reasoned"]
    assert reasoned.get("available") is True
    assert out["reasoned_forecast"]["point"] == reasoned["point"]
    assert len(out["reasoned_forecast"]["point"]) == len(out["forecast"]["point"]) == 6
