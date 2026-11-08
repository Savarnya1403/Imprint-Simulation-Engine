"""Synthetic-but-grounded agent generation for the Bharat simulator.

The population is a stratified sample, not a census. Every agent is built from
public distributions (state population, urbanisation, internet penetration,
occupation mix) plus explicit behavioural traits. Randomness is seeded so a
brief is reproducible.
"""
from __future__ import annotations

import math
import random
from typing import Any

from . import store

LANG = {
    "Andhra Pradesh": "Telugu", "Arunachal Pradesh": "Nyishi", "Assam": "Assamese",
    "Bihar": "Hindi", "Chhattisgarh": "Hindi", "Delhi": "Hindi", "Goa": "Konkani",
    "Gujarat": "Gujarati", "Haryana": "Haryanvi", "Himachal Pradesh": "Hindi",
    "Jammu & Kashmir": "Kashmiri", "Jharkhand": "Hindi", "Karnataka": "Kannada",
    "Kerala": "Malayalam", "Madhya Pradesh": "Hindi", "Maharashtra": "Marathi",
    "Manipur": "Meitei", "Meghalaya": "Khasi", "Mizoram": "Mizo", "Nagaland": "Ao",
    "Odisha": "Odia", "Punjab": "Punjabi", "Rajasthan": "Rajasthani", "Sikkim": "Nepali",
    "Tamil Nadu": "Tamil", "Telangana": "Telugu", "Tripura": "Bengali",
    "Uttar Pradesh": "Hindi", "Uttarakhand": "Hindi", "West Bengal": "Bengali",
    "Chandigarh": "Punjabi", "Puducherry": "Tamil", "Andaman & Nicobar Island": "Bengali",
    "Ladakh": "Ladakhi", "Dadara & Nagar Havelli": "Gujarati", "Lakshadweep": "Malayalam",
}

# Rough state-level religious composition (Census 2011 / Pew 2021 estimates).
# Used only to model in-group trust, never to assign values to individuals.
RELIGION = {
    "Punjab": [("Sikh", .58), ("Hindu", .38), ("Muslim", .02), ("Christian", .01)],
    "Jammu & Kashmir": [("Muslim", .68), ("Hindu", .28), ("Sikh", .02), ("Christian", .01)],
    "Ladakh": [("Buddhist", .40), ("Muslim", .46), ("Hindu", .12)],
    "Lakshadweep": [("Muslim", .97), ("Hindu", .02)],
    "Meghalaya": [("Christian", .75), ("Hindu", .12), ("Muslim", .04)],
    "Mizoram": [("Christian", .87), ("Buddhist", .08), ("Hindu", .03)],
    "Nagaland": [("Christian", .88), ("Hindu", .09)],
    "Manipur": [("Hindu", .41), ("Christian", .41), ("Muslim", .09)],
    "Arunachal Pradesh": [("Christian", .30), ("Hindu", .29), ("Buddhist", .12), ("Other", .29)],
    "Kerala": [("Hindu", .55), ("Muslim", .27), ("Christian", .18)],
    "Assam": [("Hindu", .61), ("Muslim", .34), ("Christian", .04)],
    "West Bengal": [("Hindu", .70), ("Muslim", .27), ("Christian", .01)],
    "Goa": [("Hindu", .66), ("Christian", .25), ("Muslim", .08)],
    "Andaman & Nicobar Island": [("Hindu", .69), ("Christian", .21), ("Muslim", .09)],
}
DEFAULT_RELIGION = [("Hindu", .79), ("Muslim", .14), ("Christian", .02), ("Sikh", .02), ("Buddhist", .01), ("Jain", .01), ("Other", .01)]

