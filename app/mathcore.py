"""Mathematical core for realistic perception simulation.

Implements the backend mathematics that make agent decisions feel like real
human cognition, while the frontend stays simple.

Key concepts:
  1. Belief dynamics as a continuous-time ODE system (dz/dt = ...)
  2. Temperature-scaled softmax decision making (annealing temperature)
  3. Gradient descent belief updating (cognitive dissonance minimization)
  4. Graph Laplacian diffusion for social contagion (Emergence World style)
  5. TimesFM demand forecast as an exogenous market signal
  6. Neurological attention weights and refractory periods
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# 1. BELIEF DYNAMICS — continuous-time ODE system
# ---------------------------------------------------------------------------

def belief_ode_rhs(
    t: float,
    beliefs: np.ndarray,
    utility: np.ndarray,
    social_field: np.ndarray,
    temperature: float,
    params: dict[str, float],
) -> np.ndarray:
    """Right-hand side of the belief ODE: dz/dt = F(z, t).

    Each agent's belief vector z_i ∈ R^d evolves under:
      - attraction to personal utility gradient
      - social field (peer pressure + market trend)
      - cognitive dissonance (restoring force toward consistency)
      - stochastic neural noise
    """
    n, d = beliefs.shape
    drift = np.zeros_like(beliefs)

    # --- utility pull: beliefs move toward what the agent finds useful ---
    u = utility.reshape(n, 1)
    drift += params.get("utility_alpha", 0.6) * (u - beliefs)

    # --- social field: graph Laplacian diffusion + market trend ---
    drift += params.get("social_beta", 0.35) * social_field

    # --- cognitive dissonance: restore toward internal consistency ---
    # consistency means beliefs should align with each other (no contradiction)
    mean_belief = beliefs.mean(axis=1, keepdims=True)
    dissonance = beliefs - mean_belief
    drift -= params.get("dissonance_gamma", 0.25) * dissonance

    # --- refractory: recently decided agents resist change ---
    refractory = params.get("refractory", np.zeros(n)).reshape(n, 1)
    drift *= 1.0 - refractory

    # --- neural noise (temperature-scaled) ---
    noise_scale = params.get("noise_sigma", 0.08) * temperature
    drift += noise_scale * np.random.randn(n, d)

    return drift


def rk4_step(
    t: float,
    beliefs: np.ndarray,
    dt: float,
    utility: np.ndarray,
    social_field: np.ndarray,
    temperature: float,
    params: dict[str, float],
) -> np.ndarray:
    """Fourth-order Runge-Kutta integration of the belief ODE."""
    k1 = belief_ode_rhs(t, beliefs, utility, social_field, temperature, params)
    k2 = belief_ode_rhs(t + dt / 2, beliefs + dt * k1 / 2, utility, social_field, temperature, params)
    k3 = belief_ode_rhs(t + dt / 2, beliefs + dt * k2 / 2, utility, social_field, temperature, params)
    k4 = belief_ode_rhs(t + dt, beliefs + dt * k3, utility, social_field, temperature, params)
    return beliefs + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)


# ---------------------------------------------------------------------------
# 2. TEMPERATURE-SCALED DECISION MAKING
# ---------------------------------------------------------------------------

def annealed_temperature(
    day: int,
    total_days: int,
    t_start: float = 2.0,
    t_end: float = 0.25,
    schedule: str = "cosine",
) -> float:
    """Anneal temperature from t_start to t_end over the simulation.

    High temperature early = exploratory, noisy decisions (curiosity phase).
    Low temperature later = decisive, habitual decisions (commitment phase).
    """
    if schedule == "cosine":
        frac = min(1.0, day / max(1, total_days))
        return t_end + (t_start - t_end) * 0.5 * (1 + math.cos(math.pi * frac))
    if schedule == "exponential":
        rate = math.log(t_start / t_end) / max(1, total_days)
        return max(t_end, t_start * math.exp(-rate * day))
    return t_end + (t_start - t_end) * (1 - min(1.0, day / max(1, total_days)))


def softmax_choice(
    utilities: np.ndarray,
    temperature: float,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    """Temperature-scaled softmax over utilities.

    P_i = exp(u_i / T) / sum_j exp(u_j / T)
    As T → 0, becomes argmax (deterministic). As T → ∞, becomes uniform.
    """
    t = max(temperature, 1e-6)
    u = utilities / t
    u = u - np.max(u)  # numerical stability
    exp_u = np.exp(u)
    if mask is not None:
        exp_u = exp_u * mask
    s = exp_u.sum()
    if s <= 0:
        return np.ones_like(utilities) / max(1, len(utilities))
    return exp_u / s


# ---------------------------------------------------------------------------
# 3. GRADIENT DESCENT BELIEF UPDATING (cognitive dissonance minimization)
# ---------------------------------------------------------------------------

def cognitive_dissonance_loss(
    beliefs: np.ndarray,
    observed_outcomes: np.ndarray,
    attention_weights: np.ndarray,
) -> tuple[float, np.ndarray]:
    """Loss = weighted squared error between beliefs and observed outcomes.

    Returns (loss, gradient). Agents run gradient descent on this loss to
    update beliefs — this is the "learning" step.
    """
    resid = beliefs - observed_outcomes
    loss = float(np.mean(attention_weights * resid ** 2))
    grad = 2 * attention_weights * resid / max(1, beliefs.size)
    return loss, grad


def gradient_descent_belief_update(
    beliefs: np.ndarray,
    gradient: np.ndarray,
    lr: float,
    momentum: np.ndarray | None = None,
    beta: float = 0.9,
) -> tuple[np.ndarray, np.ndarray]:
    """b ← b − lr * grad + momentum (heavy-ball acceleration)."""
    if momentum is None:
        momentum = np.zeros_like(beliefs)
    momentum = beta * momentum + lr * gradient
    new_beliefs = beliefs - momentum
    return np.clip(new_beliefs, 0.0, 1.0), momentum


# ---------------------------------------------------------------------------
# 4. GRAPH LAPLACIAN DIFFUSION (Emergence World style social contagion)
# ---------------------------------------------------------------------------

def graph_laplacian(
    src: np.ndarray,
    dst: np.ndarray,
    n: int,
    weights: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Build graph Laplacian L = D − A and degree vector."""
    if weights is None:
        weights = np.ones(len(src), dtype=np.float64)
    A = np.zeros((n, n), dtype=np.float64)
    A[src, dst] = weights
    deg = A.sum(axis=1)
    D = np.diag(deg)
    L = D - A
    return L, deg


