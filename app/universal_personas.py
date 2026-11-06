"""Universal agent population generator.

For India context queries: delegates to the existing, deeply-calibrated
personas.py (1,600 possible agents, 36 states, 4 tiers, full caste/religion/
income distributions from Census/NFHS/PLFS).

For non-India queries: generates a population described by a SimulationSpec
from the query interpreter, using configurable segments, trait distributions,
and social network structure.

Every generated agent has the same interface as an India agent so the engine,
concordia GM, and memory system can work without modification:
  id, name, state/region (mapped to context), tier/segment_id,
  occupation, household_income, digital, traits{}, biases{}, stance,
  social_radius, city, age, gender, language, education
"""
from __future__ import annotations

import hashlib
import math
import random
from typing import Any


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_population(
    n: int,
    spec: dict[str, Any],
    seed: int = 42,
    focus_segment: str | None = None,
) -> list[dict]:
    """Return a list of n agent dicts from a SimulationSpec.

    If spec['is_india_context'] is True, delegates to personas.py's
    _build_population so Indian calibration data is used.
    """
    if spec.get("is_india_context"):
        from . import personas
        tier_mix = _india_tier_mix_from_spec(spec)
        return personas.build_population(
            n=n,
            tier_mix=tier_mix,
            seed=seed,
            focus_state=focus_segment,
        )

    return _build_universal_population(n, spec, seed, focus_segment)


# ---------------------------------------------------------------------------
# Universal population builder
# ---------------------------------------------------------------------------

UNIVERSAL_OCCUPATIONS = [
    "Professional", "Manager", "Entrepreneur", "Student",
    "Worker", "Freelancer", "Retiree", "Homemaker",
    "Public servant", "Researcher",
]

GENERIC_NAMES_BY_GENDER = {
    "M": ["Alex", "Jordan", "Sam", "Morgan", "Taylor", "Casey", "Riley", "Drew",
          "Chris", "Jamie", "Robin", "Avery", "Kendall", "Quinn", "Blake"],
    "F": ["Alex", "Jordan", "Sam", "Morgan", "Taylor", "Casey", "Riley", "Drew",
          "Madison", "Jamie", "Robin", "Avery", "Kendall", "Quinn", "Blake"],
}

DOMAIN_LOCATIONS: dict[str, list[str]] = {
    "politics": ["Washington DC", "New York", "Chicago", "Houston", "Phoenix",
                 "Philadelphia", "Los Angeles", "Atlanta", "Boston", "Denver"],
    "organizational": ["HQ Campus", "Remote", "Branch Office", "Field Office",
                       "Regional Hub", "Satellite Office"],
    "finance": ["New York", "London", "Hong Kong", "Singapore", "Chicago",
                "San Francisco", "Frankfurt", "Tokyo", "Sydney", "Toronto"],
    "technology": ["San Francisco", "Seattle", "Austin", "New York", "Boston",
                   "London", "Berlin", "Singapore", "Bangalore", "Toronto"],
    "social": ["Urban", "Suburban", "Rural", "College Town", "Coastal Metro",
               "Inland Metro", "Small Town", "Exurban"],
    "science": ["Research Institute", "University", "Hospital", "Lab", "Field Site"],
    "historical": ["Capital", "Major City", "Provincial Town", "Rural Area", "Port City"],
}


def _build_universal_population(
    n: int,
    spec: dict[str, Any],
    seed: int,
    focus_segment: str | None,
) -> list[dict]:
    rng = random.Random(seed)
    pop_spec = spec.get("population_spec", {})
    segments = pop_spec.get("segments") or _default_segments_from_domain(spec.get("domain", "custom"))
    universal_traits = pop_spec.get("universal_traits", {})
    domain = spec.get("domain", "custom")
    locations = DOMAIN_LOCATIONS.get(domain, ["Location A", "Location B", "Location C",
                                               "Location D", "Location E"])

    # Normalize segment shares
    total = sum(s.get("share", 1 / len(segments)) for s in segments)
    for s in segments:
        s["share"] = s.get("share", 1 / len(segments)) / total

    # Assign agents to segments
    cum = 0.0
    cutoffs = []
    for s in segments:
        cum += s["share"]
        cutoffs.append((cum, s))

    agents = []
    for i in range(n):
        r = rng.random()
        segment = segments[-1]
        for cutoff, seg in cutoffs:
            if r <= cutoff:
                segment = seg
                break
        agent = _make_agent(i, segment, universal_traits, locations, domain, spec, rng, seed)
        agents.append(agent)

    return agents