# Broad social-group mix. Structural, not essentialist.
CASTE = {
    "Punjab": [("General", .35), ("OBC", .25), ("SC", .32), ("ST", .01), ("Other", .07)],
    "Uttar Pradesh": [("General", .22), ("OBC", .40), ("SC", .21), ("ST", .01), ("Other", .16)],
    "Bihar": [("General", .16), ("OBC", .43), ("SC", .16), ("ST", .01), ("Other", .24)],
    "Tamil Nadu": [("General", .20), ("OBC", .50), ("SC", .20), ("ST", .01), ("Other", .09)],
    "Kerala": [("General", .25), ("OBC", .45), ("SC", .10), ("ST", .02), ("Other", .18)],
    "West Bengal": [("General", .25), ("OBC", .35), ("SC", .23), ("ST", .06), ("Other", .11)],
    "Odisha": [("General", .20), ("OBC", .40), ("SC", .17), ("ST", .23)],
    "Madhya Pradesh": [("General", .20), ("OBC", .42), ("SC", .16), ("ST", .21), ("Other", .01)],
    "Chhattisgarh": [("General", .18), ("OBC", .40), ("SC", .13), ("ST", .30)],
    "Jharkhand": [("General", .16), ("OBC", .35), ("SC", .13), ("ST", .36)],
    "Rajasthan": [("General", .25), ("OBC", .40), ("SC", .18), ("ST", .13), ("Other", .04)],
    "Maharashtra": [("General", .25), ("OBC", .35), ("SC", .13), ("ST", .10), ("Other", .17)],
    "Gujarat": [("General", .25), ("OBC", .40), ("SC", .07), ("ST", .15), ("Other", .13)],
    "Karnataka": [("General", .22), ("OBC", .42), ("SC", .18), ("ST", .07), ("Other", .11)],
    "Andhra Pradesh": [("General", .22), ("OBC", .48), ("SC", .17), ("ST", .06), ("Other", .07)],
    "Telangana": [("General", .22), ("OBC", .48), ("SC", .17), ("ST", .07), ("Other", .06)],
    "Assam": [("General", .30), ("OBC", .30), ("SC", .10), ("ST", .13), ("Other", .17)],
    "Meghalaya": [("General", .04), ("OBC", .02), ("SC", .01), ("ST", .86), ("Other", .07)],
    "Nagaland": [("ST", .86), ("Other", .14)],
    "Mizoram": [("ST", .94), ("Other", .06)],
    "Manipur": [("ST", .34), ("OBC", .25), ("SC", .12), ("General", .27), ("Other", .02)],
}
DEFAULT_CASTE = [("General", .25), ("OBC", .41), ("SC", .17), ("ST", .09), ("Other", .08)]

PLATFORMS = {
    1: ["X", "Instagram", "LinkedIn", "YouTube", "WhatsApp", "Reddit", "News"],
    2: ["YouTube", "WhatsApp", "Instagram", "Facebook", "ShareChat", "News"],
    3: ["YouTube", "WhatsApp", "ShareChat", "Facebook", "TV", "News"],
    4: ["WhatsApp", "YouTube", "ShareChat", "TV", "Radio", "Word of mouth"],
}

ATTIRES = {
    "female": ["saree", "salwar", "kurta", "saree_young", "hoodie", "uniform", "burqa"],
    "male": ["kurta", "shirt", "shirt", "hoodie", "uniform", "turban", "jacket"],
}
ACCESSORIES = ["bag", "phone", "dupatta", "helmet", "none", "none", "spectacles", "child"]

# ---------------------------------------------------------------------------
# Diversity axes (48 occupations × ideology × thought × class × education
# × personality × settlement). All are modelled as structural context with
# small, explicit effects on trust / risk / conformity — never as claims
# about what any individual or community believes. Priors are illustrative
# and anchored to public distributions:
#  - religion / caste: Census 2011 + Pew (see RELIGION / CASTE above)
#  - education: Census literacy + UDISE / AISHE attainment
#  - economic band: HCES MPCE + NITI distributions (household-income proxy)
#  - ideology: Lokniti-CSDS National Election & Society Surveys (broad
#    value orientations, not vote intent); used only to vary distrust
#    in media vs institutions.
#  - personality (Big Five): McCrae & Costa (1987) NEO dimensions,
#    derived from the archetype traits below so they stay auditable.
# ---------------------------------------------------------------------------

SETTLEMENT = {1: "Metro core", 2: "Tier-2 hub", 3: "Small town", 4: "Village / peri-urban"}
SETTLEMENT_UR = {1: "Urban", 2: "Urban", 3: "Semi-urban", 4: "Rural"}