def laplacian_diffusion(
    beliefs: np.ndarray,
    L: np.ndarray,
    deg: np.ndarray,
    dt: float,
    diffusivity: float = 0.15,
) -> np.ndarray:
    """beliefs ← beliefs + dt * diffusivity * (-L @ beliefs) / deg.

    This is the heat equation on a graph: beliefs diffuse across social ties.
    High-degree nodes diffuse faster (influencers spread beliefs quicker).
    """
    deg_safe = np.where(deg == 0, 1.0, deg)
    flow = -L @ beliefs
    flow = flow / deg_safe.reshape(-1, 1)
    return beliefs + dt * diffusivity * flow


# ---------------------------------------------------------------------------
# 5. TIMESFM DEMAND FORECAST INTEGRATION
# ---------------------------------------------------------------------------

class TimesFMDemandSignal:
    """Wraps TimesFM forecast as an exogenous demand signal for agents.

    Agents observe the forecasted demand curve and update social proof
    accordingly — "everyone is buying this" becomes a self-fulfilling belief.
    """

    def __init__(self, forecast_fn: Any | None = None, horizon: int = 24):
        self.forecast_fn = forecast_fn
        self.horizon = horizon
        self.cached_demand: np.ndarray | None = None
        self.cached_confidence: np.ndarray | None = None

    def load(self, topic_id: str, history_values: list[float]) -> None:
        """Fetch TimesFM forecast for the category's historical series."""
        if self.forecast_fn is None:
            self.cached_demand = np.array(history_values + [history_values[-1]] * self.horizon)
            self.cached_confidence = np.full(len(history_values) + self.horizon, 0.5)
            return
        try:
            res = self.forecast_fn(topic_id=topic_id, horizon=self.horizon, model="auto")
            point = np.asarray(res.get("point", []), dtype=float)
            lo = np.asarray(res.get("p10", point), dtype=float)
            hi = np.asarray(res.get("p90", point), dtype=float)
            hist = np.asarray(history_values, dtype=float)
            self.cached_demand = np.concatenate([hist, point])
            width = np.maximum(hi - lo, 1e-6)
            self.cached_confidence = np.clip(1.0 - width / (np.maximum(hi, 1e-6) + 1e-6), 0, 1)
        except Exception:
            hist = np.asarray(history_values, dtype=float)
            self.cached_demand = np.concatenate([hist, [hist[-1]] * self.horizon])
            self.cached_confidence = np.full(len(hist) + self.horizon, 0.3)

    def market_trend_signal(self, day: int, total_days: int) -> float:
        """Return normalized market trend (−1 to 1) for a given day.

        Positive = demand forecast is rising (social proof tailwind).
        Negative = demand forecast is falling (social proof headwind).
        """
        if self.cached_demand is None or len(self.cached_demand) < 2:
            return 0.0
        idx = min(day, len(self.cached_demand) - 1)
        hist_len = max(1, len(self.cached_demand) - self.horizon)
        # Compare recent forecast to pre-forecast baseline
        pre = float(np.mean(self.cached_demand[max(0, idx - 4):idx]))
        post = float(np.mean(self.cached_demand[idx:idx + self.horizon]))
        if pre == 0:
            return 0.0
        trend = (post - pre) / abs(pre)
        return float(np.clip(trend * 3, -1, 1))


