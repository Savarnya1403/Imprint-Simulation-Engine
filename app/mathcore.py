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
    Works with 1D (scalar per node) or 2D (multi-dim belief) arrays.
    """
    deg_safe = np.where(deg == 0, 1.0, deg)
    flow = -L @ beliefs
    if beliefs.ndim == 1:
        flow = flow / deg_safe
    else:
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


# ---------------------------------------------------------------------------
# 7. FOKKER-PLANCK EQUATION  (opinion drift in continuous belief space)
# ---------------------------------------------------------------------------
# Models how the probability density P(x, t) of agents holding belief x
# evolves over time under drift A(x,t) and diffusion D:
#
#   ∂P/∂t = -∂/∂x [ A(x,t) · P ] + (D/2) · ∂²P/∂x²
#
# Discretised on a 1-D grid over [-1, 1].
# ---------------------------------------------------------------------------

def fokker_planck_step(
    P: np.ndarray,
    x_grid: np.ndarray,
    drift_coeffs: np.ndarray,
    diffusion: float = 0.05,
    dt: float = 0.1,
) -> np.ndarray:
    """
    One Euler step of the Fokker-Planck PDE.

    Args:
        P:             Probability density over x_grid. Shape (N,). Will be
                       normalised so it sums to 1.
        x_grid:        Spatial grid of belief values in [-1, 1]. Shape (N,).
        drift_coeffs:  A(x) evaluated at each grid point. Shape (N,).
        diffusion:     Diffusion coefficient D (> 0).
        dt:            Time step size.

    Returns:
        P_new: Updated probability density (normalised).
    """
    dx = x_grid[1] - x_grid[0]
    N  = len(P)

    # Advection flux  F_adv[i] = A[i] * P[i]  (upwind scheme)
    flux = drift_coeffs * P

    dflux_dx      = np.zeros(N)
    dflux_dx[1:-1] = (flux[2:] - flux[:-2]) / (2 * dx)
    dflux_dx[0]   = (flux[1] - flux[0])  / dx
    dflux_dx[-1]  = (flux[-1] - flux[-2]) / dx

    # Diffusion  ∂²P/∂x²  (central differences)
    d2P_dx2        = np.zeros(N)
    d2P_dx2[1:-1]  = (P[2:] - 2 * P[1:-1] + P[:-2]) / (dx ** 2)

    # Forward-Euler update
    P_new = P + dt * (-dflux_dx + 0.5 * diffusion * d2P_dx2)
    P_new = np.maximum(P_new, 0.0)
    total = P_new.sum() * dx
    if total > 1e-12:
        P_new /= total * dx       # re-normalise to density
    return P_new


def fokker_planck_simulate(
    n_agents: int,
    initial_stances: np.ndarray,
    drift_fn,                      # callable(x_grid, t) -> drift array
    diffusion: float = 0.05,
    n_steps: int = 20,
    dt: float = 0.1,
    n_bins: int = 80,
) -> dict:
    """
    Simulate opinion evolution over time using the Fokker-Planck equation.

    Returns dict with:
        x_grid         : belief axis values
        P_history      : (n_steps+1, n_bins) density snapshots
        mean_belief    : (n_steps+1,) mean belief at each step
        std_belief     : (n_steps+1,) std of belief distribution
        bimodality_idx : (n_steps+1,) crude bimodality score (> 0.5 = polarised)
    """
    x_grid = np.linspace(-1.0, 1.0, n_bins)
    dx     = x_grid[1] - x_grid[0]

    # Initialise density from agent stances via histogram
    counts, _ = np.histogram(np.clip(initial_stances, -1, 1), bins=n_bins, range=(-1, 1))
    P = counts.astype(float)
    if P.sum() > 0:
        P = P / (P.sum() * dx)

    P_history     = [P.copy()]
    mean_belief   = [float(np.sum(x_grid * P) * dx)]
    std_belief    = [float(np.sqrt(np.sum(x_grid**2 * P) * dx - mean_belief[-1]**2))]

    def bimodality(p):
        # Hartigan's dip approximation: variance of density × kurtosis proxy
        m2 = np.sum((x_grid - mean_belief[-1])**2 * p) * dx
        m4 = np.sum((x_grid - mean_belief[-1])**4 * p) * dx
        kurt = m4 / (m2**2 + 1e-10) - 3
        return float(min(1.0, max(0.0, -kurt / 4 + 0.5)))

    bimodality_idx = [bimodality(P)]

    for step in range(n_steps):
        t = step * dt
        A = drift_fn(x_grid, t)
        P = fokker_planck_step(P, x_grid, A, diffusion=diffusion, dt=dt)
        P_history.append(P.copy())
        mu = float(np.sum(x_grid * P) * dx)
        mean_belief.append(mu)
        std_belief.append(float(np.sqrt(max(0.0, np.sum(x_grid**2 * P) * dx - mu**2))))
        bimodality_idx.append(bimodality(P))

    return {
        "x_grid": x_grid,
        "P_history": np.array(P_history),
        "mean_belief": np.array(mean_belief),
        "std_belief": np.array(std_belief),
        "bimodality_idx": np.array(bimodality_idx),
        "final_mean": mean_belief[-1],
        "final_std": std_belief[-1],
        "is_polarised": bimodality_idx[-1] > 0.55,
    }


def india_opinion_drift(
    x_grid: np.ndarray,
    t: float,
    social_influence: float = 0.4,
    conformism_strength: float = 0.3,
    external_field: float = 0.0,
) -> np.ndarray:
    """
    India-calibrated drift function A(x, t) for the Fokker-Planck equation.

    Models:
    - Social pull toward mean (conformist drift)
    - External field (government scheme, media campaign, etc.)
    - Resistance in extreme zones (stubbornness)

    Returns drift coefficient at each x in x_grid.
    """
    conformist = -conformism_strength * x_grid         # pull toward 0
    field_term = external_field * np.ones_like(x_grid)
    resistance = -social_influence * np.sign(x_grid) * np.abs(x_grid) ** 2
    decay       = np.exp(-0.5 * t) * 0.1 * np.sin(np.pi * x_grid)

    return conformist + field_term + resistance + decay


# ---------------------------------------------------------------------------
# 8. ISING MODEL  (social phase transitions)
# ---------------------------------------------------------------------------
# Models a population of N agents on a 1-D chain (periodic boundary).
# Each agent σᵢ ∈ {-1, +1}  (against / in favour of adopting product).
# Energy:  E = -J Σ σᵢ σⱼ  -  h Σ σᵢ
# Transitions via Metropolis-Hastings at temperature T.
#
# High T → disordered (opinions all over the place)
# Low T  → ordered (community consensus forms)
# Critical T (India ~ 0.6-0.8) → tipping / phase transition zone
# ---------------------------------------------------------------------------

class IsingOpinionModel:
    """
    1-D Ising model of opinion dynamics in an Indian consumer population.

    Args:
        n:          Number of agents.
        J:          Coupling strength (social influence between neighbours).
                    Typical India values: 0.4 (metro) to 0.8 (village).
        h:          External field (advertising / government push).
        T:          Social temperature (disorder). India range 0.5-1.5.
        rng:        NumPy random generator.
    """
    def __init__(
        self,
        n: int,
        J: float = 0.6,
        h: float = 0.0,
        T: float = 1.0,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.n   = n
        self.J   = J
        self.h   = h
        self.T   = max(T, 1e-6)
        self.rng = rng or np.random.default_rng()
        # Initialise spins randomly
        self.spins = self.rng.choice([-1, 1], size=n).astype(float)

    def energy(self) -> float:
        """Total energy of the current spin configuration."""
        s = self.spins
        pair_sum = np.sum(s * np.roll(s, 1))   # periodic boundary
        return float(-self.J * pair_sum - self.h * np.sum(s))

    def magnetisation(self) -> float:
        """Order parameter m = Σσᵢ / N.  +1 = all adopt, -1 = all reject."""
        return float(np.mean(self.spins))

    def metropolis_step(self, n_flips: int | None = None) -> None:
        """
        Run n_flips Metropolis-Hastings updates.
        Default: flip each agent once on average (n_flips = N).
        """
        n_flips = n_flips or self.n
        for _ in range(n_flips):
            i       = int(self.rng.integers(0, self.n))
            left_i  = (i - 1) % self.n
            right_i = (i + 1) % self.n
            dE      = 2 * self.spins[i] * (
                self.J * (self.spins[left_i] + self.spins[right_i]) + self.h
            )
            if dE < 0 or self.rng.random() < math.exp(-dE / self.T):
                self.spins[i] *= -1

    def anneal(self, T_start: float, T_end: float, steps: int) -> list[float]:
        """
        Simulated annealing: cool social temperature from T_start to T_end.
        Returns magnetisation history (opinion consensus trajectory).
        """
        history = []
        for step in range(steps):
            self.T = T_start + (T_end - T_start) * step / max(steps - 1, 1)
            self.metropolis_step()
            history.append(self.magnetisation())
        return history

    def simulate(self, rounds: int, record_every: int = 1) -> dict:
        """
        Run simulation for `rounds` Metropolis sweeps.

        Returns:
            magnetisation  : list of m per recorded round
            energy         : list of E per recorded round
            final_spins    : array of final spin values
            tipping_round  : first round m crosses 0 from below (None if not)
            consensus_round: first round |m| > 0.8 (None if not)
        """
        mag_hist  = []
        e_hist    = []
        tipping   = None
        consensus = None
        prev_m    = self.magnetisation()

        for r in range(rounds):
            self.metropolis_step()
            if r % record_every == 0:
                m = self.magnetisation()
                e = self.energy()
                mag_hist.append(m)
                e_hist.append(e)
                if tipping is None and prev_m < 0 and m >= 0:
                    tipping = r
                if consensus is None and abs(m) > 0.8:
                    consensus = r
                prev_m = m

        return {
            "magnetisation": mag_hist,
            "energy": e_hist,
            "final_spins": self.spins.copy(),
            "final_magnetisation": mag_hist[-1] if mag_hist else 0.0,
            "tipping_round": tipping,
            "consensus_round": consensus,
            "adoption_fraction": float(np.mean(self.spins > 0)),
        }


def ising_tier_parameters(tier: int) -> dict[str, float]:
    """
    Return India-calibrated Ising parameters for each consumer tier.

    Tier 1 (Metro): high temperature (individualistic), low coupling
    Tier 4 (Rural): low temperature (herd), high coupling (conformism)
    """
    params = {
        1: {"J": 0.35, "T": 1.40, "note": "Metro individualism; weak peer pressure"},
        2: {"J": 0.52, "T": 1.10, "note": "Urban middle; moderate social influence"},
        3: {"J": 0.68, "T": 0.80, "note": "Semi-urban; strong community conformism"},
        4: {"J": 0.82, "T": 0.55, "note": "Rural; near-unanimous herd behaviour"},
    }
    return params.get(tier, params[3])


# ---------------------------------------------------------------------------
# 9. CULTURAL TRANSMISSION  (Boyd & Richerson 1985)
# ---------------------------------------------------------------------------
# Three modes of belief transmission between agents:
#   1. Conformist bias   — copy the majority
#   2. Prestige bias     — copy high-status/successful individuals
#   3. Content bias      — copy beliefs that match existing priors
# ---------------------------------------------------------------------------

def cultural_transmission_weight(
    agent_stance: float,
    model_stance: float,
    model_prestige: float,
    population_majority_stance: float,
    conformism_strength: float = 0.4,
    prestige_strength: float = 0.3,
    content_strength: float = 0.3,
) -> float:
    """
    Compute net transmission weight from model → agent.
    Returns probability that agent updates toward model's belief.

    India defaults: conformism > prestige > content (caste/peer society).
    """
    # Conformist: how close is model to majority?
    conformist_signal = 1.0 - abs(model_stance - population_majority_stance) / 2.0

    # Prestige: direct prestige score (0-1)
    prestige_signal = model_prestige

    # Content: similarity of beliefs (content bias = resistance to change)
    content_signal = 1.0 - abs(agent_stance - model_stance) / 2.0

    weight = (
        conformism_strength * conformist_signal +
        prestige_strength   * prestige_signal   +
        content_strength    * content_signal
    )
    return float(np.clip(weight, 0.0, 1.0))


def cultural_transmission_step(
    stances: np.ndarray,
    prestige: np.ndarray,
    rng: np.random.Generator,
    n_encounters: int = 20,
    conformism_strength: float = 0.4,
    prestige_strength: float = 0.3,
    content_strength: float = 0.3,
    learning_rate: float = 0.15,
) -> np.ndarray:
    """
    One round of cultural transmission across the population.

    Args:
        stances:    Current stance vector in [-1, 1]. Shape (N,).
        prestige:   Prestige score per agent in [0, 1]. Shape (N,).
        rng:        NumPy Generator.
        n_encounters: Random pairwise encounters per step.
        learning_rate: How much the learner moves toward the model.

    Returns:
        Updated stances.
    """
    N = len(stances)
    new_stances = stances.copy()
    majority_stance = float(np.mean(stances))

    learners = rng.integers(0, N, size=n_encounters)
    models   = rng.integers(0, N, size=n_encounters)

    for li, mi in zip(learners, models):
        if li == mi:
            continue
        w = cultural_transmission_weight(
            agent_stance              = stances[li],
            model_stance              = stances[mi],
            model_prestige            = prestige[mi],
            population_majority_stance= majority_stance,
            conformism_strength       = conformism_strength,
            prestige_strength         = prestige_strength,
            content_strength          = content_strength,
        )
        # Learner moves toward model's stance proportional to weight
        new_stances[li] += learning_rate * w * (stances[mi] - stances[li])

    return np.clip(new_stances, -1.0, 1.0)


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
    # New: statistical mechanics
    "fokker_planck_step",
    "fokker_planck_simulate",
    "india_opinion_drift",
    "IsingOpinionModel",
    "ising_tier_parameters",
    "cultural_transmission_weight",
    "cultural_transmission_step",
]