# Broad orientation priors (not vote choice). Weights are nudged by region,
# age and education; the nudge is deliberately small.
IDEOLOGY_BASE = [("Progressive", .24), ("Moderate", .40), ("Traditional", .24), ("Nationalist", .12)]
IDEOLOGY_REGION_ADJ = {
    "north": {"Traditional": .06, "Nationalist": .03, "Progressive": -.05},
    "south": {"Progressive": .06, "Traditional": -.04},
    "west": {"Moderate": .04},
    "east": {"Traditional": .04},
    "central": {"Traditional": .02, "Moderate": .02},
    "northeast": {"Progressive": .02, "Moderate": .03},
}
IDEOLOGY_EFFECT = {
    "Progressive": {"trust_media": .04, "trust_gov": -.02},
    "Moderate": {"trust_media": .01, "trust_gov": .01},
    "Traditional": {"trust_gov": .03, "trust_media": -.02, "conformity": .03},
    "Nationalist": {"trust_gov": .05, "trust_media": -.03, "status": .02},
}
THOUGHT_PROCESS_EFFECT = {
    "Analytical": {"risk": -.02, "patience": .02},
    "Deliberative": {"patience": .02},
    "Intuitive": {"optimism": .02, "risk": .02},
    "Heuristic-driven": {"conformity": .03},
}


def _age_band(age: int) -> str:
    if age < 31:
        return "Young adult (18-30)"
    if age <= 50:
        return "Prime (31-50)"
    return "Older (51+)"


def _economic_band(household_income: float) -> str:
    if household_income < 20000:
        return "Economically weaker (EWS)"
    if household_income < 45000:
        return "Lower-middle (LIG)"
    if household_income < 100000:
        return "Middle (MIG)"
    if household_income < 250000:
        return "Upper-middle (HIG)"
    return "Affluent"


def _education_band(edu_score: float) -> str:
    if edu_score < 0.30:
        return "No formal schooling"
    if edu_score < 0.44:
        return "Primary"
    if edu_score < 0.58:
        return "Secondary"
    if edu_score < 0.73:
        return "Higher secondary"
    if edu_score < 0.88:
        return "Graduate"
    return "Postgraduate / Professional"


def _need_for_cognition(traits: dict) -> float:
    return traits["education"] * 0.55 + (1 - traits["risk"]) * 0.25 + traits["patience"] * 0.20


def _thought_process(traits: dict, rng: random.Random) -> str:
    nfc = _need_for_cognition(traits) + rng.gauss(0, 0.04)
    if nfc >= 0.62:
        return "Analytical"
    if nfc >= 0.50:
        return "Deliberative"
    if nfc >= 0.38:
        return "Intuitive"
    return "Heuristic-driven"


def _ideology(rng: random.Random, region: str, age: int, edu: float, tier: int) -> str:
    adj = dict(IDEOLOGY_REGION_ADJ.get(region, {}))
    # Mild structural nudges; kept small so no group is caricatured.
    if edu >= 0.73:
        adj["Progressive"] = adj.get("Progressive", 0) + 0.05
        adj["Moderate"] = adj.get("Moderate", 0) + 0.03
        adj["Traditional"] = adj.get("Traditional", 0) - 0.05
    elif edu < 0.44:
        adj["Traditional"] = adj.get("Traditional", 0) + 0.05
    if age >= 51:
        adj["Traditional"] = adj.get("Traditional", 0) + 0.04
    elif age < 31:
        adj["Progressive"] = adj.get("Progressive", 0) + 0.03
    if tier == 1:
        adj["Progressive"] = adj.get("Progressive", 0) + 0.03
    pairs = [(label, max(0.02, w + adj.get(label, 0))) for label, w in IDEOLOGY_BASE]
    return weighted_choice(rng, pairs)


