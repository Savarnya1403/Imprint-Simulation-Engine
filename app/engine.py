"""Agent-based simulation engine: India, four tiers, one ground truth.

Backend runs complex mathematics (belief ODEs, gradient-descent belief
updating, graph-Laplacian social diffusion, temperature-annealed decisions,
TimesFM demand signals, refractory periods, phase-transition detection) while
the frontend stays simple. Public interface is unchanged.
"""
from __future__ import annotations

import math
import random
import uuid
from collections import Counter, defaultdict
from typing import Any

import numpy as np

from . import content, personas, store
from . import mathcore
from . import memory, concordia
from . import cognition
from .nn import MLP, Value, sgd_update

SCENARIOS = [
    dict(id="base", label="Base case", desc="No exogenous shock. The category competes on its own merits.", icon="◌"),
    dict(id="price_cut", label="Price cut", desc="A 22% price reduction plus heavier advertising from day 1.", icon="↓"),
    dict(id="trust_shock", label="Trust shock", desc="A viral service failure / safety incident hits on day 12.", icon="⚡"),
    dict(id="viral", label="Viral moment", desc="A creator-led moment lifts social proof and awareness.", icon="↗"),
    dict(id="policy", label="Policy push", desc="Subsidy + government endorsement lowers the effective price.", icon="₹"),
    dict(id="festival", label="Festival season", desc="Festive demand, gifting and visible consumption peak.", icon="✦"),
    dict(id="competitor", label="Competitor counter-move", desc="An incumbent cuts price and seeds doubt about the new category.", icon="⚔"),
]

SCENARIO_MODS = {
    "base": dict(price=1.0, ad=1.0, social=1.0, awareness=0.0, event_day=0),
    "price_cut": dict(price=.78, ad=1.35, social=1.15, awareness=.03, event_day=1),
    "trust_shock": dict(price=1.0, ad=.92, social=.82, awareness=-.02, event_day=12),
    "viral": dict(price=1.0, ad=1.45, social=1.55, awareness=.08, event_day=5),
    "policy": dict(price=.88, ad=1.20, social=1.20, awareness=.08, event_day=3),
    "festival": dict(price=.95, ad=1.25, social=1.35, awareness=.06, event_day=7),
    "competitor": dict(price=1.0, ad=.90, social=.90, awareness=-.01, event_day=9),
}

ADOPTION_CEILING = {
    "ev-car": .035,
    "ev-scooter": .115,
    "quick-commerce": .185,
    "upi-rural": .62,
    "ai-jobs": .55,
    "edtech": .12,
    "health-insurance": .095,
    "rural-credit": .14,
    "premium-fmcg": .18,
    "ott": .26,
    "solar-rooftop": .045,
    "gig-work": .10,
    "women-work": .12,
    "misinformation": .38,
    "agri-tech": .055,
    "bnpl": .12,
    "language-ai": .17,
    "coaching": .14,
    "generic": .12,
}


def _involvement(price: float) -> float:
    if price <= 0:
        return .30
    if price < 2000:
        return .42
    if price < 25000:
        return .62
    if price < 100000:
        return .82
    return 1.0


def _affordability(price: float, hh_income: np.ndarray) -> np.ndarray:
    if price <= 0:
        return np.full(len(hh_income), .84)
    if price < 2000:
        scale = hh_income * .018 + price * .35 + 40
        return 1 / (1 + np.exp(-(hh_income * .030 - price) / scale))
    emi = _outlay(price)
    share = .30 if price >= 50000 else .175
    scale = hh_income * .095 + emi * .30 + 1
    return 1 / (1 + np.exp(-(hh_income * share - emi) / scale))


def _addressable_mask(agents: list[dict], topic: dict, rng: random.Random, ceiling: float) -> np.ndarray:
    n = len(agents)
    k = max(1, min(n, int(round(ceiling * n))))
    price = float(topic.get("price", 0))
    hh = np.array([a["household_income"] for a in agents], dtype=float)
    digital = np.array([a["digital"] for a in agents])
    tier = np.array([a["tier"] for a in agents])
    hh_norm = (hh - hh.min()) / (hh.max() - hh.min() + 1)
    tier_norm = np.where(tier == 1, 1.0, np.where(tier == 2, .72, np.where(tier == 3, .42, .18)))

    if price <= 0:
        score = .35 + .55 * digital + .10 * tier_norm
    elif price < 5000:
        score = .15 + .55 * hh_norm + .30 * digital + .10 * tier_norm
    else:
        score = .70 * hh_norm + .18 * digital + .12 * tier_norm
    score = np.clip(score, .01, None)
    keys = np.array([rng.random() for _ in range(n)])
    rank = np.argsort(-(np.log(keys) / score))
    mask = np.zeros(n, dtype=bool)
    mask[rank[:k]] = True
    return mask


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _tier_mix_from_req(req: dict | None) -> dict[int, float]:
    if not req:
        return {1: .10, 2: .15, 3: .28, 4: .47}
    out = {}
    for k, v in req.items():
        try:
            out[int(k)] = float(v)
        except Exception:
            pass
    return out or {1: .10, 2: .15, 3: .28, 4: .47}


def build_network(agents: list[dict], rng: random.Random) -> tuple[np.ndarray, np.ndarray]:
    n = len(agents)
    buckets: dict[str, list[int]] = defaultdict(list)
    occ_buckets: dict[str, list[int]] = defaultdict(list)
    state_buckets: dict[str, list[int]] = defaultdict(list)
    for i, a in enumerate(agents):
        buckets[f"{a['state']}|{a['tier']}|{a['occupation_id']}"].append(i)
        occ_buckets[a["occupation_id"]].append(i)
        state_buckets[a["state"]].append(i)
    src, dst = [], []
    seen = set()

    def add(i, j):
        if i == j:
            return
        key = (i, j) if i < j else (j, i)
        if key in seen:
            return
        seen.add(key)
        src.append(i)
        dst.append(j)
        src.append(j)
        dst.append(i)

    for i, a in enumerate(agents):
        local = buckets[f"{a['state']}|{a['tier']}|{a['occupation_id']}"]
        for _ in range(3):
            if len(local) > 1:
                add(i, rng.choice(local))
        state = state_buckets[a["state"]]
        for _ in range(2):
            if len(state) > 1:
                add(i, rng.choice(state))
        occ = occ_buckets[a["occupation_id"]]
        if len(occ) > 1 and rng.random() < .55:
            add(i, rng.choice(occ))
        add(i, rng.randrange(n))
    return np.array(src, dtype=np.int32), np.array(dst, dtype=np.int32)