def _make_agent(
    idx: int,
    segment: dict,
    universal_traits: dict,
    locations: list[str],
    domain: str,
    spec: dict,
    rng: random.Random,
    seed: int,
) -> dict:
    gender = rng.choice(["M", "F"])
    name = rng.choice(GENERIC_NAMES_BY_GENDER[gender]) + " " + _surname(rng, domain)
    occupation = rng.choice(UNIVERSAL_OCCUPATIONS)
    location = rng.choice(locations)
    age = int(rng.gauss(38, 12))
    age = max(18, min(75, age))

    # Income: mapped loosely to segment index
    seg_income_scale = segment.get("traits", {}).get("income_level", 0.5)
    income_base = 20000 + seg_income_scale * 180000
    income = max(8000, int(rng.gauss(income_base, income_base * 0.3)))

    # Digital access: segment trait or domain default
    digital_base = segment.get("traits", {}).get("digital", 0.65)
    digital = max(0.1, min(1.0, rng.gauss(digital_base, 0.15)))

    # Traits: merge universal spec with segment spec
    traits = {}
    for trait_name, trait_cfg in universal_traits.items():
        mean = float(trait_cfg.get("mean", 0.5))
        spread = float(trait_cfg.get("spread", 0.2))
        traits[trait_name] = float(max(0.0, min(1.0, rng.gauss(mean, spread))))

    # Add segment-specific traits (override universal defaults)
    for k, v in segment.get("traits", {}).items():
        if k not in ("income_level", "digital"):
            traits[k] = float(max(0.0, min(1.0, rng.gauss(float(v), 0.12))))

    # Ensure core traits exist for engine compatibility
    for core_trait in ("risk", "price", "conformity", "trust_gov", "status",
                       "social_radius", "voice", "independence"):
        if core_trait not in traits:
            traits[core_trait] = round(rng.gauss(0.5, 0.2), 3)
            traits[core_trait] = max(0.0, min(1.0, traits[core_trait]))

    # Cognitive biases (required by engine)
    biases = {
        "status_quo": round(rng.gauss(0.5, 0.2), 3),
        "confirmation": round(rng.gauss(0.5, 0.2), 3),
        "loss_aversion": round(rng.gauss(0.55, 0.2), 3),
        "bandwagon": round(rng.gauss(0.45, 0.2), 3),
        "authority": round(rng.gauss(0.45, 0.2), 3),
        "availability": round(rng.gauss(0.5, 0.2), 3),
    }
    biases = {k: max(0.0, min(1.0, v)) for k, v in biases.items()}

    # Initial stance: drawn from segment traits
    openness = traits.get("openness", 0.5)
    risk_aversion = traits.get("risk", 0.5)
    stance = float(max(0.05, min(0.95, rng.gauss(openness * 0.6 + (1 - risk_aversion) * 0.4, 0.15))))

    agent_id = _stable_id(idx, seed)

    return {
        "id": agent_id,
        "name": name,
        "gender": gender,
        "age": age,
        "occupation": occupation,
        "occupation_id": occupation.lower().replace(" ", "_"),
        "household_income": income,
        "digital": round(digital, 3),
        "language": spec.get("language", "en"),
        "city": location,
        "state": location,                   # engine uses 'state' field
        "region": _region_from_location(location, domain),
        "tier": _tier_from_segment(segment),
        "segment_id": segment.get("label", "default").lower().replace(" ", "_"),
        "segment_label": segment.get("label", "Default"),
        "traits": {k: round(v, 3) for k, v in traits.items()},
        "biases": biases,
        "stance": round(stance, 3),
        "social_radius": round(traits.get("social_influence", 0.5) * 10, 1),
        "platform": _platform_from_digital(digital),
        "education": _education_from_traits(traits),
        # Unused India fields — set to neutral defaults so shared code doesn't crash
        "caste": "N/A",
        "religion": "N/A",
        "social_group": segment.get("label", "General"),
    }


