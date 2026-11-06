"""
India Deep Knowledge Layer — Imprint Bharat Simulation Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Encodes culturally-grounded, evidence-based data about Indian consumers.
Sources: NITI Aayog India@2047, NFHS-5, IHDS-II, CMIE CPHS, Kantar ICUBE,
         NSSO 68th Round, Nielsen India, BCG India Consumer Report 2024,
         Euromonitor India, SIAM, CEEW, TRAI, Jefferies India,
         RedseerStrategyConsultants, Blume Ventures Indus Valley Report.

All weights are 0-1 floats. 1 = extremely high, 0 = extremely low.
"""
from __future__ import annotations

from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# 1.  COMMUNITY COGNITIVE MAPS
#     25 distinct Indian socio-cultural communities with consumption biases.
# ═══════════════════════════════════════════════════════════════════════════

COMMUNITY_PROFILES: dict[str, dict[str, Any]] = {

    "gujarati_business": {
        "label": "Gujarati Business Family",
        "share_of_population": 0.025,
        "states": ["Gujarat", "Rajasthan", "Maharashtra", "Delhi"],
        "consumption_traits": {
            "savings_orientation": 0.82,
            "status_goods_reluctance": 0.60,   # prefer understated
            "gold_preference": 0.88,
            "brand_loyalty": 0.72,
            "price_negotiation": 0.92,
            "community_trust_network": 0.95,
            "external_brand_skepticism": 0.65,
            "quality_over_fashion": 0.78,
            "word_of_mouth_power": 0.90,
            "early_adopter_tech": 0.55,
        },
        "product_affinities": {
            "gold_jewelry": 0.92, "real_estate": 0.88, "insurance": 0.75,
            "mutual_funds": 0.70, "otts_family_plan": 0.60, "netflix": 0.42,
            "premium_smartphone": 0.65, "ev_scooter": 0.50,
        },
        "product_anti_affinities": {
            "visible_luxury_fashion": 0.28, "fast_fashion": 0.32,
            "single_malt_whisky": 0.30,
        },
        "trust_sources": ["community_elder", "family_male_head", "trader_network", "jain_temple_network"],
        "decision_style": "collective_family_consensus",
        "media_habits": ["gujarat_samachar", "divya_bhaskar", "whatsapp_business_groups", "business_channels"],
        "income_tier_typical": 2,
        "festive_spend_multiplier": 2.1,   # Diwali, Navratri
    },

    "marwari_trader": {
        "label": "Marwari Trading Household",
        "share_of_population": 0.015,
        "states": ["Rajasthan", "West Bengal", "Jharkhand", "Assam", "Maharashtra"],
        "consumption_traits": {
            "savings_orientation": 0.85,
            "risk_aversion": 0.72,
            "gold_preference": 0.90,
            "brand_loyalty": 0.80,
            "price_negotiation": 0.95,
            "community_trust_network": 0.97,
            "conspicuous_consumption": 0.35,  # low, wealth hidden
            "astrology_influence": 0.75,
            "auspicious_timing_purchase": 0.80,
        },
        "product_affinities": {
            "gold_jewelry": 0.95, "real_estate": 0.90, "fixed_deposit": 0.85,
            "religious_goods": 0.80, "wedding_spending": 0.90,
        },
        "trust_sources": ["seth_community", "family_elder", "astrologer", "temple_trust"],
        "decision_style": "patriarch_led_with_astro_timing",
        "income_tier_typical": 2,
        "festive_spend_multiplier": 2.5,
    },

    "punjabi_urban": {
        "label": "Punjabi Urban Household (Hindu/Sikh)",
        "share_of_population": 0.030,
        "states": ["Punjab", "Haryana", "Delhi", "Himachal Pradesh"],
        "consumption_traits": {
            "conspicuous_consumption": 0.88,  # very high — showy spending
            "brand_consciousness": 0.85,
            "hospitality_spend": 0.92,
            "vehicle_premium": 0.82,
            "food_spend": 0.80,
            "wedding_extravagance": 0.95,
            "savings_orientation": 0.42,
            "debt_comfort": 0.68,
        },
        "product_affinities": {
            "premium_suv": 0.90, "luxury_smartphone": 0.85, "gold_jewelry": 0.88,
            "premium_whisky": 0.78, "branded_clothing": 0.82, "gym_membership": 0.70,
            "netflix": 0.72, "air_conditioner": 0.88,
        },
        "trust_sources": ["neighbour_peer", "family_comparison", "social_media_influencer"],
        "decision_style": "status_led_peer_comparison",
        "income_tier_typical": 2,
        "festive_spend_multiplier": 2.8,
    },

    "south_indian_professional": {
        "label": "South Indian Educated Professional (Brahmin/Vellalar/Reddy/Nair)",
        "share_of_population": 0.040,
        "states": ["Tamil Nadu", "Karnataka", "Kerala", "Telangana", "Andhra Pradesh"],
        "consumption_traits": {
            "education_investment": 0.95,  # top priority
            "brand_quality_focus": 0.80,
            "savings_orientation": 0.72,
            "tech_adoption": 0.82,
            "frugality": 0.65,
            "conspicuous_consumption": 0.45,
            "career_planning": 0.90,
            "english_media_consumption": 0.78,
        },
        "product_affinities": {
            "laptop_premium": 0.88, "edtech": 0.85, "health_insurance": 0.80,
            "netflix_amazon": 0.78, "premium_smartphone": 0.82, "mutual_funds_sip": 0.75,
            "electric_vehicle": 0.65, "organic_food": 0.60,
        },
        "trust_sources": ["academic_credential", "expert_review", "family_elder", "colleague"],
        "decision_style": "research_heavy_rational",
        "income_tier_typical": 2,
        "festive_spend_multiplier": 1.6,
    },

    "bengali_bhadralok": {
        "label": "Bengali Middle-Class Intellectual (Bhadralok)",
        "share_of_population": 0.020,
        "states": ["West Bengal", "Assam", "Tripura"],
        "consumption_traits": {
            "cultural_spending": 0.88,  # books, music, art
            "food_indulgence": 0.82,
            "brand_consciousness": 0.52,
            "tech_skepticism": 0.58,
            "english_media": 0.75,
            "political_awareness": 0.90,
            "savings_orientation": 0.60,
            "conspicuous_consumption": 0.40,
        },
        "product_affinities": {
            "books_subscriptions": 0.90, "sweets_premium": 0.88, "fish_market": 0.92,
            "newspaper_multiple": 0.82, "travel_domestic": 0.72, "streaming_music": 0.70,
        },
        "trust_sources": ["newspaper_editorial", "academic", "neighborhood_adda"],
        "decision_style": "deliberative_consensus",
        "income_tier_typical": 3,
        "festive_spend_multiplier": 2.0,  # Durga Puja
    },

    "bihari_migrant": {
        "label": "Bihari / UP Migrant Worker",
        "share_of_population": 0.060,
        "states": ["Bihar", "Uttar Pradesh", "Jharkhand"],
        "consumption_traits": {
            "remittance_first": 0.90,  # sends money home
            "frugality": 0.80,
            "mobile_data_conscious": 0.72,
            "feature_phone_loyalty": 0.65,
            "aspirational_smartphone": 0.60,
            "caste_peer_influence": 0.82,
            "trust_formal_finance": 0.35,
            "gold_as_savings": 0.78,
        },
        "product_affinities": {
            "basic_smartphone": 0.68, "jio_recharge": 0.90, "dth_basic": 0.72,
            "cheap_tobacco": 0.55, "imitation_branded_goods": 0.60,
        },
        "trust_sources": ["caste_panchayat", "village_elder", "mobile_youtube_influencer"],
        "decision_style": "community_herd_frugal",
        "income_tier_typical": 4,
        "festive_spend_multiplier": 1.9,  # Chhath Puja
    },

    "obc_artisan": {
        "label": "OBC Artisan / Small Trader (Yadav, Kurmi, Patel, Jat)",
        "share_of_population": 0.100,
        "states": ["Uttar Pradesh", "Bihar", "Madhya Pradesh", "Rajasthan", "Haryana", "Gujarat"],
        "consumption_traits": {
            "aspirational_mobility": 0.75,
            "government_scheme_awareness": 0.80,
            "smartphone_upgrade_desire": 0.72,
            "caste_solidarity": 0.78,
            "price_sensitivity": 0.82,
            "trust_local_brand": 0.68,
            "land_investment": 0.85,
        },
        "product_affinities": {
            "mid_range_smartphone": 0.78, "two_wheeler": 0.82, "jio_fiber": 0.60,
            "pm_awas_home_loan": 0.75, "insurance_govt": 0.68, "dth_premium": 0.55,
        },
        "trust_sources": ["local_leader", "caste_network", "tv_ad_trustworthy_brand"],
        "decision_style": "aspirational_caste_peer",
        "income_tier_typical": 3,
        "festive_spend_multiplier": 2.0,
    },

    "dalit_urban": {
        "label": "Dalit Urban Professional / Aspirant",
        "share_of_population": 0.045,
        "states": ["Maharashtra", "Tamil Nadu", "Uttar Pradesh", "Punjab", "Telangana"],
        "consumption_traits": {
            "anti_caste_brand_preference": 0.72,  # avoid Brahmin-associated brands
            "government_job_aspiration": 0.88,
            "education_priority": 0.90,
            "distrust_traditional_finance": 0.70,
            "mobile_first": 0.80,
            "ambedkarite_identity": 0.75,
            "new_money_conspicuous": 0.65,
        },
        "product_affinities": {
            "coaching_classes": 0.88, "smartphone_good": 0.82, "bank_account": 0.80,
            "blue_collar_tools": 0.70, "tv_news": 0.72,
        },
        "trust_sources": ["ambedkarite_community", "government_scheme", "mobile_app"],
        "decision_style": "aspiration_identity_led",
        "income_tier_typical": 3,
        "festive_spend_multiplier": 1.5,
    },

    "muslim_urban": {
        "label": "Urban Muslim Middle Class",
        "share_of_population": 0.040,
        "states": ["Uttar Pradesh", "Maharashtra", "West Bengal", "Bihar", "Kerala", "Karnataka"],
        "consumption_traits": {
            "halal_product_preference": 0.90,
            "community_trust_network": 0.85,
            "gold_saving": 0.80,
            "real_estate_investment": 0.72,
            "distrust_mainstream_finance": 0.60,
            "religious_goods_spend": 0.82,
            "eid_festive_spike": 0.90,
            "digital_adoption": 0.65,
        },
        "product_affinities": {
            "halal_food_certified": 0.95, "gold_jewelry": 0.85, "attar_perfume": 0.78,
            "religious_books": 0.80, "biryani_restaurant": 0.88, "smartphone": 0.72,
        },
        "product_anti_affinities": {
            "pork_products": 0.00, "alcohol": 0.15, "hindu_branded_goods": 0.40,
        },
        "trust_sources": ["mosque_community", "family_elder", "maulvi"],
        "decision_style": "community_halal_led",
        "income_tier_typical": 3,
        "festive_spend_multiplier": 2.2,  # Eid
    },

    "kerala_christian": {
        "label": "Kerala Christian Household (Syrian / Latin)",
        "share_of_population": 0.012,
        "states": ["Kerala", "Goa", "Tamil Nadu"],
        "consumption_traits": {
            "education_investment": 0.92,
            "remittance_income": 0.78,  # Gulf connections
            "conspicuous_consumption": 0.65,
            "alcohol_normalisation": 0.72,
            "church_community_trust": 0.88,
            "real_estate_investment": 0.80,
            "western_fashion_affinity": 0.65,
        },
        "product_affinities": {
            "premium_smartphone": 0.82, "air_travel": 0.78, "wine_beer": 0.70,
            "foreign_goods": 0.68, "nursing_education": 0.90, "real_estate": 0.85,
        },
        "trust_sources": ["church_elder", "family_abroad", "local_newspaper"],
        "decision_style": "education_remittance_led",
        "income_tier_typical": 2,
        "festive_spend_multiplier": 2.0,
    },

    "tribal_jharkhand_odisha": {
        "label": "Tribal Household (Jharkhand / Odisha / MP / NE)",
        "share_of_population": 0.085,
        "states": ["Jharkhand", "Odisha", "Madhya Pradesh", "Chhattisgarh", "Assam"],
        "consumption_traits": {
            "cash_economy": 0.85,
            "formal_finance_exclusion": 0.80,
            "mobile_first_information": 0.65,
            "government_scheme_dependence": 0.78,
            "community_seasonal_spend": 0.72,
            "alcohol_local_brew": 0.60,
            "distrust_outsider_brands": 0.70,
        },
        "product_affinities": {
            "feature_phone": 0.68, "local_market_goods": 0.90, "govt_ration": 0.95,
            "mobile_recharge_low": 0.75,
        },
        "trust_sources": ["tribal_panchayat", "gram_pradhan", "church_if_christian"],
        "decision_style": "community_seasonal_barter",
        "income_tier_typical": 4,
        "festive_spend_multiplier": 1.6,
    },

    "urban_gen_z": {
        "label": "Urban Gen-Z (18-26, Metro/Tier-1)",
        "share_of_population": 0.055,
        "states": ["Delhi", "Maharashtra", "Karnataka", "Tamil Nadu", "Telangana"],
        "consumption_traits": {
            "digital_native": 0.98,
            "instagram_led_discovery": 0.90,
            "brand_cancel_culture": 0.72,
            "sustainability_signaling": 0.65,
            "experience_over_ownership": 0.70,
            "emi_comfort": 0.78,
            "identity_consumption": 0.82,
            "fast_fashion": 0.75,
        },
        "product_affinities": {
            "sneakers_premium": 0.85, "streaming_multiple": 0.88, "food_delivery": 0.90,
            "headphones_tws": 0.85, "gaming": 0.72, "quick_commerce": 0.80,
            "fast_fashion_online": 0.78, "coffee_cafes": 0.82,
        },
        "trust_sources": ["instagram_creator", "youtube_review", "peers", "reddit_india"],
        "decision_style": "social_proof_identity",
        "income_tier_typical": 2,
        "festive_spend_multiplier": 1.4,
    },

    "rural_farmer_hindi_belt": {
        "label": "Small Farmer Hindi Belt (< 2 hectares)",
        "share_of_population": 0.120,
        "states": ["Uttar Pradesh", "Bihar", "Madhya Pradesh", "Rajasthan", "Haryana"],
        "consumption_traits": {
            "income_volatility": 0.85,  # monsoon dependent
            "cash_preference": 0.88,
            "govt_scheme_reliance": 0.82,
            "msp_awareness": 0.72,
            "feature_phone_primary": 0.68,
            "tv_prime_time": 0.80,
            "brand_ad_trust": 0.72,  # TV ads highly trusted
            "astrology_timing": 0.68,
        },
        "product_affinities": {
            "fertiliser_input": 0.95, "dth_basic_channels": 0.78, "feature_phone": 0.80,
            "tractor_aspirational": 0.65, "pm_kisan": 0.90, "generic_medicine": 0.82,
        },
        "trust_sources": ["sarpanch", "msp_announcer", "tv_ad_star_endorser", "aasha_worker"],
        "decision_style": "income_volatility_trust_tv",
        "income_tier_typical": 4,
        "festive_spend_multiplier": 1.8,
    },

    "it_professional_metro": {
        "label": "IT Professional (Bangalore / Hyderabad / Pune / Chennai)",
        "share_of_population": 0.025,
        "states": ["Karnataka", "Telangana", "Maharashtra", "Tamil Nadu"],
        "consumption_traits": {
            "tech_early_adopter": 0.90,
            "convenience_premium": 0.85,
            "brand_global_preference": 0.80,
            "savings_sip": 0.78,
            "emi_comfort": 0.72,
            "work_life_balance_spend": 0.75,
            "urban_cosmopolitan": 0.85,
        },
        "product_affinities": {
            "flagship_smartphone": 0.90, "laptop_premium": 0.88, "food_delivery_premium": 0.82,
            "netflix_prime": 0.90, "mutual_fund_sip": 0.80, "electric_vehicle": 0.72,
            "gym_zumba": 0.70, "domestic_flights": 0.78,
        },
        "trust_sources": ["linkedin_peer", "product_hunt", "wirecutter_equivalent", "colleague"],
        "decision_style": "research_convenience_global",
        "income_tier_typical": 1,
        "festive_spend_multiplier": 1.5,
    },

    "lower_middle_urban": {
        "label": "Lower-Middle Urban Household (Shopkeeper / Clerk / Driver)",
        "share_of_population": 0.100,
        "states": ["All"],
        "consumption_traits": {
            "value_for_money": 0.90,
            "aspirational_upgrade": 0.72,
            "emi_first_time": 0.65,
            "brand_trust_jingle": 0.78,
            "mobile_data_frugal": 0.70,
            "school_fee_priority": 0.88,
            "single_tv_household": 0.75,
        },
        "product_affinities": {
            "affordable_smartphone": 0.80, "dth_package": 0.75, "two_wheeler": 0.70,
            "online_grocery": 0.55, "basic_insurance": 0.60,
        },
        "trust_sources": ["tv_celebrity_ad", "neighbour_word", "shopkeeper_recommendation"],
        "decision_style": "value_led_peer_validation",
        "income_tier_typical": 3,
        "festive_spend_multiplier": 1.9,
    },

    "nri_returnee": {
        "label": "NRI Returnee / Gulf Worker Family",
        "share_of_population": 0.008,
        "states": ["Kerala", "Punjab", "Gujarat", "Andhra Pradesh", "Telangana"],
        "consumption_traits": {
            "global_brand_preference": 0.85,
            "real_estate_investment": 0.90,
            "conspicuous_consumption": 0.75,
            "dollar_reference_pricing": 0.80,
            "tech_premium": 0.82,
            "remittance_home": 0.90,
        },
        "product_affinities": {
            "luxury_apartment": 0.90, "foreign_branded_goods": 0.85, "gold": 0.88,
            "premium_suv": 0.82, "visa_free_travel": 0.78,
        },
        "trust_sources": ["foreign_returned_peer", "newspaper_nri_edition", "family_elder"],
        "decision_style": "dollar_global_conspicuous",
        "income_tier_typical": 1,
        "festive_spend_multiplier": 2.5,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 2.  OCCUPATION PROFILES — 80+ occupations with income, digital, aspiration
# ═══════════════════════════════════════════════════════════════════════════

OCCUPATION_PROFILES: dict[str, dict[str, Any]] = {
    # ── Tier 1 — Metro / Global ──
    "software_engineer": {
        "label": "Software Engineer", "tier": 1,
        "income_monthly_inr": (80_000, 300_000), "digital": 0.98,
        "product_sensitivity": 0.30, "status_goods": 0.70,
        "community": ["it_professional_metro", "south_indian_professional"],
    },
    "startup_founder": {
        "label": "Startup Founder", "tier": 1,
        "income_monthly_inr": (50_000, 500_000), "digital": 0.99,
        "product_sensitivity": 0.25, "status_goods": 0.72,
        "community": ["it_professional_metro", "urban_gen_z"],
    },
    "doctor_specialist": {
        "label": "Specialist Doctor (private)", "tier": 1,
        "income_monthly_inr": (150_000, 600_000), "digital": 0.82,
        "product_sensitivity": 0.25, "status_goods": 0.78,
        "community": ["south_indian_professional", "lower_middle_urban"],
    },
    "ca_lawyer": {
        "label": "CA / Lawyer (urban)", "tier": 1,
        "income_monthly_inr": (60_000, 250_000), "digital": 0.78,
        "product_sensitivity": 0.35, "status_goods": 0.65,
        "community": ["gujarati_business", "marwari_trader"],
    },
    # ── Tier 2 — Urban Middle ──
    "govt_officer": {
        "label": "Government Officer (IAS/IPS/Class-I)", "tier": 2,
        "income_monthly_inr": (60_000, 200_000), "digital": 0.72,
        "product_sensitivity": 0.40, "status_goods": 0.60,
        "community": ["south_indian_professional", "obc_artisan"],
    },
    "teacher_private": {
        "label": "Private School Teacher", "tier": 2,
        "income_monthly_inr": (15_000, 45_000), "digital": 0.65,
        "product_sensitivity": 0.70, "status_goods": 0.42,
        "community": ["bengali_bhadralok", "lower_middle_urban"],
    },
    "small_business_owner": {
        "label": "Small Business Owner (kirana / retail)", "tier": 2,
        "income_monthly_inr": (25_000, 100_000), "digital": 0.68,
        "product_sensitivity": 0.65, "status_goods": 0.58,
        "community": ["gujarati_business", "obc_artisan"],
    },
    "sales_executive": {
        "label": "Sales Executive / BPO", "tier": 2,
        "income_monthly_inr": (20_000, 60_000), "digital": 0.80,
        "product_sensitivity": 0.72, "status_goods": 0.65,
        "community": ["lower_middle_urban", "urban_gen_z"],
    },
    # ── Tier 3 — Semi-urban / Small Town ──
    "auto_rickshaw_driver": {
        "label": "Auto / Cab Driver", "tier": 3,
        "income_monthly_inr": (12_000, 30_000), "digital": 0.72,
        "product_sensitivity": 0.85, "status_goods": 0.42,
        "community": ["bihari_migrant", "lower_middle_urban"],
    },
    "electrician_plumber": {
        "label": "Electrician / Plumber", "tier": 3,
        "income_monthly_inr": (15_000, 40_000), "digital": 0.60,
        "product_sensitivity": 0.78, "status_goods": 0.40,
        "community": ["obc_artisan", "lower_middle_urban"],
    },
    "nurse_asha": {
        "label": "Nurse / ASHA Worker", "tier": 3,
        "income_monthly_inr": (10_000, 35_000), "digital": 0.65,
        "product_sensitivity": 0.80, "status_goods": 0.35,
        "community": ["dalit_urban", "south_indian_professional"],
    },
    "daily_wage_construction": {
        "label": "Daily Wage Construction Worker", "tier": 4,
        "income_monthly_inr": (8_000, 18_000), "digital": 0.42,
        "product_sensitivity": 0.95, "status_goods": 0.30,
        "community": ["bihari_migrant", "tribal_jharkhand_odisha"],
    },
    "small_farmer": {
        "label": "Small / Marginal Farmer (< 2 ha)", "tier": 4,
        "income_monthly_inr": (5_000, 20_000), "digital": 0.38,
        "product_sensitivity": 0.92, "status_goods": 0.28,
        "community": ["rural_farmer_hindi_belt", "obc_artisan"],
    },
    "domestic_worker": {
        "label": "Domestic Worker / Ayah", "tier": 4,
        "income_monthly_inr": (6_000, 15_000), "digital": 0.40,
        "product_sensitivity": 0.95, "status_goods": 0.22,
        "community": ["dalit_urban", "bihari_migrant"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 3.  PREMIUM SIGNAL MATRIX
#     What makes a product/brand feel "posh" or "poor" in India.
# ═══════════════════════════════════════════════════════════════════════════

PREMIUM_SIGNALS: dict[str, dict[str, float]] = {
    # Colleges
    "iit": {"posh_score": 0.98, "income_signal": 0.90, "social_mobility": 0.95},
    "iim": {"posh_score": 0.97, "income_signal": 0.95, "social_mobility": 0.92},
    "dps_school": {"posh_score": 0.88, "income_signal": 0.85, "social_mobility": 0.70},
    "govt_school": {"posh_score": 0.20, "income_signal": 0.25, "social_mobility": 0.50},
    # Neighbourhoods
    "defence_colony_delhi": {"posh_score": 0.92, "income_signal": 0.88},
    "bandra_mumbai": {"posh_score": 0.95, "income_signal": 0.92},
    "koramangala_blr": {"posh_score": 0.88, "income_signal": 0.90},
    "dharavi_mumbai": {"posh_score": 0.08, "income_signal": 0.10},
    # Products
    "iphone": {"posh_score": 0.92, "aspirational": 0.95, "social_visibility": 0.95},
    "samsung_s_series": {"posh_score": 0.78, "aspirational": 0.80, "social_visibility": 0.82},
    "xiaomi_redmi": {"posh_score": 0.42, "aspirational": 0.55, "social_visibility": 0.48},
    "feature_phone": {"posh_score": 0.08, "aspirational": 0.15, "social_visibility": 0.12},
    "mahindra_thar": {"posh_score": 0.82, "aspirational": 0.90, "social_visibility": 0.88},
    "activa_scooter": {"posh_score": 0.52, "aspirational": 0.60, "social_visibility": 0.58},
    "hero_splendor": {"posh_score": 0.32, "aspirational": 0.42, "social_visibility": 0.38},
    # Clothing
    "branded_formal": {"posh_score": 0.72, "aspirational": 0.70, "social_visibility": 0.68},
    "unbranded_local": {"posh_score": 0.18, "aspirational": 0.22, "social_visibility": 0.15},
    "levis_jeans": {"posh_score": 0.70, "aspirational": 0.75, "social_visibility": 0.72},
    # Food
    "starbucks": {"posh_score": 0.88, "aspirational": 0.85, "social_visibility": 0.90},
    "chai_tapri": {"posh_score": 0.15, "aspirational": 0.20, "social_visibility": 0.18},
    "swiggy_zomato": {"posh_score": 0.65, "aspirational": 0.72, "social_visibility": 0.60},
}


# ═══════════════════════════════════════════════════════════════════════════
# 4.  FESTIVAL CALENDAR & SPENDING SPIKES
#     Month is 1-12. Multiplier applied to relevant product categories.
# ═══════════════════════════════════════════════════════════════════════════

FESTIVAL_CALENDAR: list[dict[str, Any]] = [
    {
        "name": "Makar Sankranti / Lohri / Pongal",
        "month": 1, "day_range": (12, 16),
        "regions": ["Punjab", "Haryana", "Tamil Nadu", "Gujarat"],
        "category_multipliers": {"sweets": 2.0, "new_clothes": 1.5, "electronics_gift": 1.3},
        "communities": ["punjabi_urban", "south_indian_professional", "gujarati_business"],
    },
    {
        "name": "Holi",
        "month": 3, "day_range": (10, 25),
        "regions": ["Uttar Pradesh", "Rajasthan", "Madhya Pradesh", "Bihar", "Delhi"],
        "category_multipliers": {"fmcg_colors": 3.0, "sweets": 2.2, "drinks": 1.8, "new_clothes": 1.6},
        "communities": ["obc_artisan", "rural_farmer_hindi_belt", "lower_middle_urban"],
    },
    {
        "name": "Eid ul-Fitr",
        "month_variable": True, "approximate_month": 4,
        "regions": ["Uttar Pradesh", "West Bengal", "Bihar", "Kerala", "Karnataka"],
        "category_multipliers": {"clothing_formal": 3.5, "sweets_bakery": 3.0, "gold_jewelry": 2.0, "smartphone_gift": 1.8},
        "communities": ["muslim_urban"],
    },
    {
        "name": "Onam",
        "month": 8, "day_range": (22, 31),
        "regions": ["Kerala"],
        "category_multipliers": {"new_clothes": 3.0, "gold": 2.5, "electronics": 2.0, "home_decor": 2.2},
        "communities": ["kerala_christian", "south_indian_professional"],
    },
    {
        "name": "Ganesh Chaturthi",
        "month": 9, "day_range": (1, 20),
        "regions": ["Maharashtra", "Goa", "Karnataka", "Andhra Pradesh"],
        "category_multipliers": {"sweets": 2.5, "decor": 3.0, "sound_system": 2.0, "clothes": 1.8},
        "communities": ["lower_middle_urban", "obc_artisan"],
    },
    {
        "name": "Navratri / Durga Puja",
        "month": 10, "day_range": (1, 24),
        "regions": ["Gujarat", "West Bengal", "Rajasthan", "Delhi"],
        "category_multipliers": {"new_clothes": 4.0, "gold": 2.8, "sweets": 2.5, "electronics": 1.8},
        "communities": ["gujarati_business", "marwari_trader", "bengali_bhadralok"],
    },
    {
        "name": "Diwali",
        "month": 10, "day_range": (20, 31),   # approximate
        "regions": ["All"],
        "category_multipliers": {
            "gold": 3.5, "electronics": 2.8, "smartphone": 2.5, "home_appliance": 2.6,
            "new_clothes": 3.0, "sweets": 3.5, "gifting": 4.0, "two_wheeler": 2.0,
        },
        "communities": ["All"],
        "note": "Single biggest consumer spending event in India.",
    },
    {
        "name": "Chhath Puja",
        "month": 11, "day_range": (1, 10),
        "regions": ["Bihar", "Jharkhand", "Uttar Pradesh", "Delhi"],
        "category_multipliers": {"new_clothes": 2.5, "puja_items": 4.0, "sweets": 2.0},
        "communities": ["bihari_migrant", "rural_farmer_hindi_belt"],
    },
    {
        "name": "Christmas",
        "month": 12, "day_range": (20, 31),
        "regions": ["Kerala", "Goa", "Tamil Nadu", "Delhi", "Mumbai"],
        "category_multipliers": {"new_clothes": 2.0, "electronics": 2.0, "wine_beer": 2.5, "restaurants": 2.5},
        "communities": ["kerala_christian", "urban_gen_z", "it_professional_metro"],
    },
    {
        "name": "Republic Day / Independence Day Sales",
        "month": 1, "day_range": (22, 28),
        "regions": ["All"],
        "category_multipliers": {"electronics_online": 2.5, "smartphone_online": 2.8, "fashion_online": 2.0},
        "communities": ["urban_gen_z", "it_professional_metro"],
        "note": "Flipkart / Amazon Republic Day sale. Dominant e-commerce event.",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# 5.  PRODUCT CATEGORY PERCEPTION MAP
#     How different tier/community combinations perceive product categories.
#     Keys: (tier, product_category) -> perception dict
# ═══════════════════════════════════════════════════════════════════════════

PRODUCT_PERCEPTION: dict[tuple, dict[str, float]] = {
    # Smartphones
    ("tier1", "flagship_smartphone"): {
        "desire": 0.90, "affordable": 0.85, "social_signal": 0.75, "trust": 0.90,
        "objection": "already have one", "objection_weight": 0.60,
    },
    ("tier2", "flagship_smartphone"): {
        "desire": 0.82, "affordable": 0.52, "social_signal": 0.88, "trust": 0.85,
        "objection": "too expensive", "objection_weight": 0.50,
        "emi_willingness": 0.72,
    },
    ("tier3", "flagship_smartphone"): {
        "desire": 0.72, "affordable": 0.28, "social_signal": 0.85, "trust": 0.78,
        "objection": "cant afford", "objection_weight": 0.70,
        "emi_willingness": 0.45,
    },
    ("tier4", "flagship_smartphone"): {
        "desire": 0.55, "affordable": 0.10, "social_signal": 0.80, "trust": 0.65,
        "objection": "not for us", "objection_weight": 0.85,
    },
    # EV Scooter
    ("tier1", "ev_scooter"): {
        "desire": 0.72, "affordable": 0.90, "social_signal": 0.60, "trust": 0.68,
        "objection": "range anxiety", "objection_weight": 0.42,
    },
    ("tier2", "ev_scooter"): {
        "desire": 0.65, "affordable": 0.52, "social_signal": 0.65, "trust": 0.55,
        "objection": "service trust", "objection_weight": 0.65,
        "emi_willingness": 0.60,
    },
    ("tier3", "ev_scooter"): {
        "desire": 0.50, "affordable": 0.32, "social_signal": 0.58, "trust": 0.40,
        "objection": "no service centre nearby", "objection_weight": 0.80,
    },
    ("tier4", "ev_scooter"): {
        "desire": 0.32, "affordable": 0.15, "social_signal": 0.45, "trust": 0.28,
        "objection": "petrol cheaper total", "objection_weight": 0.90,
    },
    # Netflix / OTT
    ("tier1", "netflix"): {
        "desire": 0.90, "affordable": 0.95, "social_signal": 0.65, "trust": 0.92,
        "objection": "already subscribed", "objection_weight": 0.55,
    },
    ("tier2", "netflix"): {
        "desire": 0.75, "affordable": 0.70, "social_signal": 0.72, "trust": 0.85,
        "objection": "JioCinema free", "objection_weight": 0.58,
    },
    ("tier3", "netflix"): {
        "desire": 0.55, "affordable": 0.42, "social_signal": 0.68, "trust": 0.72,
        "objection": "shared account / piracy", "objection_weight": 0.72,
    },
    ("tier4", "netflix"): {
        "desire": 0.32, "affordable": 0.18, "social_signal": 0.55, "trust": 0.60,
        "objection": "DTH cheaper", "objection_weight": 0.85,
    },
    # Protein Supplements
    ("tier1", "protein_supplement"): {
        "desire": 0.72, "affordable": 0.90, "social_signal": 0.68, "trust": 0.72,
        "objection": "already use", "objection_weight": 0.40,
    },
    ("tier2", "protein_supplement"): {
        "desire": 0.60, "affordable": 0.60, "social_signal": 0.65, "trust": 0.60,
        "objection": "steroids fear", "objection_weight": 0.55,
    },
    ("tier3", "protein_supplement"): {
        "desire": 0.42, "affordable": 0.35, "social_signal": 0.55, "trust": 0.45,
        "objection": "daal protein enough", "objection_weight": 0.70,
    },
    ("tier4", "protein_supplement"): {
        "desire": 0.20, "affordable": 0.12, "social_signal": 0.38, "trust": 0.30,
        "objection": "not for village", "objection_weight": 0.90,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 6.  GEOGRAPHIC SUPPLY CONSTRAINTS
#     What is simply unavailable or hard-to-find outside metros.
# ═══════════════════════════════════════════════════════════════════════════

SUPPLY_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "ev_service_centre": {
        "metro_tier1": 0.95,    # easily available
        "urban_tier2": 0.62,
        "semi_urban_tier3": 0.28,
        "rural_tier4": 0.05,
        "note": "Ola, Ather, TVS service density collapses outside top 50 cities.",
        "source": "CEEW Electric Mobility Report 2024",
    },
    "fast_internet_broadband": {
        "metro_tier1": 0.98,
        "urban_tier2": 0.82,
        "semi_urban_tier3": 0.55,
        "rural_tier4": 0.28,
        "note": "BharatNet Phase 2 covers 1.9L gram panchayats but last-mile is weak.",
        "source": "TRAI Report Mar 2024",
    },
    "organised_retail": {
        "metro_tier1": 0.98,
        "urban_tier2": 0.70,
        "semi_urban_tier3": 0.38,
        "rural_tier4": 0.08,
    },
    "quick_commerce_10min": {
        "metro_tier1": 0.88,
        "urban_tier2": 0.42,
        "semi_urban_tier3": 0.08,
        "rural_tier4": 0.01,
        "note": "Blinkit / Zepto / Swiggy Instamart limited to 50 cities as of 2024.",
    },
    "bank_branch_atm": {
        "metro_tier1": 0.99,
        "urban_tier2": 0.90,
        "semi_urban_tier3": 0.72,
        "rural_tier4": 0.48,
        "note": "India Post Payments Bank + BC model fills rural gap.",
        "source": "RBI Annual Report 2024",
    },
    "hospital_private": {
        "metro_tier1": 0.98,
        "urban_tier2": 0.72,
        "semi_urban_tier3": 0.42,
        "rural_tier4": 0.15,
    },
    "coaching_jee_neet": {
        "metro_tier1": 0.95,
        "urban_tier2": 0.78,
        "semi_urban_tier3": 0.52,
        "rural_tier4": 0.18,
        "note": "Kota / Hyderabad / Delhi / Patna dominate; online Unacademy/PW fills gap.",
    },
    "electric_grid_reliable": {
        "metro_tier1": 0.98,
        "urban_tier2": 0.88,
        "semi_urban_tier3": 0.68,
        "rural_tier4": 0.45,
        "note": "Bihar / UP / Jharkhand worst. 10-16hr outages in some districts.",
        "source": "Ministry of Power UDAY data 2023",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 7.  SOCIAL NORMS & INGRAINED BEHAVIOURS BY COMMUNITY
# ═══════════════════════════════════════════════════════════════════════════

SOCIAL_NORMS: dict[str, list[str]] = {
    "gujarati_business": [
        "Never pay MRP — always negotiate or use a known trader.",
        "Gold at every life event: birth, marriage, festival.",
        "Business expenses are family decisions, never impulsive.",
        "Jain influence means preference for non-violence, no meat spending.",
    ],
    "punjabi_urban": [
        "Shauk (passion) for good things — quality and show go together.",
        "SUV as status marker; hatchback seen as a step down.",
        "Hospitality means overfeeding guests — catering bill is a pride matter.",
        "Wedding is the most important financial event — 3-5 years of savings.",
    ],
    "bihari_migrant": [
        "Mobile is the primary identity document away from home.",
        "Sending money home (remittance) before personal expenditure.",
        "Chhath Puja trumps all — travel home at any cost.",
        "Purchase decisions deferred till village elders approve.",
    ],
    "urban_gen_z": [
        "Instagram post = social proof before purchase.",
        "BNPL (Buy Now Pay Later) normalised; no stigma.",
        "Authenticity > brand — will call out greenwashing.",
        "Food delivery as default; cooking is optional.",
    ],
    "rural_farmer_hindi_belt": [
        "Moneylender / input dealer is the first port of call for credit.",
        "TV advertisement with a film star is the gold standard for trust.",
        "Purchase delayed to post-harvest cash flow — Rabi/Kharif timing matters.",
        "Female purchase agency limited without husband/elder approval.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# 8.  CASTE / RELIGION COLOR PERCEPTION
#     Skin-tone marketing, colorism, and product linkage.
# ═══════════════════════════════════════════════════════════════════════════

COLOR_PERCEPTION: dict[str, Any] = {
    "fairness_premium": {
        "strength": 0.78,          # still strong in 2024 despite rebrand pressure
        "trend": "declining",
        "tier_variation": {
            "tier1": 0.42,          # urban educated more resistant
            "tier2": 0.65,
            "tier3": 0.78,
            "tier4": 0.85,
        },
        "gender_asymmetry": {
            "female_purchase_drive": 0.82,
            "male_self_purchase": 0.52,
            "male_gifting_to_female": 0.68,
        },
        "communities_highest": ["bihari_migrant", "rural_farmer_hindi_belt", "lower_middle_urban"],
        "communities_lowest":  ["urban_gen_z", "it_professional_metro"],
        "source": "Kantar Beauty Report India 2024 / Nielsen FMCG",
    },
    "dark_skin_discrimination": {
        "job_market_effect": 0.65,
        "marriage_market_effect": 0.75,
        "product_ad_representation": 0.30,  # 30% ads show dark-skin protagonists
        "regional_variation": {
            "South India": 0.68,  # darker skin baseline but same colorism
            "North India": 0.80,
            "East India": 0.72,
        },
        "source": "IHDS-II, Oxfam India Discrimination in India 2022",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 9.  GOVERNMENT DATA ANCHORS
#     Key statistics from NITI Aayog, NSO, NFHS, TRAI for calibration.
# ═══════════════════════════════════════════════════════════════════════════

GOVT_ANCHORS: dict[str, Any] = {
    "internet_users_2024":        {"value": 900_000_000, "unit": "people", "source": "TRAI"},
    "smartphone_users_2024":      {"value": 650_000_000, "unit": "people", "source": "GSMA"},
    "feature_phone_users_2024":   {"value": 300_000_000, "unit": "people", "source": "GSMA"},
    "upi_monthly_transactions":   {"value": 13_000_000_000, "unit": "txns", "source": "NPCI Jul 2024"},
    "avg_income_rural_monthly":   {"value": 8_059, "unit": "INR", "source": "NFHS-5 2021"},
    "avg_income_urban_monthly":   {"value": 19_301, "unit": "INR", "source": "NFHS-5 2021"},
    "obc_population_share":       {"value": 0.43, "unit": "fraction", "source": "Mandal Commission"},
    "sc_population_share":        {"value": 0.165, "unit": "fraction", "source": "Census 2011"},
    "st_population_share":        {"value": 0.085, "unit": "fraction", "source": "Census 2011"},
    "muslim_population_share":    {"value": 0.145, "unit": "fraction", "source": "Census 2011"},
    "christian_population_share": {"value": 0.023, "unit": "fraction", "source": "Census 2011"},
    "literate_population_share":  {"value": 0.775, "unit": "fraction", "source": "Census 2011"},
    "female_literacy":            {"value": 0.709, "unit": "fraction", "source": "NFHS-5"},
    "urban_population_share":     {"value": 0.36, "unit": "fraction", "source": "World Bank 2023"},
    "youth_15_29_share":          {"value": 0.27, "unit": "fraction", "source": "UN India"},
    "neet_multidimensional_poor":  {"value": 0.149, "unit": "fraction", "source": "NITI Aayog MPI 2023"},
    "ev_two_wheeler_share_2024":  {"value": 0.054, "unit": "fraction_of_new_sales", "source": "SIAM 2024"},
    "netflix_subscribers_india":  {"value": 7_000_000, "unit": "subscribers", "source": "Media Partners Asia 2024"},
    "jiocinema_mau":              {"value": 450_000_000, "unit": "MAU", "source": "Reliance 2024"},
    "organised_retail_share":     {"value": 0.15, "unit": "fraction_of_total_retail", "source": "IBEF 2024"},
}


# ═══════════════════════════════════════════════════════════════════════════
# 10.  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_community_profile(community_key: str) -> dict:
    return COMMUNITY_PROFILES.get(community_key, {})


def get_perception(tier: int, product_category: str) -> dict:
    key = (f"tier{tier}", product_category)
    return PRODUCT_PERCEPTION.get(key, {
        "desire": 0.5, "affordable": 0.5, "social_signal": 0.5,
        "trust": 0.5, "objection": "unknown", "objection_weight": 0.5,
    })


def supply_availability(product: str, tier: int) -> float:
    tier_map = {1: "metro_tier1", 2: "urban_tier2", 3: "semi_urban_tier3", 4: "rural_tier4"}
    constraint = SUPPLY_CONSTRAINTS.get(product, {})
    return constraint.get(tier_map.get(tier, "rural_tier4"), 0.5)


def festival_multiplier(product_category: str, month: int, community: str = "") -> float:
    best = 1.0
    for f in FESTIVAL_CALENDAR:
        m = f.get("month") or f.get("approximate_month", 0)
        if m != month:
            continue
        if community and community not in f.get("communities", ["All"]) and "All" not in f.get("communities", []):
            continue
        mult = f.get("category_multipliers", {}).get(product_category, 1.0)
        if mult > best:
            best = mult
    return best


def posh_score(product_or_place: str) -> float:
    return PREMIUM_SIGNALS.get(product_or_place, {}).get("posh_score", 0.5)


def fairness_demand_factor(tier: int, is_female: bool = True) -> float:
    base = COLOR_PERCEPTION["fairness_premium"]["tier_variation"].get(f"tier{tier}", 0.65)
    if is_female:
        return base * COLOR_PERCEPTION["fairness_premium"]["gender_asymmetry"]["female_purchase_drive"]
    return base * COLOR_PERCEPTION["fairness_premium"]["gender_asymmetry"]["male_self_purchase"]


def occupation_digital_score(occupation_id: str) -> float:
    occ = OCCUPATION_PROFILES.get(occupation_id, {})
    return occ.get("digital", 0.5)


def govt_anchor(key: str) -> Any:
    return GOVT_ANCHORS.get(key, {}).get("value")