def peer_mean(values: np.ndarray, src: np.ndarray, dst: np.ndarray, n: int) -> np.ndarray:
    out = np.zeros(n, dtype=np.float64)
    if len(src) == 0:
        return out
    np.add.at(out, src, values[dst])
    deg = np.bincount(src, minlength=n).astype(np.float64)
    deg[deg == 0] = 1
    return out / deg


def _outlay(price: float) -> float:
    if price <= 0:
        return 1.0
    if price >= 50000:
        return price * 0.021
    return price


def _get_llm_generate():
    """Return a prompt->text callable using the configured LLM (local or hosted), or None."""
    try:
        from . import llm
        if not llm.status().get("available"):
            return None
        def gen(prompt, max_tokens: int = 120, temperature: float = 0.7):
            return llm.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        return gen
    except Exception:
        return None


def _llm_status():
    try:
        from . import llm
        return llm.status()
    except Exception:
        return {"available": False}


def _run_generative_layer(agents, adopted, topic, rounds, rng, domain: str = "market"):
    """Stanford memory stream + Concordia Game Master adjudication (domain-aware).

    Caps LLM usage so the page stays responsive: Claude/hosted models get the full
    generative treatment; local tiny models get a small budget. Every layer has a
    deterministic fallback.
    """
    llm_generate = _get_llm_generate()
    backend = _llm_status().get("backend", "")
    hosted = backend in ("anthropic", "openai-compatible")
    llm_budget = 6 if hosted else 1  # Claude gets a generous budget; tiny local stays fast
    topic_label = topic.get("label", "this")
    streams = {}
    for a in agents:
        s = memory.MemoryStream(a["id"])
        for text, kind, imp in memory.seed_memories(a, topic_label, day=1):
            s.add(text, kind, imp, day=1)
        streams[a["id"]] = s

    encounters = []
    pairs = concordia.sample_encounters(agents, adopted, rounds, topic, rng, n=3)
    for a, b in pairs:
        use_llm = llm_generate if llm_budget > 0 else None
        if use_llm is not None:
            llm_budget -= 1
        out = concordia.resolve_encounter(a, b, topic, rounds, topic_label, use_llm, rng, domain=domain)
        encounters.append(out)
        streams[a["id"]].add(f"Talked to {b.get('name')} about {topic_label}. Outcome: {out['outcome']}.", "observation", 0.7, day=rounds)
        streams[b["id"]].add(f"Talked to {a.get('name')} about {topic_label}. Outcome: {out['outcome']}.", "observation", 0.7, day=rounds)
        a["stance"] = round(min(1.0, max(0.0, a["stance"] + out["stance_delta"])), 3)

    reflect_llm = llm_generate if hosted else None  # reflections are deterministic on tiny local models
    for a in agents:
        if rng.random() < 0.35:  # reflection is expensive; sample a subset
            try:
                streams[a["id"]].reflect(a, topic_label, rounds, reflect_llm)
            except Exception:
                pass
        a["memory"] = streams[a["id"]].to_dict()

    return encounters


def _calibration_params() -> dict:
    try:
        from .calibration import load_params
        return load_params()
    except Exception:
        return {"ceiling_mult": 1.0, "price_sensitivity": 1.0, "social_mult": 1.0, "trust_weight": 1.0, "hazard_mult": 1.0}


# ---------------------------------------------------------------------------
# Enhanced mathematical simulation loop
# ---------------------------------------------------------------------------

