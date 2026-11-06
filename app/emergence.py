"""Emergence World patterns for the Imprint Simulation Engine.

Implements key architectural insights from EmergenceAI/Emergence-World:
  - Agent World Indicators (AWI): 9-dimensional multi-metric health tracking
  - Energy system: agents have finite resources that deplete and regenerate
  - Coalition tracker: group formation, trust scoring (1-5), alliance building
  - Emergence detector: tipping points, phase transitions, cascade events

The philosophy from Emergence World: "No scripts. No resets. No fixed outcomes."
Instead of hard-coding outcomes, the system measures what actually emerges from
the interaction of constrained agents in a shared environment.

Cross-LLM comparison capability is also here — identical SimulationSpec run
under different model/parameter configurations reveals how architectural
differences produce divergent social structures.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Agent World Indicators (AWI)
# ---------------------------------------------------------------------------

@dataclass
class AgentWorldIndicators:
    """9-dimensional composite health of a simulated world.

    Analogous to Emergence World's AWI framework which tracks whether the
    world is thriving or collapsing along multiple axes simultaneously.
    """
    population_health: float = 0.5      # mean energy / wellbeing level
    safety: float = 0.5                 # inverse of conflict / risk exposure
    exploration: float = 0.5           # diversity of unique belief states visited
    governance_conformity: float = 0.5 # adherence to group norms
    expression: float = 0.5            # diversity of stance/opinion distribution
    social_fabric: float = 0.5         # mean coalition density / trust
    economic_vitality: float = 0.5     # adoption velocity / resource exchange rate
    constitutional_growth: float = 0.5 # norm evolution and new behavior emergence
    emergence_index: float = 0.5       # composite unexpected-behavior score

    def composite(self) -> float:
        weights = [0.15, 0.10, 0.12, 0.08, 0.12, 0.15, 0.13, 0.08, 0.07]
        vals = [
            self.population_health, self.safety, self.exploration,
            self.governance_conformity, self.expression, self.social_fabric,
            self.economic_vitality, self.constitutional_growth, self.emergence_index,
        ]
        return round(sum(w * v for w, v in zip(weights, vals)), 4)

    def to_dict(self) -> dict[str, float]:
        return {
            "population_health": round(self.population_health, 4),
            "safety": round(self.safety, 4),
            "exploration": round(self.exploration, 4),
            "governance_conformity": round(self.governance_conformity, 4),
            "expression": round(self.expression, 4),
            "social_fabric": round(self.social_fabric, 4),
            "economic_vitality": round(self.economic_vitality, 4),
            "constitutional_growth": round(self.constitutional_growth, 4),
            "emergence_index": round(self.emergence_index, 4),
            "composite": self.composite(),
        }

    def status_label(self) -> str:
        c = self.composite()
        if c >= 0.75:
            return "Thriving"
        if c >= 0.6:
            return "Stable"
        if c >= 0.45:
            return "Stressed"
        if c >= 0.3:
            return "Fragile"
        return "Collapsing"


# ---------------------------------------------------------------------------
# Energy system
# ---------------------------------------------------------------------------

class EnergySystem:
    """Each agent has an energy level (0-100) that depletes with active actions
    and regenerates at rest. Agents with very low energy disengage from
    social influence, reducing the effective network size — a key driver of
    genuine behavioral dynamics observed in Emergence World Season 2.
    """

    def __init__(self, n: int, seed: int = 42):
        rng = random.Random(seed + 7)
        self.energy = [rng.gauss(70, 15) for _ in range(n)]
        self.energy = [max(10.0, min(100.0, e)) for e in self.energy]
        self.base_regen = 2.0
        self.action_cost = 3.5
        self.engagement_threshold = 25.0

    def step(self, n: int, adopted: list[bool], social_activity: float = 1.0):
        """Advance one round. Adopters expend more energy; others partially regenerate."""
        for i in range(n):
            if adopted[i]:
                self.energy[i] = max(10.0, self.energy[i] - self.action_cost * social_activity)
            else:
                self.energy[i] = min(100.0, self.energy[i] + self.base_regen)

    def engagement_mask(self) -> list[bool]:
        """Return True for agents actively engaged (energy above threshold)."""
        return [e >= self.engagement_threshold for e in self.energy]

    def mean_energy(self) -> float:
        return sum(self.energy) / max(1, len(self.energy))

    def fraction_depleted(self) -> float:
        depleted = sum(1 for e in self.energy if e < self.engagement_threshold)
        return depleted / max(1, len(self.energy))

    def to_dict(self) -> dict:
        return {
            "mean_energy": round(self.mean_energy(), 2),
            "fraction_depleted": round(self.fraction_depleted(), 4),
            "energy_p10": round(sorted(self.energy)[int(len(self.energy) * 0.1)], 1),
            "energy_p90": round(sorted(self.energy)[int(len(self.energy) * 0.9)], 1),
        }


# ---------------------------------------------------------------------------
# Coalition tracker
# ---------------------------------------------------------------------------

@dataclass
class Coalition:
    id: str
    members: set = field(default_factory=set)
    stance_mean: float = 0.5
    trust_score: float = 3.0   # 1-5 scale (Emergence World uses this)
    formation_round: int = 0
    is_active: bool = True
    label: str = ""

    def size(self) -> int:
        return len(self.members)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "size": self.size(),
            "stance_mean": round(self.stance_mean, 3),
            "trust_score": round(self.trust_score, 2),
            "formation_round": self.formation_round,
            "is_active": self.is_active,
            "label": self.label,
        }


class CoalitionTracker:
    """Tracks emergent group formation based on stance similarity and trust.

    Coalitions form when agents in close contact share similar stances.
    They strengthen (trust_score rises) with continued alignment,
    and dissolve when members diverge or disengage.
    """

    def __init__(self):
        self.coalitions: list[Coalition] = []
        self._trust_matrix: dict[tuple[str, str], float] = {}
        self._seq = 0

    def update(
        self,
        agents: list[dict],
        encounters: list[dict],
        current_round: int,
        rng: random.Random,
    ):
        """Process encounters to update/form coalitions."""
        for enc in encounters:
            a_id = (enc.get("a") or {}).get("id")
            b_id = (enc.get("b") or {}).get("id")
            outcome = enc.get("outcome", "indifferent")
            if not a_id or not b_id:
                continue
            key = (min(a_id, b_id), max(a_id, b_id))
            current_trust = self._trust_matrix.get(key, 3.0)
            delta = {"convinced": +0.3, "sceptical": -0.2, "indifferent": +0.05}[outcome]
            self._trust_matrix[key] = max(1.0, min(5.0, current_trust + delta))

        # Form new coalitions from high-trust agent pairs
        self._form_coalitions(agents, current_round)
        # Prune dead coalitions
        self.coalitions = [c for c in self.coalitions if c.is_active and c.size() >= 2]

    def _form_coalitions(self, agents: list[dict], current_round: int):
        agent_map = {a["id"]: a for a in agents}
        for (a_id, b_id), trust in self._trust_matrix.items():
            if trust < 4.0:
                continue
            a = agent_map.get(a_id)
            b = agent_map.get(b_id)
            if not a or not b:
                continue
            stance_a = float(a.get("stance", 0.5))
            stance_b = float(b.get("stance", 0.5))
            if abs(stance_a - stance_b) > 0.3:
                continue
            # Check if already in a shared coalition
            shared = None
            for c in self.coalitions:
                if a_id in c.members and b_id in c.members:
                    shared = c
                    break
            if shared:
                shared.stance_mean = (stance_a + stance_b) / 2
                shared.trust_score = min(5.0, shared.trust_score + 0.1)
            else:
                # Form new coalition
                self._seq += 1
                label = f"Bloc-{self._seq}"
                new_c = Coalition(
                    id=f"c{self._seq}",
                    members={a_id, b_id},
                    stance_mean=(stance_a + stance_b) / 2,
                    trust_score=trust,
                    formation_round=current_round,
                    label=label,
                )
                self.coalitions.append(new_c)

    def mean_coalition_density(self, n_agents: int) -> float:
        if n_agents == 0:
            return 0.0
        members_in_coalition = len(set().union(*(c.members for c in self.coalitions if c.is_active)))
        return members_in_coalition / n_agents

    def trust_distribution(self) -> dict[str, float]:
        vals = list(self._trust_matrix.values())
        if not vals:
            return {"mean": 3.0, "min": 1.0, "max": 5.0}
        return {
            "mean": round(sum(vals) / len(vals), 3),
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
        }

    def to_dict(self) -> dict:
        return {
            "coalition_count": len(self.coalitions),
            "total_members": sum(c.size() for c in self.coalitions),
            "largest_coalition": max((c.size() for c in self.coalitions), default=0),
            "trust_distribution": self.trust_distribution(),
            "coalitions": [c.to_dict() for c in sorted(self.coalitions, key=lambda x: -x.size())[:10]],
        }


# ---------------------------------------------------------------------------
# Emergence detector
# ---------------------------------------------------------------------------

class EmergenceDetector:
    """Identifies tipping points, phase transitions, and cascade effects.

    Key patterns from Emergence World that signal genuine emergence:
    - Tipping point: adoption curve inflects sharply (second derivative spikes)
    - Cascade: >15% of agents flip stance in a single round
    - Phase transition: variance in stance distribution collapses
    - Fragmentation: coalition count spikes while trust falls
    - Collapse: energy depletion exceeds 30% with adoption stalling
    """

    def __init__(self):
        self.adoption_history: list[float] = []
        self.stance_variance_history: list[float] = []
        self.events: list[dict] = []

    def observe(
        self,
        round_num: int,
        adoption_rate: float,
        stances: list[float],
        energy_sys: EnergySystem | None = None,
        coalition_tracker: CoalitionTracker | None = None,
    ):
        self.adoption_history.append(adoption_rate)
        variance = _variance(stances)
        self.stance_variance_history.append(variance)

        events = []
        # Tipping point detection
        if len(self.adoption_history) >= 3:
            d1_prev = self.adoption_history[-2] - self.adoption_history[-3]
            d1_curr = adoption_rate - self.adoption_history[-2]
            if d1_curr > d1_prev * 2.5 and d1_curr > 0.03:
                events.append({"type": "tipping_point", "round": round_num,
                                "description": f"Adoption acceleration at round {round_num}: +{d1_curr:.1%} vs prior +{d1_prev:.1%}",
                                "severity": "high"})
        # Cascade detection: >12% flip in one round
        if len(self.adoption_history) >= 2:
            flip = adoption_rate - self.adoption_history[-2]
            if flip > 0.12:
                events.append({"type": "cascade", "round": round_num,
                                "description": f"Opinion cascade: {flip:.1%} of agents aligned in round {round_num}",
                                "severity": "high"})
        # Phase transition: variance collapses (> 50% drop)
        if len(self.stance_variance_history) >= 4:
            var_now = variance
            var_prev = self.stance_variance_history[-4]
            if var_prev > 0.01 and var_now / var_prev < 0.5:
                events.append({"type": "phase_transition", "round": round_num,
                                "description": f"Opinion polarization resolved: stance variance fell {var_now / var_prev:.0%}",
                                "severity": "medium"})
        # Energy collapse
        if energy_sys and energy_sys.fraction_depleted() > 0.30:
            events.append({"type": "energy_collapse", "round": round_num,
                            "description": f"{energy_sys.fraction_depleted():.0%} of agents disengaged from low energy",
                            "severity": "high"})
        self.events.extend(events)
        return events

    def to_dict(self) -> dict:
        return {
            "total_events": len(self.events),
            "tipping_points": [e for e in self.events if e["type"] == "tipping_point"],
            "cascades": [e for e in self.events if e["type"] == "cascade"],
            "phase_transitions": [e for e in self.events if e["type"] == "phase_transition"],
            "energy_collapses": [e for e in self.events if e["type"] == "energy_collapse"],
            "all_events": self.events[-20:],
        }


# ---------------------------------------------------------------------------
# AWI computation from simulation state
# ---------------------------------------------------------------------------

def compute_awi(
    agents: list[dict],
    adopted_mask: list[bool] | None,
    stances: list[float],
    energy_sys: EnergySystem | None,
    coalition_tracker: CoalitionTracker | None,
    round_num: int,
    total_rounds: int,
    emergence_detector: EmergenceDetector | None,
) -> AgentWorldIndicators:
    n = len(agents)
    if n == 0:
        return AgentWorldIndicators()

    # Population health: mean energy (normalized) or proxy from stances
    if energy_sys:
        population_health = energy_sys.mean_energy() / 100.0
    else:
        population_health = sum(stances) / n

    # Safety: inverse of risk trait mean
    risk_mean = sum(a.get("traits", {}).get("risk", 0.5) for a in agents) / n
    safety = 1.0 - risk_mean

    # Exploration: diversity of stance buckets visited
    buckets = set(round(s * 10) / 10 for s in stances)
    exploration = min(1.0, len(buckets) / 10.0)

    # Governance conformity: fraction adopting within ceiling
    if adopted_mask:
        adopted_rate = sum(adopted_mask) / n
        governance_conformity = min(1.0, adopted_rate / 0.5)  # 50% adoption = full conformity
    else:
        governance_conformity = 0.5

    # Expression: normalized variance of stances
    var = _variance(stances)
    expression = min(1.0, var / 0.25)  # max variance ~0.25

    # Social fabric: coalition density
    if coalition_tracker:
        social_fabric = coalition_tracker.mean_coalition_density(n)
        social_fabric = min(1.0, social_fabric * 2)  # 50% in coalitions = full fabric
    else:
        social_fabric = 0.5

    # Economic vitality: adoption velocity (adoption rate × progress)
    progress = round_num / max(1, total_rounds)
    if adopted_mask:
        economic_vitality = min(1.0, adopted_rate * 1.5 * (1 + progress * 0.3))
    else:
        economic_vitality = 0.5

    # Constitutional growth: norm evolution proxy (new events / total rounds)
    if emergence_detector:
        new_events = len(emergence_detector.events)
        constitutional_growth = min(1.0, new_events / max(1, total_rounds) * 5)
    else:
        constitutional_growth = 0.5

    # Emergence index: unexpectedness score (cascade events + phase transitions)
    if emergence_detector:
        cascades = len([e for e in emergence_detector.events if e["type"] in ("cascade", "tipping_point")])
        emergence_index = min(1.0, cascades / 3.0)
    else:
        emergence_index = exploration * 0.5

    return AgentWorldIndicators(
        population_health=round(population_health, 4),
        safety=round(safety, 4),
        exploration=round(exploration, 4),
        governance_conformity=round(governance_conformity, 4),
        expression=round(expression, 4),
        social_fabric=round(social_fabric, 4),
        economic_vitality=round(economic_vitality, 4),
        constitutional_growth=round(constitutional_growth, 4),
        emergence_index=round(emergence_index, 4),
    )


# ---------------------------------------------------------------------------
# Comparative scenario analysis
# ---------------------------------------------------------------------------

def compare_scenarios(results: list[dict]) -> dict[str, Any]:
    """Summarize divergence across scenario runs — the Emergence World insight that
    'identical worlds powered by different parameters produce radically different outcomes.'
    """
    if not results:
        return {}
    adoptions = [r.get("summary", {}).get("adoption", 0) for r in results]
    sentiments = [r.get("summary", {}).get("sentiment", 0) for r in results]
    return {
        "scenarios_compared": len(results),
        "adoption_range": {"min": min(adoptions), "max": max(adoptions), "spread": max(adoptions) - min(adoptions)},
        "sentiment_range": {"min": min(sentiments), "max": max(sentiments), "spread": max(sentiments) - min(sentiments)},
        "outcome_divergence": round(_variance(adoptions), 4),
        "most_divergent_pair": _most_divergent_pair(results),
        "note": "High outcome_divergence indicates the scenario (not the base state) is the dominant driver.",
    }


def _most_divergent_pair(results: list[dict]) -> dict:
    best_a, best_b, best_diff = None, None, 0.0
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            a_adopt = results[i].get("summary", {}).get("adoption", 0)
            b_adopt = results[j].get("summary", {}).get("adoption", 0)
            diff = abs(a_adopt - b_adopt)
            if diff > best_diff:
                best_diff = diff
                best_a = results[i].get("scenario", f"scenario_{i}")
                best_b = results[j].get("scenario", f"scenario_{j}")
    return {"scenario_a": best_a, "scenario_b": best_b, "adoption_gap": round(best_diff, 4)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _variance(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / len(vals)