def _personality(traits: dict, rng: random.Random) -> dict:
    o = clamp(traits["digital"] * 0.55 + traits["risk"] * 0.25 + traits["optimism"] * 0.20 + rng.gauss(0, 0.08))
    c = clamp(traits["patience"] * 0.50 + traits["education"] * 0.30 + (1 - traits["fatalism"]) * 0.20 + rng.gauss(0, 0.08))
    e = clamp(traits["social_radius"] * 0.45 + traits["voice"] * 0.30 + traits["optimism"] * 0.25 + rng.gauss(0, 0.08))
    a = clamp(traits["conformity"] * 0.50 + traits["patience"] * 0.30 + traits["trust_gov"] * 0.20 + rng.gauss(0, 0.08))
    n = clamp((1 - traits["patience"]) * 0.40 + traits["fatalism"] * 0.30 + (1 - traits["risk"]) * 0.30 + rng.gauss(0, 0.08))
    scores = {
        "Explorer": o * 0.6 + (1 - n) * 0.4,
        "Guardian": c * 0.6 + a * 0.4,
        "Achiever": e * 0.6 + c * 0.4,
        "Caregiver": a * 0.7 + e * 0.3,
        "Creator": o * 0.55 + e * 0.45,
        "Skeptic": n * 0.6 + (1 - a) * 0.4,
    }
    cluster = max(scores, key=scores.get)
    return {
        "openness": round(o, 3),
        "conscientiousness": round(c, 3),
        "extraversion": round(e, 3),
        "agreeableness": round(a, 3),
        "neuroticism": round(n, 3),
        "cluster": cluster,
    }


def weighted_choice(rng: random.Random, pairs):
    total = sum(w for _, w in pairs)
    r = rng.random() * total
    acc = 0
    for value, w in pairs:
        acc += w
        if r <= acc:
            return value
    return pairs[-1][0]