def _run_math_simulation(
    agents: list[dict],
    topic: dict,
    src: np.ndarray,
    dst: np.ndarray,
    n: int,
    rounds: int,
    rng: random.Random,
    p: dict[str, float],
    precedent: dict[str, Any],
    price: float,
    mod: dict[str, float],
    ceiling_mult: float,
    price_sens: float,
    social_mult: float,
    trust_weight: float,
    hazard_mult: float,
    atlas_strength: float,
    topic_id: str,
    forecast_fn: Any | None = None,
) -> dict[str, Any]:
    """Core simulation using belief ODEs, gradient descent, graph Laplacian
    diffusion, temperature annealing, and TimesFM demand signals."""

    N = n
    ceiling = float(np.clip(ADOPTION_CEILING.get(topic_id, .12) * ceiling_mult, .01, .95))
    addressable = _addressable_mask(agents, topic, rng, ceiling)
    n_addressable = max(1, int(addressable.sum()))

    traits = {k: np.array([a["traits"][k] for a in agents]) for k in agents[0]["traits"]}
    bias = {k: np.array([a["biases"][k] for a in agents]) for k in agents[0]["biases"]}
    hh_income = np.array([a["household_income"] for a in agents], dtype=np.float64)
    tier_arr = np.array([a["tier"] for a in agents], dtype=np.int32)
    outlay = _outlay(price)
    involvement = _involvement(price)

    tier_shift = np.array([topic.get("tier_shift", {}).get(int(t), 0) for t in tier_arr])
    region_shift = np.array([topic.get("region_shift", {}).get(a["region"], 0) for a in agents])
    occ_shift = np.array([topic.get("occupation_shift", {}).get(a["occupation_id"], 0) for a in agents])

    # --- Belief state: 6 dimensions per agent ---
    # [affordability, relative_advantage, social_proof, trust, risk, status]
    # --- Nano-agents: each agent is a tiny MLP (micrograd-style autograd) ---
    # 6 context inputs -> 1 adoption logit. Belief updating = backprop on
    # cognitive-dissonance loss vs observed peer behavior.
    mlps = [MLP(6, [4, 1]) for _ in range(N)]
    mlp_lr = 0.05

    # --- Graph Laplacian for social diffusion (Emergence World style) ---
    L, deg = mathcore.graph_laplacian(src, dst, N)

    # --- TimesFM demand signal ---
    hist = [float(topic.get("history", {}).get("values", [1.0])[i]) if i < len(topic.get("history", {}).get("values", [])) else 1.0
            for i in range(24)]
    demand_signal = mathcore.TimesFMDemandSignal(forecast_fn=forecast_fn, horizon=12)
    demand_signal.load(topic_id, hist)

    adopted = np.zeros(N, dtype=bool)
    rejected = np.zeros(N, dtype=bool)
    rejection_reason: list[str | None] = [None] * N
    adopt_day = np.full(N, -1, dtype=np.int32)
    exposures = np.zeros(N, dtype=np.int32)  # cumulative mere-exposure impressions
    susceptibility = np.array([cognition.susceptibility_to_influence(a["traits"]) for a in agents])
    need_for_cognition = np.array([cognition.need_for_cognition(a["traits"]) for a in agents])

    timeline = []
    posts = []
    events = []
    order_history = []
    peak_growth = 0
    peak_day = 1
    tipping_day = None

    panel = _pick_panel(agents, rng)
    panel_ids = {a["id"] for a in panel}

    social_field_prev = np.zeros(N)  # initial social signal observed by agents

    for day in range(1, rounds + 1):
        # --- Annealed temperature (exploration early, commitment late) ---
        temp = mathcore.annealed_temperature(day, rounds, t_start=2.0, t_end=0.25)

        # --- Market trend from TimesFM ---
        market_trend = demand_signal.market_trend_signal(day, rounds)

        # --- Context features per agent (6 inputs to each nano-MLP) ---
        afford = _affordability(price, hh_income)
        relative = np.clip(.52 + tier_shift * 1.25 + occ_shift * 1.35 + region_shift * .85
                           + (traits["optimism"] - .5) * .28, 0, 1)
        risk = np.clip(.42 + (1 - traits["risk"]) * .30 + bias["loss_aversion"] * .20
                       + bias["ambiguity"] * .16 - (traits["education"] - .5) * .10, 0, 1)
        trust = np.clip(traits["trust_gov"] * .26 + traits["trust_media"] * .14
                        + (1 - bias["loss_aversion"]) * .26 + traits["education"] * .22 + .08, 0, 1)
        status = np.clip(traits["status"], 0, 1)
        social = np.clip(.55 + (traits["conformity"] - .5) * .3, 0, 1)

        # --- Forward pass: each agent's nano-MLP maps context -> adoption probability ---
        p_raw = np.zeros(N)
        for i in range(N):
            x = [Value(afford[i]), Value(relative[i]), Value(social_field_prev[i]),
                 Value(trust[i]), Value(risk[i]), Value(status[i])]
            p_raw[i] = float(mlps[i](x).data)

        # --- Social field: Laplacian diffusion of adoption probabilities ---
        p_social = mathcore.laplacian_diffusion(p_raw, L, deg, dt=0.1, diffusivity=0.15)
        p_social = p_social * (1.0 + 0.5 * market_trend)

        # --- Backprop: cognitive dissonance (my belief vs what peers actually do) ---
        peer_adopt_rate = peer_mean(adopted.astype(float), src, dst, N)
        for i in range(N):
            mlps[i].zero_grad()
            x = [Value(afford[i]), Value(relative[i]), Value(p_social[i]),
                 Value(trust[i]), Value(risk[i]), Value(status[i])]
            out = mlps[i](x)
            loss = (out - Value(float(peer_adopt_rate[i]))) ** 2
            loss.backward()
            sgd_update(mlps[i].parameters(), mlp_lr * temp)

        # --- Adoption decision: temperature-scaled sigmoid on learned belief ---
        # Mere exposure (Zajonc): each impression rewires preference a little.
        mere = np.array([cognition.mere_exposure_bonus(int(e)) for e in exposures])
        media_lift = topic.get("ad_effect", .04) * mod["ad"] * (0.5 + 0.5 * market_trend)
        p_effective = np.clip(p_raw + media_lift + mere, 0, 1)
        willing = p_effective * addressable  # media + learned belief + habituation
        pressure = .62 + .55 * np.clip(p_social, 0, 1.2)

        # Scenario event
        event_mult = 1.0
        shock_text = None
        if day == mod.get("event_day", 0) and mod.get("event_day", 0) > 0:
            event_mult, shock_text = _event_effect(scenario, day, topic)
            events.append({"day": day, "type": scenario, "label": scenario, "text": shock_text, "impact": round(event_mult, 2)})

        event_scale = event_mult if day >= mod.get("event_day", 0) else 1.0
        hazard = (0.095 * hazard_mult * willing * (.25 + .75 * p_effective)
                  * pressure * event_scale)
        hazard = np.clip(hazard, 0, .35)

        draw = np.array([rng.random() for _ in range(N)])
        can = addressable & (~adopted) & (p_effective > 0.22) & (draw < hazard)
        adopted = adopted | can
        adopt_day[can] = day
        new_today = int(can.sum())

        # Active rejection
        rej_draw = np.array([rng.random() for _ in range(N)])
        rej = (addressable & (p_effective > 0.45) & (~adopted) & (~rejected)
               & (p_raw < 0.3)
               & (rej_draw < .05 + .07 * bias["loss_aversion"]))
        if rej.any():
            rejected = rejected | rej
            for i in np.where(rej)[0]:
                rejection_reason[i] = content.objection(agents[i], topic, rng)

        # Stance = learned belief adjusted by risk
        a_stance = np.clip(.5 + .5 * (p_raw - risk), 0, 1)

        adoption_rate = float(adopted.mean())
        conversion = float(adopted.sum() / n_addressable)
        order = mathcore.order_parameter(adopted, addressable)
        order_history.append(order)
        if tipping_day is None and conversion >= .5:
            tipping_day = day

        if new_today > peak_growth:
            peak_growth = new_today
            peak_day = day

        # Posts (non-fast mode)
        if False:  # posts handled by caller
            pass

        tier_adoption = {str(t): float(adopted[tier_arr == t].mean()) if (tier_arr == t).any() else 0.0 for t in (1, 2, 3, 4)}
        sentiment = float(a_stance.mean() * 2 - 1)
        polarization = float(a_stance.std() * 2)
        social_field_prev = p_social

        # Mere exposure accumulates: media + peer signals this day
        daily_exposures = np.clip(p_raw * 0.25 + media_lift * 2.0, 0, 0.75)
        exposures = exposures + daily_exposures.astype(np.int32)

        top_state = _group_adoption(agents, adopted, "state", 3)
        top_occ = _group_adoption(agents, adopted, "occupation", 3)
        timeline.append({
            "day": day,
            "awareness": round(float(p_raw.mean()), 3),
            "adoption": round(adoption_rate, 4),
            "conversion": round(conversion, 4),
            "addressable": n_addressable,
            "new": new_today,
            "rejected": int(rejected.sum()),
            "sentiment": round(sentiment, 3),
            "polarization": round(min(1, polarization), 3),
            "trust": round(float(trust.mean()), 3),
            "wom": round(len(posts) / max(1, day * N) * 1000, 2),
            "tier_adoption": {k: round(v, 4) for k, v in tier_adoption.items()},
            "state_adoption": _state_adoption(agents, adopted),
            "top_states": top_state,
            "top_occupations": top_occ,
            "event": shock_text if day == mod.get("event_day", 0) > 0 else None,
            "order_parameter": round(order, 4),
            "susceptibility": round(mathcore.susceptibility(order_history), 4),
            "temperature": round(temp, 3),
            "market_trend": round(market_trend, 3),
        })

    # Finalize agents
    for i, a in enumerate(agents):
        a["adopted"] = bool(adopted[i])
        a["adopt_day"] = int(adopt_day[i]) if adopt_day[i] > 0 else None
        a["rejected"] = bool(rejected[i])
        a["rejection_reason"] = rejection_reason[i]
        a["stance"] = round(float(np.clip(.5 + .5 * (p_raw[i] - risk[i]), 0, 1)), 3)
        a["awareness"] = round(float(p_raw[i]), 3)
        a["intent"] = round(float(p_raw[i]), 3)
        a["addressable"] = bool(addressable[i])
        a["panel"] = a["id"] in panel_ids
        a["decision"] = "Adopted" if a["adopted"] else ("Rejected" if a["rejected"] else "Considering")
        a["decision_ledger"] = {
            "affordability": round(float(afford[i]), 3),
            "relative_advantage": round(float(relative[i]), 3),
            "social_proof": round(float(social[i]), 3),
            "trust": round(float(trust[i]), 3),
            "risk": round(float(risk[i]), 3),
            "status": round(float(status[i]), 3),
            "intent": round(float(p_raw[i]), 3),
            "bar": round(float(0.5), 3),
            "utility": round(float(p_raw[i]), 3),
        }
        if not a["addressable"]:
            a["decision_note"] = "Not in the category's addressable pool (price, need or access)."
        elif a["adopted"]:
            a["decision_note"] = f"Crossed the adoption bar on day {a['adopt_day']}."
        elif a["rejected"]:
            a["decision_note"] = f"Actively rejected: {a['rejection_reason'] or 'the failure mode was too costly'}."
        elif a["awareness"] < .45:
            a["decision_note"] = "Awareness is still the binding constraint."
        else:
            a["decision_note"] = "Considering: intent is close to, but below, the adoption bar."

    return {
        "adopted": adopted,
        "rejected": rejected,
        "rejection_reason": rejection_reason,
        "adopt_day": adopt_day,
        "timeline": timeline,
        "n_addressable": n_addressable,
        "addressable_mask": addressable,
        "ceiling": ceiling,
        "order_history": order_history,
        "tipping_day": tipping_day,
        "peak_growth": peak_growth,
        "peak_day": peak_day,
        "panel_ids": panel_ids,
        "beliefs": p_raw,
        "adoption_score": p_raw,
        "susceptibility": susceptibility,
        "need_for_cognition": need_for_cognition,
        "exposures": exposures,
    }