# ---------------------------------------------------------------------------
# 6. NEUROLOGICAL ATTENTION + REFRACTORY
# ---------------------------------------------------------------------------

def attention_weights(
    traits: dict[str, np.ndarray],
    topic: dict[str, Any],
    day: int,
    total_days: int,
) -> np.ndarray:
    """Compute per-agent attention weights for each belief dimension.

    Agents pay more attention to dimensions that match their traits and
    the current life stage (early = price, late = trust/service).
    """
    n = len(next(iter(traits.values())))
    w = np.ones((n, 6), dtype=np.float64)  # [afford, relative, social, trust, risk, status]

    # Price-sensitive agents attend more to affordability early
    price_trait = traits.get("price", np.full(n, 0.5))
    w[:, 0] = 0.6 + 0.8 * price_trait

    # Status-conscious agents attend to status/social late
    status_trait = traits.get("status", np.full(n, 0.5))
    w[:, 5] = 0.5 + 0.6 * status_trait * (day / max(1, total_days))

    # Trust-oriented agents attend to trust
    trust_trait = traits.get("trust_gov", np.full(n, 0.5))
    w[:, 3] = 0.5 + 0.7 * trust_trait

    # Risk-averse agents attend to risk
    risk_trait = traits.get("risk", np.full(n, 0.5))
    w[:, 4] = 0.5 + 0.7 * (1 - risk_trait)

    # Education moderates attention (more rational weighting)
    edu = traits.get("education", np.full(n, 0.5))
    w = w * (0.7 + 0.6 * edu).reshape(-1, 1)

    return np.clip(w, 0.1, 2.0)


def refractory_period(
    adopted: np.ndarray,
    adopt_day: np.ndarray,
    current_day: int,
    window: int = 5,
) -> np.ndarray:
    """Agents who recently adopted/refused resist further belief change."""
    ref = np.zeros(len(adopted), dtype=np.float64)
    recently = (adopt_day > 0) & (current_day - adopt_day <= window)
    ref[recently] = 0.6
    return ref


# ---------------------------------------------------------------------------
# 7. EMERGENT PHASE TRANSITION DETECTION
# ---------------------------------------------------------------------------

def order_parameter(
    adopted: np.ndarray,
    addressable: np.ndarray,
) -> float:
    """Fraction of addressable population that has adopted (0 to 1).

    This is the "magnetization" — near 0 = disordered (no adoption),
    near 1 = ordered (universal adoption within addressable pool).
    """
    denom = max(1, int(addressable.sum()))
    return float(adopted[addressable].sum() / denom)


def susceptibility(
    order_history: list[float],
    window: int = 7,
) -> float:
    """Variance of the order parameter — spikes near phase transitions."""
    if len(order_history) < window:
        return 0.0
    recent = order_history[-window:]
    return float(np.var(recent))


__all__ = [
    "belief_ode_rhs",
    "rk4_step",
    "annealed_temperature",
    "softmax_choice",
    "cognitive_dissonance_loss",
    "gradient_descent_belief_update",
    "graph_laplacian",
    "laplacian_diffusion",
    "TimesFMDemandSignal",
    "attention_weights",
    "refractory_period",
    "order_parameter",
    "susceptibility",
]
