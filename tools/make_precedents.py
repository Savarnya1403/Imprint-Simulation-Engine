"""Build the precedent library: past Indian market decisions and perception arcs.

The arcs are *reconstructed* from public reporting, not measured from a panel.
Every case says so. The point is retrieval and analogy, not a claim of causal
identification. Each record carries the source, the mechanism, the outcome
range and the caveat.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "precedents.json"
DAYS = [-14, -7, 0, 7, 14, 30, 45, 60]


def p(support, neutral, oppose):
    total = support + neutral + oppose
    return {"support": round(support / total, 3), "neutral": round(neutral / total, 3), "oppose": round(oppose / total, 3)}


def arc(rows):
    return [{"day": d, **p(*r)} for d, r in zip(DAYS, rows)]


def src(org, title, year, url):
    return {"org": org, "title": title, "year": year, "url": url}


CASES = [
    {
        "id": "jio-2016", "brand": "Reliance Jio", "decision": "Free 4G data and voice launch", "year": 2016, "month": 9,
        "category": "telecom", "tags": ["price shock", "telecom", "data", "incumbent response", "mass market"],
        "summary": "Jio entered with free voice and cheap data, forcing incumbents to cut prices and collapsing data tariffs.",
        "context": "Incumbents earned rents on voice and data; smartphone penetration was rising but data was expensive. Jio needed scale before rivals could copy.",
        "announcement": "Free services until 31 December 2016, then aggressive tariff packs.",
        "treatment_type": "price shock", "geography": "national",
        "sources": [src("TRAI", "Telecom subscription and tariff data", 2017, "https://www.trai.gov.in/"), src("Reliance Industries", "Annual Report 2016-17", 2017, "https://www.ril.com/investors")],
        "perception": arc([(.30, .45, .25), (.34, .44, .22), (.62, .27, .11), (.70, .21, .09), (.67, .24, .09), (.60, .29, .11), (.56, .31, .13), (.54, .33, .13)]),
        "peak_oppose_day": 7, "peak_support_day": 7, "half_life_days": 28,
        "outcome": {"kpi": "mobile data price", "direction": "down", "magnitude_pct": -90, "low": -95, "high": -80, "confidence": "high", "note": "Tariffs fell sharply; the exact basket depends on plan and circle."},
        "mechanisms": ["Price Shock", "Incumbent Response", "Network Effect", "Scale Bet"],
        "segments": [{"segment": "Urban youth", "reaction": "Immediate trial; data-heavy behaviour."}, {"segment": "Rural feature-phone users", "reaction": "Slower; device and coverage bind."}, {"segment": "Incumbent shareholders", "reaction": "Severe value destruction."}],
        "caveats": "Free service is not a sustainable price; the perception arc is reconstructed from public reporting.",
    },
    {
        "id": "demonetisation-2016", "brand": "Government of India", "decision": " ₹500/₹1000 note withdrawal", "year": 2016, "month": 11,
        "category": "payments", "tags": ["policy shock", "cash", "digital payments", "trust", "informal economy"],
        "summary": "A sudden currency withdrawal pushed households and merchants toward digital payments, then cash partially returned.",
        "context": "Cash dominated small transactions; UPI was new and merchant acceptance was thin. The policy was announced as a fight against black money.",
        "announcement": "Prime-time address; 86% of currency by value invalidated with a short exchange window.",
        "treatment_type": "policy shock", "geography": "national",
        "sources": [src("RBI", "Annual Report 2016-17", 2017, "https://www.rbi.org.in/"), src("NPCI", "UPI statistics", 2017, "https://www.npci.org.in/")],
        "perception": arc([(.38, .30, .32), (.42, .28, .30), (.55, .22, .23), (.48, .24, .28), (.40, .26, .34), (.34, .28, .38), (.32, .29, .39), (.31, .30, .39)]),
        "peak_oppose_day": 14, "peak_support_day": 0, "half_life_days": 35,
        "outcome": {"kpi": "digital payment volume", "direction": "up", "magnitude_pct": 35, "low": 20, "high": 50, "confidence": "medium", "note": "Digital payments rose, but cash also returned; attribution to the policy alone is contested."},
        "mechanisms": ["Forced Adoption", "Cash Constraint", "Merchant Acceptance", "Trust Shock"],
        "segments": [{"segment": "Urban salaried", "reaction": "Quick digital shift."}, {"segment": "Informal daily-wage", "reaction": "Severe short-term disruption."}, {"segment": "Small merchants", "reaction": "Adopted QR codes, then reverted partly to cash."}],
        "caveats": "Perception and outcome are entangled with UPI, GST and bank recapitalisation. Not a clean natural experiment.",
    },
    {
        "id": "maggi-2015", "brand": "Nestlé Maggi", "decision": "Regulatory ban after lead tests", "year": 2015, "month": 6,
        "category": "fmcg", "tags": ["trust shock", "food safety", "regulator", "boycott", "recovery"],
        "summary": "A food-safety scare removed Maggi from shelves; trust collapsed, then recovered slowly after relaunch and testing.",
        "context": "Maggi was a category-defining convenience food with deep household penetration and a nostalgic position among students.",
        "announcement": "FSSAI order; widespread product withdrawal and negative TV coverage.",
        "treatment_type": "trust shock", "geography": "national",
        "sources": [src("FSSAI", "Order on Maggi noodles", 2015, "https://fssai.gov.in/"), src("Nestlé India", "Annual Report 2015", 2016, "https://www.nestle.in/investors")],
        "perception": arc([(.40, .32, .28), (.38, .30, .32), (.18, .20, .62), (.16, .18, .66), (.20, .22, .58), (.30, .28, .42), (.38, .30, .32), (.43, .31, .26)]),
        "peak_oppose_day": 7, "peak_support_day": -14, "half_life_days": 40,
        "outcome": {"kpi": "brand sales", "direction": "down", "magnitude_pct": -55, "low": -70, "high": -35, "confidence": "high", "note": "Sales collapsed during the ban; recovery took multiple quarters."},
        "mechanisms": ["Trust Shock", "Regulatory Legitimacy", "Nostalgia", "Distribution Loss"],
        "segments": [{"segment": "Parents", "reaction": "Strong avoidance."}, {"segment": "Students", "reaction": "Faster return after relaunch."}, {"segment": "Retailers", "reaction": "Delisted, then restored after assurance."}],
        "caveats": "The ban was later contested in court; the perception arc is a reconstruction, not a measured panel.",
    },
    {
        "id": "whatsapp-2021", "brand": "WhatsApp", "decision": "Privacy policy update", "year": 2021, "month": 1,
        "category": "digital", "tags": ["privacy", "trust", "network effect", "migration", "backlash"],
        "summary": "A privacy-policy change triggered a loud backlash and a migration wave to Signal and Telegram, but WhatsApp's core network held.",
        "context": "WhatsApp was the default social graph; switching costs were high because family and work groups lived there.",
        "announcement": "In-app notice requiring acceptance; confusion about what would be shared with Facebook.",
        "treatment_type": "trust shock", "geography": "national",
        "sources": [src("WhatsApp", "Privacy policy update explainer", 2021, "https://blog.whatsapp.com/"), src("Reuters", "Signal and Telegram downloads surge", 2021, "https://www.reuters.com/")],
        "perception": arc([(.38, .40, .22), (.36, .40, .24), (.26, .33, .41), (.22, .27, .51), (.24, .28, .48), (.28, .31, .41), (.30, .32, .38), (.31, .33, .36)]),
        "peak_oppose_day": 7, "peak_support_day": -14, "half_life_days": 30,
        "outcome": {"kpi": "migration to rivals", "direction": "up", "magnitude_pct": 4, "low": 1, "high": 9, "confidence": "medium", "note": "Downloads surged, but durable switching was limited by network effects."},
        "mechanisms": ["Privacy Backlash", "Network Lock-in", "Media Amplification", "Low Behavioural Elasticity"],
        "segments": [{"segment": "Urban tech workers", "reaction": "Visible migration."}, {"segment": "Family groups", "reaction": "Stayed; switching cost too high."}, {"segment": "Small businesses", "reaction": "Stayed for customer reach."}],
        "caveats": "A canonical case of loud online opposition not translating into proportional behaviour change.",
    },
    {
        "id": "netflix-mobile-2019", "brand": "Netflix India", "decision": "Mobile-only low-price plan", "year": 2019, "month": 7,
        "category": "ott", "tags": ["price cut", "ott", "mobile", "premium", "india-first"],
        "summary": "Netflix introduced a mobile-only plan at a fraction of the standard price to widen reach beyond affluent metros.",
        "context": "Indian OTT price points were low, data was cheap, and most viewing was mobile. Netflix was seen as expensive and English-first.",
        "announcement": "₹199/month mobile-only plan with local content push.",
        "treatment_type": "price cut", "geography": "national",
        "sources": [src("Netflix", "India mobile plan announcement", 2019, "https://about.netflix.com/"), src("Media Partners Asia", "India OTT outlook", 2020, "https://www.mediapartnersasia.com/")],
        "perception": arc([(.34, .48, .18), (.36, .47, .17), (.48, .42, .10), (.53, .37, .10), (.50, .39, .11), (.45, .43, .12), (.43, .44, .13), (.42, .45, .13)]),
        "peak_oppose_day": 7, "peak_support_day": 7, "half_life_days": 30,
        "outcome": {"kpi": "paid subscriptions", "direction": "up", "magnitude_pct": 28, "low": 15, "high": 40, "confidence": "medium", "note": "The plan widened the funnel; ARPU fell and sharing remained common."},
        "mechanisms": ["Price Architecture", "Mobile First", "Local Content", "Status Democratisation"],
        "segments": [{"segment": "Students", "reaction": "High trial."}, {"segment": "Families", "reaction": "Shared passwords."}, {"segment": "Affluent metro", "reaction": "Stayed on premium plans."}],
        "caveats": "Subscriber estimates vary by source; the perception arc is reconstructed.",
    },
    {
        "id": "airtel-min-recharge-2018", "brand": "Bharti Airtel", "decision": "Minimum monthly recharge", "year": 2018, "month": 11,
        "category": "telecom", "tags": ["price hike", "telecom", "churn", "arpu", "low-end users"],
        "summary": "Airtel set a minimum recharge to clean up low-ARPU subscribers, lifting ARPU while churning marginal users.",
        "context": "The market had collapsed into a price war; operators wanted to reduce inactive and ultra-low-ARPU subscribers.",
        "announcement": "Minimum monthly recharge of ₹35 to retain incoming service.",
        "treatment_type": "price hike", "geography": "national",
        "sources": [src("TRAI", "Telecom subscription reports", 2019, "https://www.trai.gov.in/"), src("Bharti Airtel", "Annual Report 2018-19", 2019, "https://www.airtel.in/investors")],
        "perception": arc([(.35, .45, .20), (.33, .44, .23), (.27, .38, .35), (.25, .31, .44), (.26, .31, .43), (.30, .34, .36), (.32, .35, .33), (.33, .36, .31)]),
        "peak_oppose_day": 7, "peak_support_day": -14, "half_life_days": 35,
        "outcome": {"kpi": "ARPU", "direction": "up", "magnitude_pct": 18, "low": 10, "high": 26, "confidence": "high", "note": "ARPU rose and the subscriber base shrank; the trade-off was deliberate."},
        "mechanisms": ["Price Hike", "Customer Cleaning", "Churn", "ARPU Trade-off"],
        "segments": [{"segment": "Low-end prepaid", "reaction": "Churn or multi-SIM."}, {"segment": "Urban postpaid", "reaction": "Low impact."}, {"segment": "Rural shared phones", "reaction": "Disproportionate disruption."}],
        "caveats": "ARPU and churn are reported at company level; perception is reconstructed.",
    },
    {
        "id": "patanjali-2015", "brand": "Patanjali Ayurved", "decision": "Ayurvedic FMCG scale-up", "year": 2015, "month": 1,
        "category": "fmcg", "tags": ["trust", "price", "swadeshi", "incumbent response", "distribution"],
        "summary": "Patanjali combined ayurvedic claims, low prices and swadeshi identity to take share from incumbents in oral care, hair oil and foods.",
        "context": "Consumers were sceptical of chemical-heavy FMCG; Baba Ramdev's brand had mass trust and a yoga-media platform.",
        "announcement": "Aggressive expansion through franchise stores and kirana distribution.",
        "treatment_type": "new entrant", "geography": "national",
        "sources": [src("NielsenIQ", "India FMCG market data", 2017, "https://nielseniq.com/"), src("Patanjali Ayurved", "Company information", 2016, "https://www.patanjaliayurved.net/")],
        "perception": arc([(.44, .42, .14), (.46, .41, .13), (.54, .37, .09), (.58, .34, .08), (.56, .35, .09), (.51, .39, .10), (.48, .41, .11), (.47, .42, .11)]),
        "peak_oppose_day": -14, "peak_support_day": 7, "half_life_days": 45,
        "outcome": {"kpi": "category share", "direction": "up", "magnitude_pct": 6, "low": 3, "high": 10, "confidence": "medium", "note": "Share gains were real in some categories; quality and distribution varied."},
        "mechanisms": ["Trust Transfer", "Price Advantage", "Cultural Identity", "Incumbent Response"],
        "segments": [{"segment": "Hindi-belt households", "reaction": "Strong trial."}, {"segment": "Urban sceptics", "reaction": "Quality concerns."}, {"segment": "Kirana", "reaction": "Adopted where margins were better."}],
        "caveats": "Category shares are contested; treat as directional.",
    },
    {
        "id": "byjus-2023", "brand": "BYJU'S", "decision": "Aggressive edtech expansion and refund crisis", "year": 2023, "month": 5,
        "category": "edtech", "tags": ["trust shock", "edtech", "refunds", "sales pressure", "collapse"],
        "summary": "A high-pressure sales model and refund failures destroyed trust in India's most visible edtech brand.",
        "context": "Pandemic-era demand inflated the category; parents were buying hope and exam outcomes, often financed by loans.",
        "announcement": "Layoffs, delayed salaries, auditor resignation and regulatory scrutiny.",
        "treatment_type": "trust shock", "geography": "national",
        "sources": [src("Ministry of Corporate Affairs", "Company filings and inspections", 2023, "https://www.mca.gov.in/"), src("Reuters", "BYJU'S crisis coverage", 2023, "https://www.reuters.com/")],
        "perception": arc([(.46, .36, .18), (.43, .34, .23), (.30, .28, .42), (.22, .22, .56), (.17, .18, .65), (.12, .16, .72), (.11, .16, .73), (.10, .17, .73)]),
        "peak_oppose_day": 30, "peak_support_day": -14, "half_life_days": 60,
        "outcome": {"kpi": "paid renewals", "direction": "down", "magnitude_pct": -60, "low": -75, "high": -40, "confidence": "high", "note": "Renewals and new sales collapsed; the brand became a cautionary tale."},
        "mechanisms": ["Trust Shock", "Refund Failure", "Sales Pressure", "Regulatory Scrutiny"],
        "segments": [{"segment": "Parents", "reaction": "Anger and refund demands."}, {"segment": "Students", "reaction": "Disruption and distrust."}, {"segment": "Investors", "reaction": "Write-downs."}],
        "caveats": "A company-level collapse, not a clean category experiment.",
    },
    {
        "id": "nano-2009", "brand": "Tata Nano", "decision": "₹1 lakh car launch", "year": 2009, "month": 3,
        "category": "mobility", "tags": ["status", "positioning", "car", "aspiration", "failure"],
        "summary": "The Nano was engineered as the world's cheapest car; the market read 'cheap' as a status insult, not a triumph.",
        "context": "Two-wheeler families aspired to a car as a visible sign of arrival. Price was a barrier, but status was the reason to buy.",
        "announcement": "Launch at ₹1 lakh, positioned as a safer alternative to a scooter.",
        "treatment_type": "new product", "geography": "national",
        "sources": [src("Tata Motors", "Annual Report 2009-10", 2010, "https://www.tatamotors.com/investors/"), src("SIAM", "Passenger vehicle statistics", 2010, "https://www.siam.in/statistics.aspx")],
        "perception": arc([(.30, .48, .22), (.28, .47, .25), (.24, .44, .32), (.22, .42, .36), (.21, .41, .38), (.22, .40, .38), (.23, .40, .37), (.24, .40, .36)]),
        "peak_oppose_day": 14, "peak_support_day": -14, "half_life_days": 60,
        "outcome": {"kpi": "unit sales vs target", "direction": "down", "magnitude_pct": -70, "low": -85, "high": -50, "confidence": "high", "note": "The car missed volume targets badly; later variants did not repair the positioning."},
        "mechanisms": ["Status Misread", "Price Signal", "Aspiration Gap", "Distribution"],
        "segments": [{"segment": "First-time car buyers", "reaction": "Rejected the 'cheap' label."}, {"segment": "Two-wheeler owners", "reaction": "Preferred a used car or entry hatch."}, {"segment": "Dealers", "reaction": "Low pull."}],
        "caveats": "A product/positioning failure; the perception arc is reconstructed.",
    },
    {
        "id": "fair-lovely-2020", "brand": "HUL", "decision": "Fair & Lovely rebrand to Glow & Lovely", "year": 2020, "month": 6,
        "category": "beauty", "tags": ["colourism", "brand", "symbolic change", "beauty", "status"],
        "summary": "A name change responded to colourism criticism without changing the product or the underlying fairness promise.",
        "context": "Fairness creams were a large, profitable category; colourism was increasingly contested online but still embedded in matrimony and media.",
        "announcement": "Rebrand announced amid global Black Lives Matter scrutiny and a public petition.",
        "treatment_type": "rebrand", "geography": "national",
        "sources": [src("Hindustan Unilever", "Press release on brand change", 2020, "https://www.hul.co.in/"), src("NielsenIQ", "Beauty and personal care data", 2021, "https://nielseniq.com/")],
        "perception": arc([(.28, .42, .30), (.29, .41, .30), (.36, .38, .26), (.40, .35, .25), (.38, .36, .26), (.34, .38, .28), (.32, .39, .29), (.31, .40, .29)]),
        "peak_oppose_day": -14, "peak_support_day": 7, "half_life_days": 30,
        "outcome": {"kpi": "brand share", "direction": "flat", "magnitude_pct": 0, "low": -3, "high": 3, "confidence": "medium", "note": "The name changed; the category logic did not. Sales were broadly stable."},
        "mechanisms": ["Symbolic Response", "Colourism", "Brand Equity", "Consumer Cynicism"],
        "segments": [{"segment": "Urban young women", "reaction": "Sceptical of cosmetic change."}, {"segment": "Mass market", "reaction": "Continued purchase."}, {"segment": "Activists", "reaction": "Called it superficial."}],
        "caveats": "Perception is reconstructed from public commentary, not a measured survey.",
    },
    {
        "id": "ondc-2022", "brand": "ONDC", "decision": "Open network for digital commerce launch", "year": 2022, "month": 4,
        "category": "ecommerce", "tags": ["infrastructure", "ecommerce", "open network", "slow adoption", "policy"],
        "summary": "An open protocol aimed to democratise e-commerce, but adoption was slow because buyer apps, seller onboarding and incentives were fragmented.",
        "context": "Marketplace duopoly, high commissions and small-seller exclusion created policy demand for an open network.",
        "announcement": "Beta launch with a handful of buyer and seller apps.",
        "treatment_type": "infrastructure", "geography": "national",
        "sources": [src("ONDC", "Network launch and statistics", 2024, "https://ondc.org/"), src("Bain & Company", "How India Shops Online", 2024, "https://www.bain.com/insights/how-india-shops-online/")],
        "perception": arc([(.30, .58, .12), (.31, .57, .12), (.36, .53, .11), (.38, .51, .11), (.37, .51, .12), (.34, .53, .13), (.33, .53, .14), (.32, .54, .14)]),
        "peak_oppose_day": 45, "peak_support_day": 7, "half_life_days": 45,
        "outcome": {"kpi": "GMV share", "direction": "up", "magnitude_pct": 1, "low": 0, "high": 3, "confidence": "medium", "note": "Real but small share; the network's impact is longer-term and depends on incentives."},
        "mechanisms": ["Infrastructure", "Chicken-and-Egg", "Seller Incentives", "Buyer Habit"],
        "segments": [{"segment": "Small sellers", "reaction": "Curious but under-resourced."}, {"segment": "Buyers", "reaction": "Low awareness."}, {"segment": "Incumbents", "reaction": "Watchful."}],
        "caveats": "Too early for a stable outcome estimate; the case is included to model infrastructure-led adoption.",
    },
    {
        "id": "upi-2016", "brand": "NPCI / UPI", "decision": "Unified Payments Interface launch", "year": 2016, "month": 4,
        "category": "payments", "tags": ["infrastructure", "payments", "network effect", "slow then fast", "policy"],
        "summary": "UPI took years to reach escape velocity, then became the default retail payment rail.",
        "context": "Cash dominated; bank apps were poor; merchant acceptance was thin. Demonetisation and cheap data accelerated adoption.",
        "announcement": "API launch with a handful of banks; later incentives and QR codes.",
        "treatment_type": "infrastructure", "geography": "national",
        "sources": [src("NPCI", "UPI ecosystem statistics", 2025, "https://www.npci.org.in/"), src("RBI", "Payments system indicators", 2025, "https://www.rbi.org.in/")],
        "perception": arc([(.36, .52, .12), (.37, .51, .12), (.44, .47, .09), (.50, .42, .08), (.54, .39, .07), (.58, .36, .06), (.60, .35, .05), (.61, .34, .05)]),
        "peak_oppose_day": -14, "peak_support_day": 60, "half_life_days": 60,
        "outcome": {"kpi": "transaction volume", "direction": "up", "magnitude_pct": 100, "low": 50, "high": 200, "confidence": "high", "note": "From a small base to hundreds of billions of annual transactions; exact growth depends on the base year."},
        "mechanisms": ["Infrastructure", "Network Effect", "Policy Push", "Merchant Acceptance"],
        "segments": [{"segment": "Urban digitally native", "reaction": "Rapid adoption."}, {"segment": "Rural feature-phone users", "reaction": "Slower; assisted and feature-phone UPI emerging."}, {"segment": "Small merchants", "reaction": "QR codes lowered acceptance cost."}],
        "caveats": "A multi-year adoption arc, not a 60-day event. Included as an infrastructure precedent.",
    },
    {
        "id": "gst-2017", "brand": "Government of India", "decision": "Goods and Services Tax rollout", "year": 2017, "month": 7,
        "category": "policy", "tags": ["policy", "tax", "compliance", "informal", "confusion"],
        "summary": "GST unified indirect taxes but created short-term compliance confusion, especially for small traders.",
        "context": "State VAT regimes fragmented the market; informal traders were outside the tax net.",
        "announcement": "Midnight launch; multiple rate slabs and frequent revisions.",
        "treatment_type": "policy", "geography": "national",
        "sources": [src("GST Council", "GST implementation records", 2018, "https://gstcouncil.gov.in/"), src("World Bank", "India Development Update", 2018, "https://www.worldbank.org/en/country/india")],
        "perception": arc([(.32, .38, .30), (.33, .37, .30), (.40, .34, .26), (.38, .32, .30), (.36, .31, .33), (.35, .31, .34), (.36, .32, .32), (.37, .33, .30)]),
        "peak_oppose_day": 14, "peak_support_day": 0, "half_life_days": 40,
        "outcome": {"kpi": "formal compliance", "direction": "up", "magnitude_pct": 12, "low": 5, "high": 20, "confidence": "medium", "note": "Formalisation rose; short-term disruption and compliance costs were real."},
        "mechanisms": ["Policy Shock", "Compliance Cost", "Formalisation", "Rate Confusion"],
        "segments": [{"segment": "Large firms", "reaction": "Adapted."}, {"segment": "Small traders", "reaction": "Confusion and cost."}, {"segment": "Consumers", "reaction": "Mixed price effects."}],
        "caveats": "A structural policy, not a consumer brand decision.",
    },
    {
        "id": "farm-bills-2020", "brand": "Government of India", "decision": "Three farm laws", "year": 2020, "month": 9,
        "category": "policy", "tags": ["policy", "agriculture", "protest", "trust", "regional"],
        "summary": "Farm laws triggered sustained protests, especially in Punjab and Haryana, and were repealed after a trust breakdown.",
        "context": "MSP and mandi systems were core to agrarian identity; farmers feared corporate capture of procurement.",
        "announcement": "Passed amid pandemic restrictions; protests and negotiations followed.",
        "treatment_type": "policy", "geography": "national, concentrated in north",
        "sources": [src("PRS India", "Legislative tracking", 2021, "https://prsindia.org/"), src("Government of India", "Repeal announcement", 2021, "https://www.india.gov.in/")],
        "perception": arc([(.42, .38, .20), (.40, .36, .24), (.30, .30, .40), (.24, .24, .52), (.21, .21, .58), (.20, .20, .60), (.19, .20, .61), (.20, .21, .59)]),
        "peak_oppose_day": 30, "peak_support_day": -14, "half_life_days": 60,
        "outcome": {"kpi": "government support", "direction": "down", "magnitude_pct": -18, "low": -25, "high": -10, "confidence": "medium", "note": "The laws were repealed; electoral effects varied by state."},
        "mechanisms": ["Trust Shock", "Identity Politics", "Organised Protest", "Policy Reversal"],
        "segments": [{"segment": "Punjab farmers", "reaction": "Sustained opposition."}, {"segment": "Urban consumers", "reaction": "Mixed, low salience."}, {"segment": "Government", "reaction": "Repeal."}],
        "caveats": "A politically salient case; perception is not a proxy for vote share.",
    },
    {
        "id": "ola-uber-2016", "brand": "Ola / Uber", "decision": "Surge pricing during demand spikes", "year": 2016, "month": 2,
        "category": "mobility", "tags": ["price", "surge", "trust", "regulation", "platform"],
        "summary": "Surge pricing was economically logical and socially toxic; users felt exploited during rain, strikes and emergencies.",
        "context": "App-based ride-hailing was displacing autos and taxis; drivers and riders were both learning platform rules.",
        "announcement": "Dynamic pricing expanded; regulators and users pushed back.",
        "treatment_type": "price shock", "geography": "metros",
        "sources": [src("Transport Department, Delhi", "Radio taxi regulation", 2016, "https://transport.delhi.gov.in/"), src("Reuters", "India ride-hailing coverage", 2016, "https://www.reuters.com/")],
        "perception": arc([(.34, .42, .24), (.33, .42, .25), (.28, .36, .36), (.26, .32, .42), (.25, .31, .44), (.28, .34, .38), (.30, .35, .35), (.31, .36, .33)]),
        "peak_oppose_day": 14, "peak_support_day": -14, "half_life_days": 30,
        "outcome": {"kpi": "ride frequency", "direction": "down", "magnitude_pct": -6, "low": -12, "high": -2, "confidence": "medium", "note": "Short-term dips and regulatory scrutiny; the platform model survived."},
        "mechanisms": ["Price Fairness", "Trust Shock", "Regulatory Response", "Dependence"],
        "segments": [{"segment": "Daily commuters", "reaction": "Anger but continued use."}, {"segment": "Drivers", "reaction": "Mixed; incentives mattered."}, {"segment": "Regulators", "reaction": "Price caps and licensing."}],
        "caveats": "Perception is reconstructed; ride-hailing data is private.",
    },
    {
        "id": "platform-fee-2023", "brand": "Swiggy / Zomato", "decision": "Platform fee and surge fee expansion", "year": 2023, "month": 4,
        "category": "food delivery", "tags": ["price", "platform", "fee", "low elasticity", "habit"],
        "summary": "Food-delivery platforms raised fees; users complained but order frequency fell only modestly.",
        "context": "Habit, discounts and convenience made demand less elastic than social media anger suggested.",
        "announcement": "Per-order platform fee, rain fees and priority fees.",
        "treatment_type": "price hike", "geography": "metros and tier-2",
        "sources": [src("Swiggy", "Annual Report 2023-24", 2024, "https://www.swiggy.com/investors"), src("Zomato", "Annual Report 2023-24", 2024, "https://www.zomato.com/investor-relations")],
        "perception": arc([(.36, .46, .18), (.35, .45, .20), (.30, .38, .32), (.28, .34, .38), (.29, .34, .37), (.31, .36, .33), (.32, .37, .31), (.33, .37, .30)]),
        "peak_oppose_day": 14, "peak_support_day": -14, "half_life_days": 25,
        "outcome": {"kpi": "order frequency", "direction": "down", "magnitude_pct": -3, "low": -7, "high": 0, "confidence": "medium", "note": "Small frequency impact; fee revenue rose. Habit and convenience dominate."},
        "mechanisms": ["Low Price Elasticity", "Habit", "Fee Fatigue", "Platform Power"],
        "segments": [{"segment": "Young urban users", "reaction": "Complain, keep ordering."}, {"segment": "Families", "reaction": "More sensitive."}, {"segment": "Restaurants", "reaction": "Margin pressure."}],
        "caveats": "Company-level data, not a measured consumer panel.",
    },
]


def main():
    data = {
        "version": "2026.11-seed",
        "built": "2026-11-05",
        "provenance_note": (
            "Reconstructed perception arcs from public reporting and regulator/company records. "
            "They are illustrative, not a measured panel, not a representative survey, and not a causal estimate. "
            "Use them for analogy and calibration priors, not as ground truth."
        ),
        "days": DAYS,
        "cases": CASES,
    }
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} · {len(CASES)} cases")


if __name__ == "__main__":
    main()