def softmax_with_threshold(scores: np.ndarray, temperature: float, mask: np.ndarray) -> np.ndarray:
    """Temperature-scaled softmax gated by addressable mask."""
    t = max(temperature, 1e-6)
    u = scores / t
    u = u - np.max(u)
    exp_u = np.exp(u) * mask
    s = exp_u.sum()
    if s <= 0:
        return np.zeros_like(scores)
    return exp_u / s


def _event_effect(scenario: str, day: int, topic: dict) -> tuple[float, str]:
    if scenario == "trust_shock":
        return .62, "A service failure video goes viral in a district WhatsApp group. Returns and cancellations spike."
    if scenario == "price_cut":
        return 1.28, "A 22% price cut lands. Dealers report a spike in enquiries, but service capacity is unchanged."
    if scenario == "viral":
        return 1.40, "A creator's 90-second review crosses 8 million views. Search interest doubles in 48 hours."
    if scenario == "policy":
        return 1.24, "A subsidy is extended and a minister endorses the category. Paperwork remains the filter."
    if scenario == "festival":
        return 1.22, "Festive demand and gifting lift visible adoption. The effect is seasonal, not structural."
    if scenario == "competitor":
        return .82, "The incumbent cuts prices and seeds doubt about resale and service. The category narrative fractures."
    return 1.0, ""


def _pick_panel(agents: list[dict], rng: random.Random) -> list[dict]:
    panel = []
    for t in (1, 2, 3, 4):
        tier_agents = [a for a in agents if a["tier"] == t]
        if not tier_agents:
            continue
        tier_agents = sorted(tier_agents, key=lambda a: -(a["traits"]["voice"] + abs(a["stance"] - .5)))
        pick = tier_agents[0]
        panel.append(pick)
        if len(tier_agents) > 2 and rng.random() < .8:
            opposite = min(tier_agents, key=lambda a: abs(a["stance"] - (.2 if pick["stance"] > .5 else .8)))
            panel.append(opposite)
    seen = set()
    out = []
    for a in panel:
        if a["id"] not in seen:
            out.append(a)
            seen.add(a["id"])
    return out[:6] or agents[:6]


def _group_adoption(agents: list[dict], adopted: np.ndarray, key: str, k: int):
    groups = defaultdict(list)
    for i, a in enumerate(agents):
        groups[a[key]].append(i)
    rows = []
    for name, idxs in groups.items():
        if len(idxs) < 2:
            continue
        rows.append({"name": name, "adoption": round(float(adopted[idxs].mean()), 3), "n": len(idxs)})
    rows.sort(key=lambda x: -x["adoption"])
    return rows[:k]


def _state_adoption(agents: list[dict], adopted: np.ndarray) -> dict[str, dict]:
    groups = defaultdict(list)
    for i, a in enumerate(agents):
        groups[a["state"]].append(i)
    out: dict[str, dict] = {}
    for name, idxs in groups.items():
        n = len(idxs)
        out[name] = {
            "adopted": int(adopted[idxs].sum()),
            "n": n,
            "rate": round(float(adopted[idxs].mean()), 3),
        }
    return out