def clamp(x, lo=0.01, hi=0.99):
    return max(lo, min(hi, x))


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def build_agent(idx: int, rng: random.Random, tier_dist: dict[int, float], topic: dict, focus_state: str | None = None,
                used_names: set[str] | None = None) -> dict[str, Any]:
    tier = weighted_choice(rng, list(tier_dist.items()))
    states = store.states()
    if focus_state:
        candidates = [s for s in states if s["name"] == focus_state and any(c["tier"] == tier for c in s["cities"])]
        if candidates:
            state = candidates[0]
        else:
            candidates = [s for s in states if s["name"] == focus_state]
            state = candidates[0] if candidates else None
    else:
        state = None
    if state is None:
        city_pool = []
        for s in states:
            cities = [c for c in s["cities"] if c["tier"] == tier]
            if cities:
                city_pool.append((s, cities))
        # Larger states and more urban states get more weight
        weights = [(s, cs, s["population_m"] * (1 + 0.4 * s["urban_pct"] / 100)) for s, cs in city_pool]
        total = sum(w for _, _, w in weights)
        r = rng.random() * total
        upto = 0
        for s, cs, w in weights:
            upto += w
            if r <= upto:
                state = s
                break
        if state is None:
            state = city_pool[-1][0]
    cities = [c for c in state["cities"] if c["tier"] == tier] or state["cities"]
    city = rng.choice(cities)
    tier = city["tier"]
    region = state["region"]

    # occupation conditioned on tier
    arch_pool = [(a, {int(k): v for k, v in a["tiers"].items()}.get(tier, 0)) for a in store.archetypes()]
    arch_pool = [(a, w) for a, w in arch_pool if w > 0]
    arch = weighted_choice(rng, arch_pool)
    traits = {k: clamp(arch[k] + rng.gauss(0, 0.07)) for k in ["digital", "risk", "patience", "conformity", "status", "price", "jugaad", "fatalism", "optimism", "trust_gov", "trust_media", "education", "social_radius", "voice"]}

    # tier + region modifiers (small, additive)
    tier_mod = {1: dict(digital=.06, risk=.04, patience=.02, conformity=-.04, status=.04, price=-.06, fatalism=-.06, optimism=.04),
                2: dict(digital=.02, risk=.00, patience=.01, conformity=.00, status=.02, price=.00, fatalism=-.01, optimism=.01),
                3: dict(digital=-.03, risk=-.02, patience=.00, conformity=.02, status=-.01, price=.03, fatalism=.03, optimism=-.01),
                4: dict(digital=-.10, risk=-.03, patience=-.02, conformity=.05, status=-.03, price=.06, fatalism=.07, optimism=-.03)}[tier]
    region_mod = {"north": dict(status=.03, price=.02, trust_gov=.01),
                  "south": dict(education=.02, patience=.01, digital=.02, price=-.01),
                  "west": dict(risk=.03, digital=.02, price=-.01),
                  "east": dict(price=.03, trust_gov=-.01, fatalism=.02),
                  "central": dict(price=.03, fatalism=.03),
                  "northeast": dict(social_radius=.04, digital=-.03, trust_gov=.01)}[region]
    for k, v in {**tier_mod, **region_mod}.items():
        traits[k] = clamp(traits[k] + v)

    digital = clamp(traits["digital"] * .7 + state["internet_pct"] / 100 * .3 + rng.gauss(0, .03))
    age = {
        "student": rng.randint(16, 24), "jobseeker": rng.randint(21, 31),
        "retired": rng.randint(58, 76), "metro_it": rng.randint(23, 45),
        "founder": rng.randint(26, 55), "doctor": rng.randint(28, 62),
        "call_center": rng.randint(20, 35), "priest": rng.randint(28, 70),
        "domestic_worker": rng.randint(24, 52), "truck_driver": rng.randint(24, 55),
        "barber_salon": rng.randint(20, 55), "pharma_rep": rng.randint(24, 45),
        "tutor_coach": rng.randint(22, 55), "security_guard": rng.randint(22, 55),
        "dairy_farmer": rng.randint(25, 60), "fisher_worker": rng.randint(22, 56),
        "powerloom_worker": rng.randint(20, 50), "hotel_owner": rng.randint(28, 58),
        "carpenter": rng.randint(22, 58), "online_reseller": rng.randint(20, 45),
        "farmer_fpo": rng.randint(26, 58),
    }.get(arch["id"], rng.randint(23, 60))
    if arch["id"] == "homemaker":
        age = rng.randint(24, 58)

    # gender is occupation-aware but not deterministic
    female_p = {"homemaker": .93, "asha": .86, "nurse_pharmacist": .72, "teacher": .58,
                "student": .49, "jobseeker": .47, "metro_it": .38, "doctor": .40,
                "farmer": .28, "agri_labour": .40, "gig_rider": .08,
                "auto_driver": .03, "erickshaw_driver": .03, "factory_worker": .30,
                "kirana": .35, "street_vendor": .38, "tailor_beauty": .72,
                "influencer": .52, "journalist": .42, "ward_politician": .22,
                "police": .16, "bank_agent": .30, "migrant_worker": .18,
                "tea_stall": .30, "electrician": .04, "cable_operator": .12,
                "ngo_worker": .55, "salesperson": .28, "corporate_manager": .38,
                "govt_employee": .34, "artisan": .48, "retired": .42,
                # 15 added occupations (PLFS-consistent gender shares)
                "domestic_worker": .88, "truck_driver": .02, "barber_salon": .18,
                "pharma_rep": .30, "tutor_coach": .46, "priest": .04,
                "security_guard": .06, "dairy_farmer": .30, "fisher_worker": .32,
                "powerloom_worker": .36, "call_center": .42, "hotel_owner": .24,
                "carpenter": .05, "online_reseller": .54, "farmer_fpo": .22}.get(arch["id"], .48)
    gender = "female" if rng.random() < female_p else "male"

    # names: draw without replacement where possible so a crowd of 240 citizens
    # does not contain three people with the same name on the same street.
    region_names = store.names().get(region) or store.names()["north"]
    for _ in range(60):
        first = rng.choice(region_names[gender])
        last = rng.choice(region_names["last"])
        if last in ("Kaur", "Gill", "Sandhu") and gender == "male":
            last = rng.choice(["Singh", "Gill", "Sandhu"])
        if last in ("Singh",) and gender == "female" and rng.random() < .6:
            last = "Kaur"
        name = f"{first} {last}"
        if used_names is None or name not in used_names:
            break
    if used_names is not None:
        used_names.add(name)

    # income
    lo, hi = arch["income"]
    base = math.sqrt(max(1, lo) * max(1, hi))
    nsdp_factor = clamp((state["nsdp_pc"] / 200000) ** 0.35, .62, 1.45)
    tier_factor = {1: 1.18, 2: 1.0, 3: .82, 4: .66}[tier]
    income = base * nsdp_factor * tier_factor * math.exp(rng.gauss(0, .32))
    if arch["id"] in ("student", "jobseeker", "homemaker"):
        income *= rng.uniform(.18, .55)
    income = max(2500, round(income / 500) * 500)
    household_income = max(income * rng.uniform(1.7, 2.4), {1: 95000, 2: 48000, 3: 29000, 4: 16000}[tier] * math.exp(rng.gauss(0, .3)))
    household_size = rng.choices([2, 3, 4, 5, 6, 7], [8, 18, 30, 25, 13, 6])[0]

    religion = weighted_choice(rng, RELIGION.get(state["name"], DEFAULT_RELIGION))
    caste = weighted_choice(rng, CASTE.get(state["name"], DEFAULT_CASTE))
    lang = LANG.get(state["name"], "Hindi")

    # --- Diversity axes: ideology, thought, class, schooling, personality ---
    # Derived here, before biases/stance, so their small effects flow into
    # the decision function. All are structural context, not identity claims.
    thought = _thought_process(traits, rng)
    ideology = _ideology(rng, region, age, traits["education"], tier)
    for k, v in THOUGHT_PROCESS_EFFECT.get(thought, {}).items():
        traits[k] = clamp(traits[k] + v)
    for k, v in IDEOLOGY_EFFECT.get(ideology, {}).items():
        traits[k] = clamp(traits[k] + v)
    personality = _personality(traits, rng)
    if personality["neuroticism"] > 0.65:
        traits["risk"] = clamp(traits["risk"] - 0.03)
    if personality["openness"] > 0.65:
        traits["risk"] = clamp(traits["risk"] + 0.02)
    economic = _economic_band(household_income)
    if economic.startswith("Economically weaker"):
        traits["price"] = clamp(traits["price"] + 0.04)
    elif economic == "Affluent":
        traits["price"] = clamp(traits["price"] - 0.03)
    edu_band = _education_band(traits["education"])
    settlement = SETTLEMENT[tier]
    settlement_ur = SETTLEMENT_UR[tier]
    age_band = _age_band(age)

    english = sigmoid((traits["education"] - .58) * 3.2 + (tier == 1) * .9 - (age > 40) * .2 + rng.gauss(0, .25))

    # media diet
    base_media = PLATFORMS[tier][:]
    if gender == "female":
        base_media = [p for p in base_media if p != "X"] + (["Instagram"] if tier <= 2 else ["ShareChat"])
    if age < 24:
        base_media += ["Instagram", "YouTube"]
    if age > 55:
        base_media += ["TV", "WhatsApp"]
    media = list(dict.fromkeys(base_media))

    biases = {}
    flat = {"risk": traits["risk"], "price": traits["price"], "conformity": traits["conformity"],
            "social_radius": traits["social_radius"], "trust_gov": traits["trust_gov"],
            "trust_media": traits["trust_media"], "status": traits["status"],
            "fatalism": traits["fatalism"], "optimism": traits["optimism"],
            "education": traits["education"]}
    for b in store.biases():
        base_b = b["tiers"][str(tier)] if str(tier) in b["tiers"] else b["tiers"][tier]
        modifier = 0
        for tr, coef in b["traits"].items():
            modifier += coef * (flat.get(tr, .5) - .5)
        score = clamp(base_b * (1 + .45 * modifier) * (1 + rng.gauss(0, .10)))
        biases[b["id"]] = round(score, 3)

    # topic-specific starting position
    tier_shift = topic.get("tier_shift", {}).get(tier, 0)
    occ_shift = topic.get("occupation_shift", {}).get(arch["id"], 0)
    reg_shift = topic.get("region_shift", {}).get(region, 0)
    # Stance is centred on ambivalence, not on enthusiasm. The topic's structural
    # shifts and the agent's own traits decide which side of 0.5 they start on.
    starting = tier_shift * 1.15 + occ_shift * 1.35 + reg_shift * .75
    starting += (traits["optimism"] - .5) * .42 + (traits["risk"] - .5) * .18 + (traits["status"] - .5) * .20
    starting += (traits["price"] - .5) * -.30 + (traits["fatalism"] - .5) * -.26
    starting += rng.gauss(0, .34)
    stance = clamp(.5 + .5 * math.tanh(starting * .9), .04, .96)
    aware = clamp(topic.get("baseline_awareness", .5) + (digital - .5) * .3 + rng.gauss(0, .08), .03, .98)
    if rng.random() < .06:
        aware = clamp(aware * .4, .02, .5)

    # avatar look
    attire = rng.choice(ATTIRES[gender])
    if state["name"] in ("Punjab", "Haryana", "Delhi") and gender == "male" and rng.random() < .18:
        attire = "turban"
    if region == "south" and gender == "female" and rng.random() < .55:
        attire = "saree"
    if arch["id"] == "gig_rider":
        attire = "jacket"
    if arch["id"] == "student" and rng.random() < .4:
        attire = "uniform"
    accessory = rng.choice(ACCESSORIES)
    if arch["id"] == "gig_rider":
        accessory = "helmet"
    elif arch["id"] == "student":
        accessory = "bag"
    elif arch["id"] == "farmer":
        accessory = "none"
    elif arch["id"] == "homemaker" and rng.random() < .6:
        accessory = "dupatta"
    look = dict(variant=rng.randint(0, 19), attire=attire, accessory=accessory, hair=rng.choice(["short", "long", "bun", "curly", "turban", "bald"]))
    if attire == "turban":
        look["hair"] = "turban"
    if gender == "male" and age > 45 and rng.random() < .3:
        look["hair"] = "bald"

    bio = f"{arch['label']} in {city['name']}, {state['name']}. {arch['quirk']}"
    handle = f"{first.lower()}{last.lower()[:4]}{rng.randint(10, 99)}"
    quote = rng.choice([
        "Paisa vasool hona chahiye, bas.",
        "Pehle istemal karo, phir bharosa karo.",
        "Mera kaam bolta hai.",
        "Dekha jayega.",
        "If it works, I'll tell ten people. If it fails, a hundred.",
        "Service network is the real product.",
        "Price is what you pay, trust is what you keep.",
        "Metro logic doesn't always survive the district.",
        "My family builds the budget, I execute it.",
        "I don't need a discount. I need it to not fail.",
    ])

    return {
        "id": f"a{idx:04d}",
        "name": name,
        "handle": handle,
        "age": age,
        "age_band": age_band,
        "gender": gender,
        "state": state["name"],
        "region": region,
        "city": city["name"],
        "tier": tier,
        "settlement": settlement,
        "settlement_ur": settlement_ur,
        "language": lang,
        "english": round(english, 3),
        "occupation": arch["label"],
        "occupation_id": arch["id"],
        "archetype_short": arch["short"],
        "category": arch["category"],
        "income_monthly": income,
        "household_income": round(household_income / 500) * 500,
        "household_size": household_size,
        "economic_status": economic,
        "religion": religion,
        "caste_group": caste,
        "ideology": ideology,
        "thought_process": thought,
        "education_band": edu_band,
        "education": round(traits["education"], 3),
        "digital": round(digital, 3),
        "personality": personality,
        "personality_cluster": personality["cluster"],
        # Backwards-compatible flat copies for segmentation / UI filters.
        "big5_openness": personality["openness"],
        "big5_conscientiousness": personality["conscientiousness"],
        "big5_extraversion": personality["extraversion"],
        "big5_agreeableness": personality["agreeableness"],
        "big5_neuroticism": personality["neuroticism"],
        "traits": {k: round(v, 3) for k, v in traits.items()},
        "biases": biases,
        "media": media,
        "awareness": round(aware, 3),
        "stance": round(stance, 3),
        "adopted": False,
        "adopt_day": None,
        "rejected": False,
        "rejection_reason": None,
        "intent": 0.0,
        "look": look,
        "bio": bio,
        "quote": quote,
        "aspiration": arch["aspiration"],
        "fears": arch["fears"],
        "values": arch["values"],
        "quirks": arch["quirk"],
        "topic_start": round(starting, 3),
    }


def build_population(n: int, seed: int, tier_mix: dict[int, float] | None, topic: dict, focus_state: str | None = None) -> list[dict]:
    rng = random.Random(seed)
    if not tier_mix:
        tier_mix = {1: .10, 2: .15, 3: .28, 4: .47}
    total = sum(tier_mix.values())
    tier_dist = {int(k): v / total for k, v in tier_mix.items() if v > 0}
    if not tier_dist:
        tier_dist = {1: .10, 2: .15, 3: .28, 4: .47}
    used_names: set[str] = set()
    agents = [build_agent(i, rng, tier_dist, topic, focus_state, used_names) for i in range(n)]
    # ensure each tier is represented when requested
    for t in tier_dist:
        if not any(a["tier"] == t for a in agents):
            agents[t % len(agents)] = build_agent(10000 + t, rng, {t: 1.0}, topic, focus_state, used_names)
    return agents