def _stable_id(idx: int, seed: int) -> str:
    h = hashlib.md5(f"{seed}-{idx}".encode()).hexdigest()[:8]
    return f"u-{h}"


def _surname(rng: random.Random, domain: str) -> str:
    pools: dict[str, list[str]] = {
        "politics": ["Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson",
                     "Moore", "Taylor", "Anderson", "Thomas"],
        "finance": ["Chen", "Smith", "Kumar", "Park", "Patel", "Garcia",
                    "Nguyen", "Kim", "Okafor", "Hassan"],
        "technology": ["Zhang", "Singh", "Lee", "Müller", "Tanaka", "Santos",
                       "Okonkwo", "Petrov", "Nkosi", "Ramirez"],
    }
    pool = pools.get(domain, ["Smith", "Jones", "Williams", "Taylor", "Brown",
                               "Davies", "Evans", "Wilson", "Thomas", "Roberts",
                               "Kumar", "Singh", "Patel", "Chen", "Kim"])
    return rng.choice(pool)


def _region_from_location(location: str, domain: str) -> str:
    location_l = location.lower()
    if any(x in location_l for x in ("west", "california", "francisco", "seattle", "portland")):
        return "West"
    if any(x in location_l for x in ("east", "new york", "boston", "washington", "philadelphia")):
        return "East"
    if any(x in location_l for x in ("south", "atlanta", "houston", "miami", "dallas")):
        return "South"
    if any(x in location_l for x in ("north", "chicago", "detroit", "minneapolis")):
        return "North"
    return "Central"


def _tier_from_segment(segment: dict) -> int:
    """Map segments to tier 1-4 for engine compatibility."""
    label = segment.get("label", "").lower()
    if any(x in label for x in ("leader", "senior", "institutional", "elite", "early")):
        return 1
    if any(x in label for x in ("middle", "moderate", "mainstream", "retail")):
        return 2
    if any(x in label for x in ("worker", "passive", "laggard", "skeptic")):
        return 4
    return 3


def _platform_from_digital(digital: float) -> list[str]:
    if digital > 0.8:
        return ["Twitter/X", "LinkedIn", "Reddit", "YouTube", "Podcast"]
    if digital > 0.6:
        return ["YouTube", "Instagram", "Facebook", "News"]
    if digital > 0.4:
        return ["Facebook", "YouTube", "WhatsApp"]
    return ["TV", "Radio", "Word of mouth"]


def _education_from_traits(traits: dict) -> str:
    info_seeking = traits.get("information_seeking", 0.5)
    if info_seeking > 0.75:
        return "postgraduate"
    if info_seeking > 0.55:
        return "graduate"
    if info_seeking > 0.35:
        return "undergraduate"
    return "secondary"


def _default_segments_from_domain(domain: str) -> list[dict]:
    return [
        {"label": "Early adopters", "share": 0.15, "description": "Innovators", "traits": {"openness": 0.85, "risk": 0.25}},
        {"label": "Early majority", "share": 0.35, "description": "Early mainstream", "traits": {"openness": 0.6, "risk": 0.45}},
        {"label": "Late majority", "share": 0.35, "description": "Late mainstream", "traits": {"openness": 0.4, "risk": 0.6}},
        {"label": "Laggards", "share": 0.15, "description": "Skeptics", "traits": {"openness": 0.2, "risk": 0.8}},
    ]


def _india_tier_mix_from_spec(spec: dict) -> dict[int, float] | None:
    pop = spec.get("population_spec", {})
    segs = pop.get("segments") or []
    # If spec has explicit tier mix, use it
    if any(s.get("label", "").lower().startswith("tier") or "tier-" in s.get("label", "").lower() for s in segs):
        mix: dict[int, float] = {}
        for s in segs:
            label = s.get("label", "").lower()
            if "tier-1" in label or "metro" in label or "1" in label:
                mix[1] = s.get("share", 0.1)
            elif "tier-2" in label or "2" in label:
                mix[2] = s.get("share", 0.15)
            elif "tier-3" in label or "3" in label:
                mix[3] = s.get("share", 0.28)
            elif "tier-4" in label or "rural" in label or "4" in label:
                mix[4] = s.get("share", 0.47)
        if mix:
            return mix
    return None  # use personas.py defaults