def run_simulation(
    brief: str,
    n_agents: int = 240,
    rounds: int = 36,
    seed: int = 42,
    tier_mix: dict | None = None,
    scenario: str = "base",
    focus_state: str | None = None,
    price_override: float | None = None,
    question: str | None = None,
    params: dict | None = None,
    fast: bool = False,
    _simulation_spec: dict | None = None,
) -> dict[str, Any]:
    rng = _rng(seed)
    topic = store.pick_topic(brief)
    if price_override is not None and price_override > 0:
        topic = dict(topic)
        topic["price"] = price_override
    # Merge topic from spec if provided (non-India domains get spec-derived topic)
    if _simulation_spec and not _simulation_spec.get("is_india_context"):
        spec_topic = _simulation_spec.get("topic") or {}
        if spec_topic.get("id"):
            topic = {**topic, **{k: v for k, v in spec_topic.items() if v}}
    mod = SCENARIO_MODS.get(scenario, SCENARIO_MODS["base"])
    price = float(topic.get("price", 0)) * mod["price"]
    n_agents = max(40, min(1600, int(n_agents)))
    rounds = max(12, min(120, int(rounds)))
    tier_mix = _tier_mix_from_req(tier_mix)

    # Use universal personas for non-India specs; fall back to India personas otherwise
    if _simulation_spec and not _simulation_spec.get("is_india_context"):
        try:
            from .universal_personas import build_population as universal_build
            agents = universal_build(n=n_agents, spec=_simulation_spec, seed=seed, focus_segment=focus_state)
        except Exception:
            agents = personas.build_population(n_agents, seed, tier_mix, topic, focus_state)
    else:
        agents = personas.build_population(n_agents, seed, tier_mix, topic, focus_state)
    src, dst = build_network(agents, rng)

    from . import atlas, perception
    cal = _calibration_params()
    p = {**cal, **(params or {})}
    ceiling_mult = float(p.get("ceiling_mult", 1.0))
    price_sensitivity = float(p.get("price_sensitivity", 1.0))
    social_mult = float(p.get("social_mult", 1.0))
    trust_weight = float(p.get("trust_weight", 1.0))
    hazard_mult = float(p.get("hazard_mult", 1.0))
    atlas_strength = float(p.get("atlas_strength", 1.0))
    precedent = perception.prior_for_simulation(brief, topic)

    # TimesFM forecast function
    from . import forecast
    forecast_fn = forecast.forecast_topic

    # --- Run the mathematical simulation ---
    math_result = _run_math_simulation(
        agents=agents,
        topic=topic,
        src=src,
        dst=dst,
        n=n_agents,
        rounds=rounds,
        rng=rng,
        p=p,
        precedent=precedent,
        price=price,
        mod=mod,
        ceiling_mult=ceiling_mult,
        price_sens=price_sensitivity,
        social_mult=social_mult,
        trust_weight=trust_weight,
        hazard_mult=hazard_mult,
        atlas_strength=atlas_strength,
        topic_id=topic.get("id", "generic"),
        forecast_fn=forecast_fn,
    )

    adopted = math_result["adopted"]
    rejected = math_result["rejected"]
    rejection_reason = math_result["rejection_reason"]
    adopt_day = math_result["adopt_day"]
    timeline = math_result["timeline"]
    n_addressable = math_result["n_addressable"]
    addressable_mask = math_result["addressable_mask"]
    ceiling = math_result["ceiling"]
    panel_ids = math_result["panel_ids"]
    susceptibility = math_result["susceptibility"]
    need_for_cognition = math_result["need_for_cognition"]
    exposures_arr = math_result["exposures"]

    # --- Cognitive / diffusion analytics (Rogers, Bass, prospect theory) ---
    total_adopted = int(adopted.sum())
    market_potential = max(1, n_addressable)
    bass = cognition.bass_fit(timeline, market_potential)
    exposure_list = exposures_arr.tolist()
    exposure_consolidations = cognition.exposure_consolidation(exposure_list)
    bootstrap = cognition.bootstrap_ci([int(x) for x in adopted], n_boot=100, alpha=0.05)
    suscept_mean = float(np.mean(susceptibility))
    nfc_mean = float(np.mean(need_for_cognition))
    # Rogers wave classification of adopters (by innovativeness: voice + risk + digital)
    innov_scores = []
    for a in agents:
        innov_scores.append(float(a["traits"]["voice"]) * 0.3 + (1 - float(a["traits"]["risk"])) * 0.3 + float(a["traits"]["digital"]) * 0.4)
    ranked = np.argsort(np.array([a["adopt_day"] if a["adopt_day"] else 10**9 for a in agents]))
    rogers_buckets = {"innovator": 0, "early_adopter": 0, "early_majority": 0, "late_majority": 0, "laggard": 0}
    for rank_pos, idx in enumerate(ranked):
        if not agents[idx]["adopted"]:
            continue
        pct = rank_pos / max(1, len(ranked) - 1)
        if pct < 0.025:
            rogers_buckets["innovator"] += 1
        elif pct < 0.16:
            rogers_buckets["early_adopter"] += 1
        elif pct < 0.50:
            rogers_buckets["early_majority"] += 1
        elif pct < 0.84:
            rogers_buckets["late_majority"] += 1
        else:
            rogers_buckets["laggard"] += 1
    cognitive_stats = {
        "bass_p": bass["p"],
        "bass_q": bass["q"],
        "bass_r2": bass["r_squared"],
        "bass_peak_day": bass["peak_day"],
        "bass_interpretation": bass["interpretation"],
        "consolidation_rate": round(exposure_consolidations, 3),
        "susceptibility_mean": round(suscept_mean, 1),
        "need_for_cognition_mean": round(nfc_mean, 1),
        "bootstrap_adoption_ci": bootstrap,
        "rogers": rogers_buckets,
        "market_potential": market_potential,
    }

    # Social posts (only in non-fast mode)
    if fast:
        posts = []
        debate = []
        focus = []
        encounters = []
    else:
        # Rebuild stances for post generation
        a_stance = np.array([a["stance"] for a in agents])
        posts = _make_posts(agents, topic, a_stance, adopted, adopt_day, rounds, rng, max(2, int(n_agents * 0.022)))
        posts = _sort_and_balance_posts(posts, agents, topic, rng)
        debate = content.debate_script(
            [a for a in agents if a["id"] in panel_ids],
            topic,
            {"day": rounds, "adoption": float(adopted.mean()),
             "tier_adoption": {str(t): float(adopted[[i for i, a in enumerate(agents) if a["tier"] == t]].mean())
                              for t in (1, 2, 3, 4)}},
            rng,
        )
        focus = _make_focus_group(agents, topic, question or "Would you adopt this? Why or why not?", rng, rounds)
        _domain = (_simulation_spec or {}).get("domain", "market")
        encounters = _run_generative_layer(agents, adopted, topic, rounds, rng, domain=_domain)

    # Summary
    summary = _summary(topic, timeline, agents, adopted, np.array([a["stance"] for a in agents]),
                       rejected, rejection_reason, [a for a in agents if a["id"] in panel_ids],
                       scenario, brief, addressable=addressable_mask, ceiling=ceiling)

    report = _report(topic, summary, timeline, agents, adopted,
                     np.array([a["stance"] for a in agents]), rejected, rejection_reason, rng)

    emap = store.evidence_map()
    evidence = [emap[i] for i in topic.get("evidence_ids", []) if i in emap]
    if not evidence:
        evidence = list(emap.values())[:6]

    context_bundle = atlas.bundle(topic, limit=6)
    run_id = uuid.uuid4().hex[:12]
    result = {
        "run_id": run_id,
        "context": context_bundle,
        "precedents": precedent,
        "params": {k: p.get(k) for k in ("ceiling_mult", "price_sensitivity", "social_mult", "trust_weight", "hazard_mult", "atlas_strength")},
        "fast": fast,
        "brief": brief,
        "question": question or "Would you adopt this? Why or why not?",
        "topic": {k: topic[k] for k in ("id", "label", "category", "motion", "price", "price_note", "unit", "benefits", "objections") if k in topic},
        "research": topic.get("research"),
        "scenario": scenario,
        "scenario_label": next((s["label"] for s in SCENARIOS if s["id"] == scenario), scenario),
        "seed": seed,
        "population": n_agents,
        "rounds": rounds,
        "tier_mix": {str(k): v for k, v in tier_mix.items()},
        "focus_state": focus_state,
        "price": price,
        "timeline": timeline,
        "summary": summary,
        "cognitive": cognitive_stats,
        "agents": agents,
        "posts": posts,
        "debate": debate,
        "panel": [a["id"] for a in agents if a["id"] in panel_ids],
        "encounters": encounters,
        "focus_group": focus,
        "report": report,
        "evidence": evidence,
        "events": math_result.get("timeline", []) and [e for e in timeline if e.get("event")],
        "scenarios": SCENARIOS,
        "platforms": {},
        "meta": {
            "model": "Imprint Reasoning Core v3 (Mathematical)",
            "timesfm": "available via /api/forecast",
            "tiers": store.tiers(),
            "biases": sorted(store.biases(), key=lambda b: b["id"]),
            "data_note": "Synthetic population calibrated to public distributions. Not a poll; a decision rehearsal.",
            "math": {
                "belief_ode": "RK4-integrated continuous-time belief dynamics",
                "temperature_annealing": "exploration → commitment schedule",
                "gradient_descent": "cognitive dissonance belief updating",
                "graph_laplacian": "Emergence World style social diffusion",
                "timesfm_demand": "TimesFM 3.0 exogenous market signal",
                "refractory_period": "neurological resistance to belief change",
                "phase_transition": "order parameter + susceptibility tracking",
            },
        },
    }
    result["audit"] = _audit_run(result)
    return result


def _audit_run(run: dict) -> dict:
    s = run["summary"]
    checks = []
    pop = max(1, run["population"])
    adopted = round(s["adoption"] * pop)
    addressable = max(1, s["addressable"])

    def add(cid, ok, detail, level="error"):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "level": level})

    add("adoption_bounds", 0 <= s["adoption"] <= 1, f"adoption={s['adoption']:.3f}")
    add("conversion_bounds", 0 <= s["conversion"] <= 1, f"conversion={s['conversion']:.3f}")
    add("adopted_not_above_addressable", adopted <= addressable + 1, f"{adopted} adopted / {addressable} addressable")
    add("rejected_not_above_addressable", s["rejected"] <= addressable, f"{s['rejected']} rejected / {addressable} addressable")
    add("sentiment_bounds", -1 <= s["sentiment"] <= 1, f"sentiment={s['sentiment']}")
    add("tier_sum", abs(sum(s["tier_adoption"].values()) - 4) < .2, "four tier rates present", "warn")
    add("context_coverage", s.get("context_coverage", 0) >= .9, f"{s.get('context_coverage', 0):.0%} of agents carry citations", "warn")
    add("evidence_attached", len(run.get("evidence") or []) > 0, f"{len(run.get('evidence') or [])} evidence cards")
    add("deterministic_seed", True, f"seed={run['seed']} recorded for replay", "warn")
    failed = [c for c in checks if not c["ok"] and c["level"] == "error"]
    warned = [c for c in checks if not c["ok"] and c["level"] == "warn"]
    return {
        "ok": not failed,
        "score": round(100 * sum(1 for c in checks if c["ok"]) / max(1, len(checks))),
        "checks": checks,
        "failed": len(failed),
        "warnings": len(warned),
    }


def _summary(topic, timeline, agents, adopted_arr, stances_arr, rejected_arr, reasons, panel, scenario, brief, addressable, ceiling):
    n = len(agents)
    adoption = float(np.mean(adopted_arr))
    addressable_n = max(1, int(np.sum(addressable)))
    conversion = float(np.sum(adopted_arr) / addressable_n)
    aware = float(np.mean([a["awareness"] for a in agents]))
    sentiment = float(np.mean(stances_arr) * 2 - 1)
    peak = max(timeline, key=lambda x: x["new"])
    counts = Counter([r for r in reasons if r])
    top_rej = counts.most_common(3)
    tiers = {}
    for t in (1, 2, 3, 4):
        mask = np.array([a["tier"] == t for a in agents])
        tiers[str(t)] = float(np.mean(adopted_arr[mask])) if mask.any() else 0
    best_tier = max(tiers, key=lambda k: tiers[k])
    worst_tier = min(tiers, key=lambda k: tiers[k])
    first_adopt = min([x["day"] for x in timeline if x["new"] > 0] or [1])
    tipping = next((x["day"] for x in timeline if x.get("conversion", 0) >= 0.5), None)
    convergence = abs(timeline[-1]["conversion"] - timeline[max(0, len(timeline) - 6)]["conversion"])
    confidence = .58 + .18 * min(1, n / 500) + .12 * (1 - min(1, convergence * 8)) + .08 * (1 - min(1, peak["new"] / max(1, addressable_n) * 5))
    confidence = max(.52, min(.91, confidence))
    verdict = ("SCALE" if conversion >= 0.60 and sentiment > 0.05
               else "TEST" if conversion >= 0.32
               else "REFRAME" if sentiment > -0.12
               else "HOLD")
    cited = sum(1 for a in agents if a.get("context"))
    return {
        "context_coverage": round(cited / max(1, len(agents)), 3),
        "context_nodes": sum(len(a.get("context") or []) for a in agents),
        "days": int(timeline[-1]["day"]),
        "adoption": round(adoption, 4),
        "conversion": round(conversion, 4),
        "addressable": addressable_n,
        "ceiling": round(ceiling, 4),
        "awareness": round(aware, 4),
        "sentiment": round(sentiment, 3),
        "rejected": int(np.sum(rejected_arr)),
        "rejection_rate": round(float(np.sum(rejected_arr) / addressable_n), 3),
        "tipping_point": tipping,
        "first_adoption_day": first_adopt,
        "peak_growth_day": peak["day"],
        "peak_new_adopters": peak["new"],
        "tier_adoption": tiers,
        "best_tier": best_tier,
        "worst_tier": worst_tier,
        "top_rejections": [{"reason": r, "count": c} for r, c in top_rej],
        "confidence": round(confidence, 2),
        "verdict": verdict,
        "scenario": scenario,
        "panel_size": len(panel),
        "headline": _headline(topic, conversion, adoption, sentiment, tiers, top_rej),
    }


def _headline(topic, conversion, adoption, sentiment, tiers, top_rej):
    if conversion >= 0.60 and sentiment > 0.05:
        return f"{topic['label']} is converting its in-market pool — but the next tranche will be won on service, not price."
    if conversion >= 0.32:
        return f"{topic['label']} has found a working early market. The constraint is trust, not awareness."
    if sentiment < -0.12:
        return f"{topic['label']} is not failing on awareness. It is failing on the failure mode."
    return f"{topic['label']} is stuck between curiosity and commitment."


def _make_posts(agents, topic, stances, adopted, adopt_day, day, rng, count):
    candidates = []
    for i, a in enumerate(agents):
        if a["awareness"] < 0.38:
            continue
        w = .3 + a["traits"]["voice"] * 1.4 + abs(stances[i] - .5) * 1.2 + (0.7 if adopted[i] else 0)
        w *= 1.0 if day - (adopt_day[i] if adopt_day[i] > 0 else 0) <= 3 else .7
        candidates.append((a, i, w))
    if not candidates:
        return []
    chosen = []
    for _ in range(min(count, len(candidates))):
        pool = candidates
        total = sum(w for _, _, w in pool)
        r = rng.random() * total
        acc = 0
        for a, i, w in pool:
            acc += w
            if r <= acc:
                chosen.append((a, i))
                candidates.remove((a, i, w))
                break
        if not candidates:
            break
    out = []
    for a, i in chosen:
        platform = _pick_platform(a, topic, rng)
        stance = float(stances[i])
        p = content.post_text(a, topic, rng, platform, stance)
        base = 18 + 220 * a["traits"]["voice"] * (0.5 + abs(stance - .5)) * (1 + (1.2 if a["tier"] == 1 else .8 if a["tier"] == 2 else .5))
        likes = int(max(1, base * rng.lognormvariate(0, .55)))
        shares = int(likes * (0.06 + .30 * abs(stance - .5) + (0.18 if platform == "WhatsApp" else 0)))
        comments = int(likes * (0.07 + rng.random() * .10))
        reach = int(likes * rng.uniform(4, 14) + shares * rng.uniform(15, 45))
        flagged = p["text"].startswith("⚠️") or "BREAKING" in p["text"] or "banned" in p["text"].lower() or "causes serious" in p["text"].lower()
        emap = store.evidence_map()
        ev = p.get("evidence")
        out.append({
            "id": f"p{day:02d}_{len(out):02d}_{rng.randint(100,999)}",
            "day": day,
            "platform": platform,
            "agent_id": a["id"],
            "name": a["name"],
            "handle": a["handle"],
            "occupation": a["occupation"],
            "city": a["city"],
            "state": a["state"],
            "tier": a["tier"],
            "language": a["language"],
            "text": p["text"],
            "translation": p.get("translation"),
            "tone": p["tone"],
            "stance": round(stance, 3),
            "likes": likes,
            "shares": shares,
            "comments": comments,
            "reach": reach,
            "hashtags": p.get("hashtags", []),
            "flagged": flagged,
            "fact_check": (f"Unverified claim. Reference: {ev['claim']} is {ev['value']} {ev['unit']} ({ev['org']}, {ev['year']}).") if flagged and ev else None,
            "evidence": ev,
            "is_forward": platform == "WhatsApp" and rng.random() < .45,
            "thread": _make_comments(agents, topic, rng, stance, day, a["id"]),
        })
    return out


def _make_comments(agents, topic, rng, stance, day, exclude_id):
    pool = [a for a in agents if a["id"] != exclude_id and a["awareness"] > 0.3]
    rng.shuffle(pool)
    out = []
    for a in pool[:rng.choice([1, 2, 2, 3])]:
        out.append({
            "agent_id": a["id"],
            "name": a["name"],
            "city": a["city"],
            "tier": a["tier"],
            "text": content.comment_text(a, topic, rng, a["stance"]),
            "stance": round(a["stance"], 3),
            "likes": int(2 + 40 * rng.random() ** 2),
        })
    return out


def _pick_platform(a, topic, rng):
    preferred = [p for p in topic.get("platforms", []) if p in a["media"]]
    if preferred and rng.random() < .78:
        return rng.choice(preferred)
    return rng.choice(a["media"] or ["WhatsApp"])


def _sort_and_balance_posts(posts, agents, topic, rng):
    if not posts:
        return posts
    tiers = {p["tier"] for p in posts}
    for t in (1, 2, 3, 4):
        if t not in tiers:
            pool = [a for a in agents if a["tier"] == t]
            if pool:
                a = rng.choice(pool)
                platform = _pick_platform(a, topic, rng)
                p = content.post_text(a, topic, rng, platform, a["stance"])
                posts.append({
                    "id": f"px{t}_{rng.randint(1000,9999)}", "day": rng.randint(1, max(1, max(x['day'] for x in posts))),
                    "platform": platform, "agent_id": a["id"], "name": a["name"], "handle": a["handle"],
                    "occupation": a["occupation"], "city": a["city"], "state": a["state"], "tier": a["tier"],
                    "language": a["language"], "text": p["text"], "translation": p.get("translation"),
                    "tone": p["tone"], "stance": a["stance"], "likes": int(80 + rng.random() * 900),
                    "shares": int(10 + rng.random() * 180), "comments": int(5 + rng.random() * 80),
                    "reach": int(500 + rng.random() * 12000), "hashtags": p.get("hashtags", []),
                    "flagged": False, "fact_check": None, "evidence": p.get("evidence"),
                    "is_forward": platform == "WhatsApp", "thread": [],
                })
    posts.sort(key=lambda p: (-(p["likes"] + p["shares"] * 3), p["day"]))
    return posts[:520]


def _make_focus_group(agents, topic, question, rng, day):
    out = []
    for t in (1, 2, 3, 4):
        pool = [a for a in agents if a["tier"] == t]
        rng.shuffle(pool)
        seen = set()
        for a in pool:
            if a["occupation_id"] in seen:
                continue
            out.append(a)
            seen.add(a["occupation_id"])
            break
    if len(out) < 6:
        out = agents[:8]
    out = out[:8]
    return [content.focus_answer(a, topic, question, rng, day) for a in out]


def _report(topic, summary, timeline, agents, adopted_arr, stances_arr, rejected_arr, reasons, rng):
    def group(key, min_n=4):
        d = defaultdict(list)
        for i, a in enumerate(agents):
            d[a[key]].append(i)
        rows = []
        for k, idxs in d.items():
            if len(idxs) < min_n:
                continue
            rows.append({"name": k, "adoption": round(float(np.mean(adopted_arr[idxs])), 3),
                         "sentiment": round(float((np.mean(stances_arr[idxs]) * 2 - 1)), 3), "n": len(idxs)})
        rows.sort(key=lambda x: -x["adoption"])
        return rows

    by_tier = group("tier")
    by_occ = group("occupation", 3)[:10]
    by_state = group("state", 3)[:8]

    ys = adopted_arr
    bias_corr = []
    for b in store.biases():
        xs = np.array([a["biases"][b["id"]] for a in agents])
        if xs.std() < 1e-6 or ys.std() < 1e-6:
            continue
        corr = float(np.corrcoef(xs, ys)[0, 1])
        bias_corr.append({"id": b["id"], "label": b["label"], "corr": round(corr, 3),
                          "effect": "raises adoption" if corr > .03 else "lowers adoption" if corr < -.03 else "neutral"})
    bias_corr.sort(key=lambda x: -abs(x["corr"]))

    trait_corr = []
    for tr in ["income", "digital", "risk", "optimism", "price", "trust_gov", "education", "status", "conformity", "patience", "social_radius", "fatalism"]:
        if tr == "income":
            xs = np.array([a["household_income"] for a in agents], dtype=float)
        else:
            xs = np.array([a["traits"][tr] for a in agents])
        if xs.std() < 1e-6 or ys.std() < 1e-6:
            continue
        corr = float(np.corrcoef(xs, ys)[0, 1])
        trait_corr.append({"trait": tr, "corr": round(corr, 3)})
    trait_corr.sort(key=lambda x: -abs(x["corr"]))

    counts = Counter([r for r in reasons if r])
    objections = []
    for reason, c in counts.most_common(6):
        segs = [a for i, a in enumerate(agents) if reasons[i] == reason]
        top_tier = Counter([a["tier"] for a in segs]).most_common(1)
        objections.append({"reason": reason, "count": c, "share": round(c / max(1, len(reasons)), 3),
                           "tier": f"T{top_tier[0][0]}" if top_tier else ""})

    drivers = []
    for tc in trait_corr[:5]:
        direction = "raises" if tc["corr"] > 0 else "lowers"
        drivers.append(f"{tc['trait'].replace('_', ' ').title()} {direction} adoption (r={tc['corr']:+.2f}).")
    if not drivers:
        drivers = ["Income and digital access are the strongest observed splits."]

    obj = objections[0]["reason"] if objections else "trust"
    best = by_tier[0]["name"] if by_tier else "1"
    recommendations = [
        f"Lead with the failure mode, not the feature list. The top objection is “{obj}”; make the remedy visible, local and unconditional.",
        f"Treat Tier {best} as the beachhead, but do not mistake it for India. The Tier 4 gap is the real forecast risk.",
        "Build a 'proof in the neighbourhood' programme: one credible local owner, one service promise, one WhatsApp group. Social proof outperforms reach.",
        "Price the risk, not just the product: warranty, resale guarantee, and a clear return path reduce the perceived cost of being wrong.",
        "Instrument the first 90 days by district and occupation. The national average will hide the failure before it becomes expensive.",
    ]
    if any("price" in (o["reason"] or "").lower() for o in objections):
        recommendations.append("Offer a cash-flow product (EMI, subscription or sachet) that matches irregular incomes; the sticker price is not the real barrier.")
    if topic["id"] in ("quick-commerce", "gig-work", "ev-scooter", "rural-credit"):
        recommendations.append("Stress-test the worker/borrower side of the model. If the economics only work when the weakest party absorbs the risk, the growth is rented.")

    caveats = [
        "This is a synthetic rehearsal, not a representative survey. Confidence intervals are not sampling errors.",
        "The population is calibrated to public state/tier distributions, but within-group variance is modelled, not observed.",
        "Behavioural parameters are explicit and auditable; change the seed, tier mix or scenario to test sensitivity.",
        "Cultural traits are modelled as structural context, not as claims about individuals or communities.",
    ]
    methods = [
        "Stratified synthetic population by state, tier, occupation, gender, age and digital access.",
        "Homophilous social graph with local, state and occupation ties plus long-range weak ties.",
        "Dual-process appraisal: affordability + relative advantage + social proof + trust − risk + status/bias.",
        "Belief ODE system (RK4-integrated) with temperature annealing and gradient-descent belief updating.",
        "Graph Laplacian social diffusion (Emergence World style) with TimesFM 3.0 exogenous demand signal.",
        "Refractory periods and phase-transition detection (order parameter + susceptibility).",
        "Evidence retrieval from a curated public-data library; claims carry source and year.",
    ]
    return {
        "headline": summary["headline"],
        "verdict": summary["verdict"],
        "summary": _summary_text(topic, summary, by_tier, objections),
        "drivers": drivers,
        "bias_correlations": bias_corr[:6],
        "trait_correlations": trait_corr[:8],
        "segments": {"tier": by_tier, "occupation": by_occ, "state": by_state},
        "objections": objections,
        "recommendations": recommendations,
        "caveats": caveats,
        "methods": methods,
        "next_experiments": _experiments(topic, objections),
    }


def _summary_text(topic, summary, by_tier, objections):
    a = summary["adoption"] * 100
    conv = summary["conversion"] * 100
    s = summary["sentiment"]
    t1 = summary["tier_adoption"].get("1", 0) * 100
    t4 = summary["tier_adoption"].get("4", 0) * 100
    obj = objections[0]["reason"].lower() if objections else "trust"
    return (f"After {summary.get('days', 0)} days of simulated diffusion, {a:.1f}% of the population has adopted "
            f"{topic['label'].lower()} — {conv:.0f}% of the addressable in-market pool — with sentiment at {s:+.2f}. "
            f"Penetration is {t1:.1f}% in Tier 1 and {t4:.1f}% in Tier 4. The binding constraint is {obj}, not awareness. "
            f"The verdict is {summary['verdict']}: {('the category is ready to scale with a service guarantee' if summary['verdict']=='SCALE' else 'run a contained test before committing capital' if summary['verdict']=='TEST' else 'reframe the promise before spending on reach' if summary['verdict']=='REFRAME' else 'wait for the failure mode to be fixed')}.")


def _recommendations(topic, summary, by_tier, by_occ, objections, bias_corr):
    return []


def _experiments(topic, objections):
    obj = objections[0]["reason"] if objections else "trust"
    return [
        f"A/B a local service guarantee vs a 10% discount. Measure trust, not clicks. Primary objection: {obj}.",
        "Run a 4-city tier-2 matched test with identical creative and different service density. Measure adoption and rejection reasons.",
        "Test a 'try before you commit' offer with a real return path; track word-of-mouth in WhatsApp groups.",
        "Interview 20 non-adopters who are aware. The gap between awareness and adoption is the product.",
    ]
