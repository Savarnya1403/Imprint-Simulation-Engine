"""Build the Imprint Bharat context atlas.

The atlas is a *curated seed corpus*, not a claim to have trained on every
Indian dataset. It records public indicators, the source that published them,
the geographic scope, and a confidence label. The ingestion module can add
PDFs/HTML/CSV on top without changing the schema.

Run: python tools/make_atlas.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "atlas.json"


def S(id, org, title, year, url, typ, coverage, note):
    return {
        "id": id, "org": org, "title": title, "year": year, "url": url,
        "type": typ, "coverage": coverage, "note": note,
    }


SOURCES = [
    S("census2011", "Office of the Registrar General & Census Commissioner, India", "Census of India 2011", 2011, "https://censusindia.gov.in/census.website/", "government census", "national / state / district", "Primary census tables: population, urbanisation, households, amenities."),
    S("census_religion", "Census of India", "C-1 Religion tables, 2011", 2011, "https://censusindia.gov.in/nada/index.php/catalog/11361", "government census", "national / state", "Religion composition by state; used only for structural context."),
    S("census_migration", "Census of India", "D-Series migration tables, 2011", 2011, "https://censusindia.gov.in/nada/index.php/catalog/11363", "government census", "national / state / district", "Internal migration, place of birth and last residence."),
    S("nfhs5", "International Institute for Population Sciences / MoHFW", "National Family Health Survey 5 (2019-21), India Report", 2021, "https://rchiips.org/nfhs/NFHS-5Reports/India.pdf", "government survey", "national / state / district", "Health, gender, fertility, household amenities, internet use."),
    S("nfhs5_state", "IIPS / MoHFW", "NFHS-5 State Fact Sheets", 2021, "https://rchiips.org/nfhs/NFHS-5_FCTS/India.pdf", "government survey", "state / district", "State-level indicators used to vary context, not to type individuals."),
    S("niti_mpi", "NITI Aayog / UNDP", "National Multidimensional Poverty Index 2023", 2023, "https://www.niti.gov.in/sites/default/files/2023-12/National-Multidimensional-Poverty-Index-2023.pdf", "government report", "national / state / district", "MPI headcount and inter-temporal escape from poverty."),
    S("niti_adp", "NITI Aayog", "Aspirational Districts Programme", 2024, "https://www.niti.gov.in/aspirational-districts-programme", "government programme", "district", "District-level development gaps in health, education, agriculture, finance."),
    S("hces2223", "Ministry of Statistics and Programme Implementation", "Household Consumption Expenditure Survey 2022-23", 2023, "https://www.mospi.gov.in/sites/default/files/publication_reports/Household_Consumption_Expenditure_Survey_2022_23.pdf", "government survey", "national / state", "MPCE, food/non-food shares, consumption inequality."),
    S("plfs2324", "Ministry of Statistics and Programme Implementation", "Periodic Labour Force Survey Annual Report 2023-24", 2024, "https://www.mospi.gov.in/sites/default/files/publication_reports/PLFS_Annual_Report_2023_24.pdf", "government survey", "national / state", "LFPR, unemployment, informality, female participation."),
    S("cms_telecom", "Ministry of Statistics and Programme Implementation", "Comprehensive Modular Survey: Telecom 2025", 2025, "https://www.mospi.gov.in/sites/default/files/press_release/Final_press%20release_CMS_T.pdf", "government survey", "national / state", "Household phone and internet access, digital divides."),
    S("trai", "Telecom Regulatory Authority of India", "Telecom Subscription Reports", 2025, "https://www.trai.gov.in/release-publication/reports/telecom-subscription-reports", "regulator data", "national / circle", "Subscribers, rural/urban split, broadband, ARPU."),
    S("npci_upi", "National Payments Corporation of India", "UPI Ecosystem Statistics", 2025, "https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics", "payments data", "national", "Transaction volume and value; adoption is not the same as usage intensity."),
    S("rbi_payments", "Reserve Bank of India", "Payments System Indicators", 2025, "https://www.rbi.org.in/Scripts/Statistics.aspx", "central bank data", "national", "Digital payment mix, currency in circulation, financial access."),
    S("rbi_fi", "Reserve Bank of India", "Financial Inclusion Index", 2024, "https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx", "central bank report", "national / state", "Access, usage and quality of financial services."),
    S("irdai", "Insurance Regulatory and Development Authority of India", "Annual Report 2023-24", 2024, "https://irdai.gov.in/", "regulator data", "national / state", "Insurance penetration and density; protection gap."),
    S("nha", "National Health Systems Resource Centre", "National Health Accounts 2021-22", 2024, "https://nhsrcindia.org/national-health-accounts-records", "government report", "national / state", "Health spending, out-of-pocket share, insurance coverage."),
    S("udise", "Ministry of Education", "UDISE+ 2023-24", 2024, "https://udiseplus.gov.in/", "government data", "national / state / district", "School enrolment, infrastructure, digital access."),
    S("aishe", "Ministry of Education", "All India Survey on Higher Education 2021-22", 2023, "https://aishe.gov.in/", "government survey", "national / state", "College enrolment, GER, gender and discipline mix."),
    S("aser", "ASER Centre", "Annual Status of Education Report 2023 (Beyond Basics)", 2024, "https://asercentre.org/aser-2023/", "public survey", "district / rural", "14-18 learning, digital access and work aspirations."),
    S("jjm", "Department of Drinking Water and Sanitation", "Jal Jeevan Mission Dashboard", 2025, "https://jaljeevanmission.gov.in/", "government dashboard", "national / state / district", "Tap-water coverage and rural infrastructure gaps."),
    S("mgnrega", "Ministry of Rural Development", "MGNREGA Public Dashboard", 2025, "https://nrega.nic.in/", "government dashboard", "national / state / district", "Rural wage demand, women's participation, distress signals."),
    S("pmayg", "Ministry of Rural Development", "PMAY-Gramin Dashboard", 2025, "https://pmayg.nic.in/", "government dashboard", "national / state / district", "Rural housing, asset creation and credit linkage."),
    S("mohua", "Ministry of Housing and Urban Affairs", "Urban Transport and Smart Cities", 2024, "https://mohua.gov.in/", "government programme", "city", "Urban services, mobility and municipal capacity."),
    S("ppac", "Petroleum Planning & Analysis Cell", "Snapshots of Petroleum Statistics", 2025, "https://ppac.gov.in/", "government data", "national / state", "LPG, diesel, petrol consumption and import dependence."),
    S("mnre", "Ministry of New and Renewable Energy", "Renewable Energy Statistics", 2024, "https://mnre.gov.in/", "government data", "national / state", "Solar rooftop, RE capacity and state-wise progress."),
    S("siam", "Society of Indian Automobile Manufacturers", "Automobile Statistics", 2025, "https://www.siam.in/statistics.aspx", "industry data", "national", "Two-wheeler, car and commercial vehicle sales."),
    S("bnef", "BloombergNEF", "Electric Vehicle Outlook", 2024, "https://about.bnef.com/electric-vehicle-outlook/", "industry research", "global / India", "EV penetration and charging infrastructure."),
    S("iamai", "IAMAI / Kantar", "Internet in India", 2025, "https://www.iamai.in/", "industry survey", "national / state", "Active internet users, rural share, language use."),
    S("kantar", "Kantar", "Brand Footprint India", 2024, "https://www.kantar.com/", "industry research", "national / state", "FMCG penetration, frequency and rural reach."),
    S("nielseniq", "NielsenIQ", "India Consumer Outlook", 2024, "https://nielseniq.com/global/en/insights/", "industry research", "national / state", "FMCG value/volume, premiumisation and channel mix."),
    S("bain_flipkart", "Bain & Company / Flipkart", "How India Shops Online", 2024, "https://www.bain.com/insights/how-india-shops-online/", "industry report", "national / city tier", "E-commerce shoppers, categories, tier-2/3 growth."),
    S("redseer", "Redseer Strategy Consultants", "India Internet and Quick Commerce", 2024, "https://redseer.com/reports/", "industry research", "national / city", "Quick commerce size, dark stores, usage frequency."),
    S("gs_consumer", "Goldman Sachs", "India Consumer Market", 2023, "https://www.goldmansachs.com/insights/", "investment research", "national", "Consumer class, premiumisation and category expansion."),
    S("mckinsey", "McKinsey & Company", "India Consumer Insights", 2024, "https://www.mckinsey.com/featured-insights/india", "consulting research", "national", "Consumption, income growth and channel shifts."),
    S("bcg", "Boston Consulting Group", "India Consumer and Retail", 2024, "https://www.bcg.com/publications", "consulting research", "national", "Premiumisation, Bharat consumers and distribution."),
    S("meta_bcg", "BCG / Meta", "Bharat Consumer Survey", 2023, "https://www.bcg.com/publications", "industry survey", "national / tier 2-4", "Digital behaviour and aspiration in smaller towns."),
    S("hul", "Hindustan Unilever Limited", "Annual Report 2023-24", 2024, "https://www.hul.co.in/investor-relations/annual-reports/", "company filing", "national", "Rural/urban FMCG demand, premium portfolio, distribution."),
    S("price", "People Research on India's Consumer Economy", "Indian Consumer Economy", 2024, "https://www.priceindia.org/", "independent research", "national / state", "Household income classes and consumption segments."),
    S("cmie", "Centre for Monitoring Indian Economy", "Consumer Pyramids Household Survey", 2024, "https://www.cmie.com/", "private survey", "national / state", "Income, employment and consumption panel."),
    S("oxfam", "Oxfam India", "India Inequality Report", 2022, "https://www.oxfamindia.org/inequality-report-2022", "civil society report", "national", "Wealth and consumption inequality; treat as advocacy evidence."),
    S("pew", "Pew Research Center", "Religion in India: Tolerance and Segregation", 2021, "https://www.pewresearch.org/religion/2021/06/29/religion-in-india-tolerance-and-segregation/", "public survey", "national", "Religious identity, practice, mixing and attitudes."),
    S("ihds", "University of Maryland / NCAER", "India Human Development Survey", 2018, "https://ihds.umd.edu/", "public survey", "national / state", "Caste, gender, education, health and social networks."),
    S("sec_census", "Ministry of Rural Development", "Socio-Economic and Caste Census 2011", 2011, "https://secc.gov.in/", "government census", "national / state", "Rural deprivation, caste and household assets."),
    S("worldbank", "World Bank", "India Development Update and Data", 2025, "https://data.worldbank.org/country/india", "multilateral data", "national", "Poverty, urbanisation, growth and service access."),
    S("imf", "International Monetary Fund", "India Country Data", 2025, "https://www.imf.org/en/Countries/IND", "multilateral data", "national", "Macro context and consumption growth."),
    S("mpa", "Media Partners Asia", "India Video and OTT", 2024, "https://www.mediapartnersasia.com/", "industry research", "national", "OTT subscribers, revenue and content spend."),
    S("counterpoint", "Counterpoint Research", "India Smartphone and Device Market", 2025, "https://www.counterpointresearch.com/", "industry research", "national", "Smartphone ASP, replacement cycles and premium mix."),
    S("idc", "IDC India", "Consumer Device Tracker", 2024, "https://www.idc.com/", "industry research", "national", "PC, tablet and wearable adoption."),
    S("nrai", "National Restaurant Association of India", "India Food Services Report", 2024, "https://www.nrai.in/", "industry report", "national / city", "Eating out, QSR and food delivery."),
    S("barc", "Broadcast Audience Research Council", "TV Audience Measurement", 2024, "https://www.barcindia.co.in/", "industry data", "national / state", "TV households, viewing and language markets."),
    S("prasar_bharati", "Prasar Bharati", "Doordarshan and All India Radio", 2024, "https://prasarbharati.gov.in/", "public broadcaster", "national", "Terrestrial and free-to-air reach in remote areas."),
    S("fssai", "Food Safety and Standards Authority of India", "Food Safety and Nutrition Regulations", 2024, "https://fssai.gov.in/", "regulator", "national", "Claims, fortification and labelling."),
    S("icmr", "Indian Council of Medical Research / NIN", "Dietary Guidelines for Indians", 2024, "https://www.icmr.gov.in/", "government research", "national", "Nutrition gaps, protein and ultra-processed food."),
    S("ministry_education", "Ministry of Education", "Education Statistics", 2024, "https://www.education.gov.in/", "government data", "national / state", "Enrolment, dropout and institutions."),
    S("niti_sdg", "NITI Aayog", "SDG India Index", 2024, "https://www.niti.gov.in/sdg-india-index", "government index", "state / district", "State performance on health, education, gender, infrastructure."),
    S("google_temasek_bain", "Google / Temasek / Bain", "e-Conomy India", 2024, "https://www.bain.com/insights/e-conomy-india/", "industry report", "national", "Internet economy, digital consumption and inclusion."),
    S("crisil", "CRISIL", "India Consumption and Mobility", 2024, "https://www.crisil.com/", "rating agency research", "national / state", "Income, spending and category resilience."),
    S("ncaer", "NCAER", "National Council of Applied Economic Research", 2024, "https://www.ncaer.org/", "independent research", "national / state", "Household income and consumer sentiment."),
    S("lokniti", "Lokniti-CSDS", "National Election and Society Surveys", 2024, "https://www.lokniti.org/", "public survey", "national / state", "Social attitudes, trust and political economy."),
    S("ficci", "FICCI", "India Consumer and Retail Reports", 2024, "https://www.ficci.in/", "industry body", "national", "Retail, FMCG and MSME context."),
]


def F(id, dimension, claim, value, unit, year, source_ids, tags, detail, confidence="high"):
    return {
        "id": id, "dimension": dimension, "claim": claim, "value": value,
        "unit": unit, "year": year, "source_ids": source_ids, "tags": tags,
        "detail": detail, "confidence": confidence, "geo": "India",
    }


FACTS = [
    # geography / urbanisation
    F("geo_urban_share", "geography", "Urban share of population", "31.2", "%", 2011, ["census2011"], ["urban", "rural", "tier"], "Census 2011. The 2011 definition undercounts peri-urban growth; World Bank later estimates are higher.", "high"),
    F("geo_urban_pop", "geography", "Urban population", "377", "million", 2011, ["census2011"], ["urban"], "Census 2011. India added more urban residents in 2001-11 than in any previous decade.", "high"),
    F("geo_rural_pop", "geography", "Rural population", "834", "million", 2011, ["census2011"], ["rural", "village"], "Census 2011. Rural India is not a residual category; it is the majority of demand for many categories.", "high"),
    F("geo_villages", "geography", "Census villages", "640,867", "villages", 2011, ["census2011"], ["village", "rural", "last mile"], "Census 2011. Roughly 6 lakh inhabited villages; a single district can contain more than 1,000.", "high"),
    F("geo_statutory_towns", "geography", "Statutory towns", "4,041", "towns", 2011, ["census2011"], ["town", "urban"], "Census 2011. Municipal boundaries lag settlement growth, so many 'rural' households are functionally urban.", "high"),
    F("geo_census_towns", "geography", "Census towns", "3,894", "towns", 2011, ["census2011"], ["town", "peri-urban"], "Census 2011. Census towns are settlements that cross the urban threshold without a municipal government.", "high"),
    F("geo_metros_1m", "geography", "Urban agglomerations above 1 million", "53", "agglomerations", 2011, ["census2011"], ["metro", "tier 1"], "Census 2011. Metro India is a small share of population but a large share of premium demand.", "high"),
    F("geo_tn_urban", "geography", "Tamil Nadu urbanisation", "48.4", "%", 2011, ["census2011"], ["tamil nadu", "south", "urban"], "Census 2011. Among the most urbanised large states; strong secondary towns, not just Chennai.", "high"),
    F("geo_kerala_urban", "geography", "Kerala urbanisation", "47.7", "%", 2011, ["census2011"], ["kerala", "south", "urban"], "Census 2011. Dispersed urbanisation; high human development and remittance exposure.", "high"),
    F("geo_mh_urban", "geography", "Maharashtra urbanisation", "45.2", "%", 2011, ["census2011"], ["maharashtra", "west", "urban"], "Census 2011. Mumbai dominates, but Pune, Nashik and Nagpur carry distinct consumption cultures.", "high"),
    F("geo_up_urban", "geography", "Uttar Pradesh urbanisation", "22.3", "%", 2011, ["census2011"], ["uttar pradesh", "north", "urban"], "Census 2011. Large rural base; tier-2 towns like Lucknow, Kanpur, Varanasi and Gorakhpur matter.", "high"),
    F("geo_bihar_urban", "geography", "Bihar urbanisation", "11.3", "%", 2011, ["census2011"], ["bihar", "east", "rural"], "Census 2011. India's least urbanised large state; migration is a core household strategy.", "high"),
    F("geo_delhi_pop", "geography", "Delhi population", "16.8", "million", 2011, ["census2011"], ["delhi", "metro"], "Census 2011. High income dispersion inside one city; 'Delhi' is not one market.", "high"),
    F("geo_mumbai_pop", "geography", "Mumbai population", "12.4", "million", 2011, ["census2011"], ["mumbai", "metro"], "Census 2011. Extreme space constraint and a very large rental/commuter economy.", "high"),
    F("geo_blr_pop", "geography", "Bengaluru population", "8.4", "million", 2011, ["census2011"], ["bengaluru", "metro", "south"], "Census 2011. Tech-led migration, gated housing and a large young renter population.", "high"),

    # income / consumption
    F("inc_mpce_rural", "income", "Monthly per-capita consumption expenditure, rural", "3,773", "₹ / month", 2023, ["hces2223"], ["mpce", "rural", "income"], "HCES 2022-23, nominal. The median household has far less discretionary income than metro averages suggest.", "high"),
    F("inc_mpce_urban", "income", "Monthly per-capita consumption expenditure, urban", "6,459", "₹ / month", 2023, ["hces2223"], ["mpce", "urban", "income"], "HCES 2022-23, nominal. Urban average is roughly 1.7x rural.", "high"),
    F("inc_food_rural", "consumption", "Food share of rural consumption", "46.4", "%", 2023, ["hces2223"], ["food", "rural", "budget"], "HCES 2022-23. Food remains the largest single block; a price shock crowds out everything else.", "high"),
    F("inc_food_urban", "consumption", "Food share of urban consumption", "39.2", "%", 2023, ["hces2223"], ["food", "urban", "budget"], "HCES 2022-23. Still high by middle-income country standards.", "high"),
    F("inc_mpi_headcount", "poverty", "Multidimensional poverty headcount", "11.28", "%", 2023, ["niti_mpi"], ["poverty", "mpi", "district"], "NITI Aayog National MPI 2023. National average hides district-level concentration.", "high"),
    F("inc_mpi_escape", "poverty", "People escaping multidimensional poverty, 2013-14 to 2022-23", "24.82", "crore", 2024, ["niti_mpi"], ["poverty", "mobility"], "NITI Aayog discussion paper, 2024. Improvement is real but uneven; newly non-poor households remain fragile.", "high"),
    F("inc_hh_size", "demography", "Average household size", "4.4", "people", 2021, ["nfhs5"], ["household", "family"], "NFHS-5. Joint and multi-generational households still shape purchase permission.", "high"),
    F("inc_premiumisation", "consumption", "Premiumisation", "uneven", "qualitative", 2024, ["hul", "nielseniq", "gs_consumer"], ["premium", "fmcg", "class"], "Premium packs grow faster in metros and affluent tier-2, while mass and sachet packs still dominate volume in tier-3/4.", "medium"),
    F("inc_income_volatility", "income", "Income volatility", "high", "qualitative", 2024, ["cmie", "plfs2324", "worldbank"], ["income", "informal", "risk"], "A large share of households earn from informal, seasonal or piece-rate work; monthly affordability is not stable.", "high"),
    F("inc_credit_dependence", "finance", "Household credit dependence", "rising", "qualitative", 2024, ["rbi_fi", "crisil"], ["credit", "emi", "bnpl"], "Consumer credit and EMI penetration are rising, but access is uneven and informal borrowing remains common.", "medium"),
    F("inc_class_definition", "class", "Middle-class definition", "contested", "qualitative", 2024, ["price", "cmie", "worldbank"], ["class", "middle class"], "Estimates range from 100m to 500m+ depending on income thresholds. Treat 'middle class' as a spectrum, not a badge.", "medium"),

    # caste / religion / gender
    F("id_hindu", "religion", "Hindu share", "79.8", "%", 2011, ["census_religion"], ["religion", "hindu"], "Census 2011. National average masks state-level variation.", "high"),
    F("id_muslim", "religion", "Muslim share", "14.2", "%", 2011, ["census_religion"], ["religion", "muslim"], "Census 2011. Concentrated in specific states and districts; not a monolith.", "high"),
    F("id_christian", "religion", "Christian share", "2.3", "%", 2011, ["census_religion"], ["religion", "christian"], "Census 2011. Significant in Kerala, Goa and much of the Northeast.", "high"),
    F("id_sikh", "religion", "Sikh share", "1.7", "%", 2011, ["census_religion"], ["religion", "sikh"], "Census 2011. Punjab and adjoining states; strong diaspora and gurdwara networks.", "high"),
    F("id_buddhist", "religion", "Buddhist share", "0.7", "%", 2011, ["census_religion"], ["religion", "buddhist"], "Census 2011. Maharashtra (Dalit Buddhist movement), Ladakh and the Northeast.", "high"),
    F("id_jain", "religion", "Jain share", "0.4", "%", 2011, ["census_religion"], ["religion", "jain"], "Census 2011. Small share, disproportionate presence in trade and finance.", "high"),
    F("id_sc", "caste", "Scheduled Castes", "16.6", "%", 2011, ["census2011", "sec_census"], ["caste", "sc", "deprivation"], "Census 2011. Caste remains a structural marker of access, network and consumption risk.", "high"),
    F("id_st", "caste", "Scheduled Tribes", "8.6", "%", 2011, ["census2011", "sec_census"], ["caste", "st", "tribal"], "Census 2011. Concentrated in central, eastern and northeastern India; distinct land and forest rights.", "high"),
    F("id_sex_ratio", "gender", "Sex ratio", "1,020", "females / 1,000 males", 2021, ["nfhs5"], ["gender", "sex ratio"], "NFHS-5 household population. Improves on Census 2011 but hides regional skew.", "high"),
    F("id_women_internet", "gender", "Women who have ever used the internet", "33.3", "%", 2021, ["nfhs5"], ["gender", "digital", "internet"], "NFHS-5. Men: roughly 57%. The gender digital gap is a direct constraint on reach.", "high"),
    F("id_men_internet", "gender", "Men who have ever used the internet", "57.1", "%", 2021, ["nfhs5"], ["gender", "digital", "internet"], "NFHS-5. Device sharing often hides women's actual access.", "high"),
    F("id_female_lfpr", "gender", "Female labour force participation", "41.7", "%", 2024, ["plfs2324"], ["gender", "work", "lfpr"], "PLFS 2023-24, usual status. Rising but still low; unpaid care work is a major constraint.", "high"),
    F("id_child_marriage", "gender", "Women aged 20-24 married before 18", "23.3", "%", 2021, ["nfhs5"], ["gender", "marriage", "norms"], "NFHS-5. Varies sharply by state; affects education, mobility and consumption agency.", "high"),
    F("id_caste_gap", "caste", "Caste consumption gap", "persistent", "qualitative", 2024, ["ihds", "sec_census", "oxfam"], ["caste", "inequality", "consumption"], "SC/ST and OBC households remain over-represented in lower consumption deciles and informal work.", "medium"),
    F("id_religion_mixing", "religion", "Inter-religious social mixing", "low", "qualitative", 2021, ["pew"], ["religion", "trust", "community"], "Pew 2021 finds high stated tolerance but low everyday mixing; trust is often community-bounded.", "medium"),
    F("id_gender_mobility", "gender", "Women's mobility and purchase agency", "constrained", "qualitative", 2024, ["nfhs5", "ihds"], ["gender", "mobility", "permission"], "Many purchases require a father, husband or elder's permission; women-only channels and home delivery reduce friction.", "medium"),

    # jobs / education
    F("job_lfpr", "jobs", "Labour force participation rate", "60.1", "%", 2024, ["plfs2324"], ["jobs", "lfpr", "employment"], "PLFS 2023-24, usual status (15+).", "high"),
    F("job_unemployment", "jobs", "Unemployment rate", "3.2", "%", 2024, ["plfs2324"], ["jobs", "unemployment"], "PLFS 2023-24. Low headline rate coexists with underemployment and low-quality work.", "high"),
    F("job_informal", "jobs", "Informal employment share", "~90", "%", 2024, ["plfs2324", "cmie"], ["jobs", "informal", "msme"], "Most workers are self-employed, casual or in enterprises without formal contracts.", "medium"),
    F("job_gig", "jobs", "Gig workers", "7.7", "million", 2022, ["niti_adp", "plfs2324"], ["gig", "platform", "jobs"], "NITI Aayog 2022 estimate; projected 23.5 million by 2029-30. Definitional debates are large.", "medium"),
    F("job_msme_units", "jobs", "MSME units", "63", "million", 2024, ["ficci", "worldbank"], ["msme", "enterprise", "jobs"], "Broad estimate including micro-enterprises; most employ fewer than five people.", "medium"),
    F("job_agri_share", "jobs", "Agriculture share of employment", "45.8", "%", 2023, ["plfs2324"], ["agriculture", "rural", "jobs"], "PLFS 2022-23. Falling slowly; still the largest rural employer.", "high"),
    F("edu_college_enrolment", "education", "Higher-education enrolment", "43.3", "million", 2022, ["aishe"], ["college", "education", "youth"], "AISHE 2021-22. Gross enrolment ratio around 28%; huge state variation.", "high"),
    F("edu_ger", "education", "Gross enrolment ratio, higher education", "28.4", "%", 2022, ["aishe"], ["college", "education"], "AISHE 2021-22. Enrolment is concentrated in arts, science and commerce; employability is a separate problem.", "high"),
    F("edu_neet", "education", "NEET aspirants", "24", "lakh", 2024, ["ministry_education"], ["coaching", "college", "exam"], "Approximate candidate volume; coaching hubs like Kota and Hyderabad are their own micro-economies.", "medium"),
    F("edu_asER", "education", "14-18 learning and digital access", "uneven", "qualitative", 2024, ["aser"], ["school", "learning", "digital"], "ASER 2023 finds most 14-18-year-olds enrolled, but large gaps in reading, maths and access to a smartphone at home.", "high"),
    F("edu_college_culture", "education", "College culture", "status-defining", "qualitative", 2024, ["aser", "aishe"], ["college", "youth", "status"], "College is a status market: city, course, hostel, phone, clothes and 'exposure' all signal class.", "medium"),
    F("job_sarkari_status", "jobs", "Government job prestige", "high", "qualitative", 2024, ["lokniti", "cmie"], ["jobs", "status", "security"], "A permanent government job remains a marriage-market and family-status asset, especially in the Hindi belt.", "medium"),

    # digital / media
    F("dig_internet_subs", "digital", "Internet subscribers", "950", "million", 2025, ["trai"], ["internet", "telecom"], "TRAI subscriber data. Subscriptions overstate unique users because of multiple SIMs and shared devices.", "high"),
    F("dig_active_users", "digital", "Active internet users", "958", "million", 2025, ["iamai"], ["internet", "rural"], "IAMAI-Kantar 2025. Rural users are now the majority of new additions.", "high"),
    F("dig_rural_share", "digital", "Rural share of internet users", "55", "%", 2025, ["iamai"], ["rural", "internet"], "Rural internet growth is real, but usage is shallower: entertainment, messaging and payments dominate.", "medium"),
    F("dig_smartphone_hh", "digital", "Households with a smartphone", "85.5", "%", 2025, ["cms_telecom"], ["smartphone", "device"], "MoSPI CMS Telecom 2025. Rural 82.1%, urban 91.3%; device sharing is common.", "high"),
    F("dig_telecom_subs", "digital", "Telephone subscribers", "1.15", "billion", 2025, ["trai"], ["telecom", "mobile"], "TRAI. India is a multi-SIM market; subscriber counts are not people counts.", "high"),
    F("dig_data_cost", "digital", "Mobile data affordability", "among the lowest", "qualitative", 2024, ["trai", "iamai"], ["data", "affordability"], "Cheap data is the single biggest reason for video-first behaviour in tier-2/3/4.", "high"),
    F("dig_upi", "payments", "UPI transactions", "172", "billion / year", 2025, ["npci_upi"], ["upi", "payments", "digital"], "FY2024-25 scale. High volume does not mean high balances or credit access.", "high"),
    F("dig_whatsapp", "media", "WhatsApp users", "500+", "million", 2024, ["iamai", "meta_bcg"], ["whatsapp", "messaging", "trust"], "WhatsApp is the de facto social graph, market and rumour network for much of India.", "medium"),
    F("dig_ott", "media", "OTT viewers", "500+", "million", 2024, ["mpa", "iamai"], ["ott", "video", "netflix"], "Reach is broad; paid subscriptions are much smaller and churn is high.", "medium"),
    F("dig_tv_hh", "media", "TV households", "210", "million", 2024, ["barc", "prasar_bharati"], ["tv", "media", "rural"], "TV remains the widest video reach, especially in rural and older segments; DD Free Dish matters in remote areas.", "medium"),
    F("dig_social_users", "media", "Social media users", "500+", "million", 2024, ["iamai"], ["social", "media"], "Platform mix shifts by tier: Instagram/YouTube in metros, ShareChat/Moj and WhatsApp status in smaller towns.", "medium"),
    F("dig_ecom_shoppers", "retail", "Online shoppers", "270", "million", 2024, ["bain_flipkart"], ["ecommerce", "online", "retail"], "Bain-Flipkart estimate. Most growth is now from tier-2/3, but basket sizes are smaller.", "medium"),
    F("dig_language", "language", "Preference for Indic languages online", "~90", "%", 2024, ["iamai"], ["language", "internet", "content"], "Most new internet users prefer content in their own language; English signals status but limits reach.", "medium"),
    F("dig_broadband_gap", "digital", "Rural broadband gap", "persistent", "qualitative", 2025, ["trai", "jjm"], ["broadband", "rural", "supply"], "Mobile coverage is broad; reliable fixed broadband and device quality are not. Shared phones constrain commerce.", "high"),

    # category / market
    F("cat_ev2w", "category", "Electric two-wheeler share of new sales", "5.4", "%", 2024, ["siam", "bnef"], ["ev", "two-wheeler", "mobility"], "FY2023-24 approximate. Highly concentrated in a few states and urban pockets.", "medium"),
    F("cat_ev3w", "category", "Electric three-wheeler share of new sales", "55", "%", 2024, ["siam", "bnef"], ["ev", "three-wheeler", "mobility"], "Commercial three-wheelers electrify faster because total cost of ownership is visible daily.", "medium"),
    F("cat_evcar", "category", "Electric car share of new car sales", "2.4", "%", 2024, ["siam", "bnef"], ["ev", "car", "premium"], "Small but growing; charging and resale anxiety remain the binding constraints outside metros.", "medium"),
    F("cat_chargers", "category", "Public EV charging points", "~30,000", "points", 2024, ["bnef", "mnre"], ["ev", "charging", "supply"], "Heavily concentrated in Maharashtra, Delhi, Karnataka, Tamil Nadu and Gujarat.", "low"),
    F("cat_qcom", "category", "Quick commerce GMV", "$6-7", "billion", 2024, ["redseer", "bain_flipkart"], ["quick commerce", "retail", "city"], "Concentrated in the top 10-12 cities; unit economics depend on order density.", "medium"),
    F("cat_darkstores", "category", "Dark stores", "5,000+", "stores", 2024, ["redseer"], ["quick commerce", "supply"], "Store density, not app downloads, is the real moat.", "medium"),
    F("cat_kirana", "category", "Kirana stores", "12", "million", 2024, ["kantar", "hul"], ["kirana", "retail", "distribution"], "Kiranas still handle the majority of FMCG volume; they are also credit providers and community nodes.", "high"),
    F("cat_modern_trade", "category", "Modern trade share of retail", "~12", "%", 2024, ["nielseniq", "hul"], ["modern trade", "retail"], "Modern trade is metro-skewed; general trade remains the default in smaller towns.", "medium"),
    F("cat_fmcg_rural", "category", "Rural share of FMCG demand", "~37", "%", 2024, ["hul", "nielseniq"], ["fmcg", "rural"], "Rural demand is volume-led and monsoon-sensitive; premium packs travel less well.", "medium"),
    F("cat_beauty", "category", "Beauty and personal care market", "~$20", "billion", 2023, ["hul", "nielseniq", "bcg"], ["beauty", "personal care", "premium"], "Mass skincare and hair oil dominate volume; premium beauty grows from a small base in metros.", "low"),
    F("cat_protein", "category", "Protein supplement market", "small but growing", "qualitative", 2024, ["icmr", "nielseniq"], ["protein", "health", "premium"], "Protein deficiency is widespread; supplements are an urban, gym-linked category with trust and adulteration concerns.", "medium"),
    F("cat_ott_paid", "category", "Paid OTT subscriptions", "~100", "million", 2024, ["mpa"], ["ott", "netflix", "subscription"], "Paid base is far smaller than reach; telecom bundles and mobile-only plans drive conversion.", "low"),
    F("cat_netflix", "category", "Netflix India strategy", "mobile-first", "qualitative", 2024, ["mpa"], ["netflix", "ott", "pricing"], "Netflix India relies on mobile-only plans, telecom bundles and local originals; household sharing is common.", "medium"),
    F("cat_telecom_arpu", "category", "Telecom ARPU", "~₹200", "₹ / month", 2024, ["trai"], ["telecom", "arpu", "price"], "Low ARPU limits operator investment; price hikes are politically and competitively constrained.", "medium"),
    F("cat_lpg", "category", "LPG coverage", "99.8", "%", 2024, ["ppac"], ["lpg", "energy", "household"], "Coverage is near-universal, but refill affordability and last-mile reliability vary.", "high"),
    F("cat_crude_import", "category", "Crude oil import dependence", "~88", "%", 2024, ["ppac"], ["oil", "energy", "macro"], "India imports most of its crude; global prices transmit quickly to household budgets.", "high"),
    F("cat_health_insurance", "category", "Population covered by health insurance", "~30", "%", 2022, ["nha", "irdai"], ["health", "insurance", "protection"], "Public schemes cover a large share; depth and hospital access are uneven. Out-of-pocket spending remains high.", "medium"),
    F("cat_solar", "category", "Rooftop solar", "small base", "qualitative", 2024, ["mnre", "bnef"], ["solar", "energy", "premium"], "Rooftop solar is growing from a small base; financing, roof rights and installer trust are barriers.", "medium"),
    F("cat_bnpl", "category", "Buy-now-pay-later", "regulated growth", "qualitative", 2024, ["rbi_payments", "crisil"], ["bnpl", "credit", "youth"], "Young, urban and thin-file consumers adopt BNPL; RBI has tightened unsecured credit and default norms.", "medium"),
    F("cat_coaching", "category", "Coaching economy", "large", "qualitative", 2024, ["ministry_education", "aser"], ["coaching", "education", "youth"], "Exam coaching is a household expense with high social pressure and weak consumer protection.", "medium"),

    # supply / infrastructure
    F("sup_cold_chain", "supply", "Cold-chain coverage", "fragmented", "qualitative", 2024, ["ficci", "worldbank"], ["cold chain", "agri", "supply"], "A large share of perishables still moves without reliable cold chain; wastage is concentrated at the farm-gate.", "medium"),
    F("sup_ev_charging", "supply", "EV charging concentration", "metro-skewed", "qualitative", 2024, ["bnef", "mnre"], ["ev", "charging", "tier 2"], "Public chargers cluster in a few states and cities; highway and small-town coverage is thin.", "high"),
    F("sup_qcom_cities", "supply", "Quick commerce city concentration", "top 10-12 cities", "qualitative", 2024, ["redseer"], ["quick commerce", "tier 2", "supply"], "Expansion beyond the top cities depends on density, rider supply and store economics.", "high"),
    F("sup_phc", "supply", "Primary health centre gaps", "persistent", "qualitative", 2024, ["nha", "niti_adp"], ["health", "rural", "supply"], "Staffing, diagnostics and drug availability vary widely; private providers fill the gap at a cost.", "medium"),
    F("sup_specialists", "supply", "Specialist doctor shortage", "concentrated in metros", "qualitative", 2024, ["nha"], ["health", "doctors", "supply"], "Specialists cluster in cities; district hospitals depend on visiting consultants and referral networks.", "medium"),
    F("sup_jjm", "infrastructure", "Rural households with tap water", "~80", "%", 2025, ["jjm"], ["water", "rural", "infrastructure"], "Jal Jeevan Mission coverage has risen fast; quality and reliability lag connection numbers.", "medium"),
    F("sup_sanitation", "infrastructure", "Improved sanitation coverage", "70.2", "%", 2021, ["nfhs5"], ["sanitation", "rural", "infrastructure"], "NFHS-5. Usage gaps and water availability matter more than toilet construction alone.", "high"),
    F("sup_roads", "infrastructure", "Road connectivity", "improving", "qualitative", 2024, ["worldbank", "mohua"], ["roads", "logistics", "rural"], "Road access has improved, but last-mile quality and transport costs still shape market access.", "medium"),
    F("sup_northeast", "supply", "Northeast logistics", "high-cost", "qualitative", 2024, ["niti_adp", "worldbank"], ["northeast", "logistics", "supply"], "Distance, terrain, inner-line permits and small markets raise landed costs and delay service.", "medium"),
    F("sup_power", "infrastructure", "Power reliability", "uneven", "qualitative", 2024, ["mnre", "worldbank"], ["power", "rural", "infrastructure"], "Grid reliability varies by state and season; inverter/battery ownership is a coping strategy.", "medium"),
    F("sup_insurance_density", "finance", "Insurance penetration", "4.0", "% of GDP", 2024, ["irdai"], ["insurance", "penetration", "finance"], "Life and non-life combined; protection gap is much larger than the headline.", "medium"),
    F("sup_banking", "finance", "Bank branch access", "uneven", "qualitative", 2024, ["rbi_fi"], ["banking", "rural", "access"], "Branch density is metro-heavy; business correspondents and UPI fill some gaps but not credit.", "medium"),
    F("sup_last_mile", "supply", "Last-mile delivery cost", "high outside metros", "qualitative", 2024, ["bain_flipkart", "redseer"], ["logistics", "tier 3", "supply"], "Address density and returns make tier-3/4 unit economics harder than metro averages.", "medium"),

    # culture / festival / status
    F("cul_festive_share", "festival", "Festive quarter share of annual sales", "40-50", "%", 2024, ["nielseniq", "hul", "bcg"], ["festival", "diwali", "demand"], "For many discretionary categories, Sep-Dec carries a disproportionate share of annual demand.", "medium"),
    F("cul_weddings", "festival", "Weddings per year", "~10", "million", 2024, ["ficci", "nrai"], ["wedding", "status", "consumption"], "Weddings are a major status and gifting market; spending is often socially benchmarked.", "low"),
    F("cul_gold", "status", "Gold as household asset", "core", "qualitative", 2024, ["rbi_payments", "worldbank"], ["gold", "status", "savings"], "Gold is savings, status and marriage security at once; price sensitivity is different from other categories.", "medium"),
    F("cul_car_status", "status", "Car as status good", "high", "qualitative", 2024, ["siam", "mckinsey"], ["car", "status", "class"], "In smaller towns a car signals family arrival; the neighbour's car is a reference price.", "medium"),
    F("cul_phone_status", "status", "Phone as status good", "high", "qualitative", 2025, ["counterpoint", "iamai"], ["phone", "status", "youth"], "The phone is the most visible everyday status marker; model, camera and brand matter more than specs.", "medium"),
    F("cul_house_status", "status", "House as status good", "high", "qualitative", 2024, ["pmayg", "worldbank"], ["house", "status", "family"], "A pucca house, a separate gate and a 'good address' are long-horizon status projects.", "medium"),
    F("cul_saree", "status", "Clothing and saree signalling", "high", "qualitative", 2024, ["nielseniq", "bcg"], ["clothing", "status", "gender"], "Clothing signals occasion, community and respectability; premium is read through fabric and brand, not just price.", "medium"),
    F("cul_log_kya", "norms", "Social surveillance ('log kya kahenge')", "strong", "qualitative", 2024, ["pew", "ihds", "lokniti"], ["norms", "status", "community"], "Purchase decisions are often family and community decisions; visible consumption invites judgement.", "medium"),
    F("cul_vastu", "norms", "Vastu, muhurat and auspicious timing", "persistent", "qualitative", 2024, ["lokniti", "ihds"], ["norms", "festival", "house"], "House, gold and vehicle purchases may be timed to auspicious dates; rational to the household even when it looks inefficient.", "medium"),
    F("cul_caste_network", "norms", "Caste and community trade networks", "persistent", "qualitative", 2024, ["ihds", "sec_census"], ["caste", "trade", "trust"], "Occupation and credit networks are still community-linked in many towns; trust travels through known networks.", "medium"),
    F("cul_jugaad", "norms", "Jugaad and repair culture", "strong", "qualitative", 2024, ["worldbank", "cmie"], ["jugaad", "repair", "informal"], "Households optimise for repairability, local spare parts and informal service, not just warranty terms.", "medium"),
    F("cul_neighbour_proof", "norms", "Neighbour proof", "decisive", "qualitative", 2024, ["meta_bcg", "kantar"], ["social proof", "trust", "word of mouth"], "One visible owner in the same street or apartment block outweighs a national ad for high-involvement purchases.", "medium"),
    F("cul_local_dealer", "norms", "Local dealer trust", "decisive", "qualitative", 2024, ["siam", "hul"], ["dealer", "trust", "service"], "The dealer is the product's face; service access and resale value are judged through them.", "medium"),
    F("cul_education_mobility", "norms", "Education as mobility", "strong", "qualitative", 2024, ["aser", "aishe"], ["education", "aspiration", "class"], "Families sacrifice current consumption for children's English-medium education and exam coaching.", "medium"),
    F("cul_regional_pride", "norms", "Regional and language pride", "strong", "qualitative", 2024, ["lokniti", "iamai"], ["language", "region", "identity"], "Campaigns that use the local language and local references travel further than translated metro creative.", "medium"),
    F("cul_colourism", "norms", "Colour and fairness bias", "persistent", "qualitative", 2024, ["ihds", "nielseniq"], ["colour", "beauty", "status"], "Fairness products and matrimonial preferences show colourism is still a market force; treat it as a bias to model, not endorse.", "medium"),
    F("cul_posh_area", "status", "Posh-area signalling", "strong", "qualitative", 2024, ["mckinsey", "bcg"], ["posh", "address", "class"], "Addresses like South Delhi, South Mumbai, Jubilee Hills, Koramangala or Alipore carry social meaning beyond amenities.", "medium"),
    F("cul_college_hubs", "culture", "College hubs", "distinct markets", "qualitative", 2024, ["aishe", "aser"], ["college", "youth", "city"], "Kota, Hyderabad, Pune, Bengaluru, Delhi North Campus and Chennai have their own student economies and status codes.", "medium"),
    F("cul_migration_remittance", "culture", "Migration and remittance obligations", "core", "qualitative", 2024, ["census_migration", "worldbank"], ["migration", "remittance", "family"], "Migrants often support a village household; spending is negotiated across two locations.", "medium"),
    F("cul_service_trust", "norms", "Service network as trust", "decisive", "qualitative", 2024, ["siam", "bnef"], ["service", "trust", "after-sales"], "The perceived distance to a service centre is a direct price on risk, especially for vehicles and durables.", "medium"),
    F("cul_whatsapp_rumour", "norms", "WhatsApp forward authority", "high", "qualitative", 2024, ["iamai", "pew"], ["whatsapp", "misinformation", "trust"], "Forwards from a trusted contact can outweigh official corrections; fact-checking must travel through the same network.", "medium"),
    F("cul_status_avoidance", "norms", "Avoiding visible show-off", "contextual", "qualitative", 2024, ["lokniti", "ihds"], ["status", "small town", "norms"], "In small communities, visible excess can invite envy or suspicion; understatement is sometimes the safer signal.", "medium"),
]


REGIONS = [
    {
        "id": "north", "name": "North", "states": ["Delhi", "Haryana", "Punjab", "Uttar Pradesh", "Uttarakhand", "Rajasthan", "Himachal Pradesh", "Jammu & Kashmir", "Ladakh", "Chandigarh"],
        "summary": "Agrarian hinterland, dense towns, strong status competition and family-mediated purchases.",
        "consumption": "Festival and wedding spending are highly visible; gold, vehicles and electronics carry family prestige. Sachets and EMI bridge irregular cash flows.",
        "gender": "Women's mobility and paid work vary sharply by community and state; purdah, safety and family permission still shape access.",
        "status": "Address, vehicle, phone and children's English-medium schooling are the core status markers.",
        "constraints": "Seasonal income, groundwater stress, air pollution, weak last-mile service in small towns.",
        "culture": "Hindi belt sociality, caste networks, temple towns, migration to Delhi/NCR and Punjab-to-abroad links.",
        "source_ids": ["census2011", "nfhs5", "hces2223", "plfs2324", "pew", "ihds"],
    },
    {
        "id": "south", "name": "South", "states": ["Tamil Nadu", "Kerala", "Karnataka", "Telangana", "Andhra Pradesh", "Puducherry", "Lakshadweep", "Andaman & Nicobar Island"],
        "summary": "Higher urbanisation, stronger human development, language pride and a dense tier-2 town network.",
        "consumption": "Education, healthcare and durable goods are prioritised; filter coffee, rice, gold and silk carry cultural weight. Premium adoption travels through tier-2 towns faster than in the north.",
        "gender": "Kerala and Tamil Nadu show comparatively better female literacy and mobility, but paid work and safety still vary.",
        "status": "Education, house, car and children's professional careers; 'good family' matters more than display in some communities.",
        "constraints": "Water stress, congestion, high land prices, dependence on inter-state migrant labour.",
        "culture": "Temple festivals, classical arts, film and language politics; Bengaluru and Hyderabad are tech-migration cities.",
        "source_ids": ["census2011", "nfhs5", "hces2223", "plfs2324", "aishe", "iamai"],
    },
    {
        "id": "west", "name": "West", "states": ["Maharashtra", "Gujarat", "Goa", "Dadara & Nagar Havelli"],
        "summary": "Trade-led, entrepreneurial, highly urban and deeply connected to global commodity and migration flows.",
        "consumption": "Gujarat's business networks and Maharashtra's metro aspiration create a wide spread: from diamond workers to luxury South Mumbai. Credit and dealer relationships are central.",
        "gender": "Female work participation varies; Goa and urban Maharashtra are more liberal, while conservative pockets persist.",
        "status": "Business scale, property, gold and vehicles; community reputation is a credit asset.",
        "constraints": "Housing cost, water, congestion, migrant labour dependence, cyclical commodity exposure.",
        "culture": "Garba, Ganesh Chaturthi, Diwali, business-family networks, Bollywood and a strong cooperative tradition.",
        "source_ids": ["census2011", "nfhs5", "hces2223", "plfs2324", "rbi_fi", "bcg"],
    },
    {
        "id": "east", "name": "East", "states": ["West Bengal", "Bihar", "Jharkhand", "Odisha", "Assam", "Sikkim"],
        "summary": "Young, rural-heavy and migration-linked, with strong cultural identity and uneven industrialisation.",
        "consumption": "Price sensitivity is high; sachets, second-hand goods and local repair markets matter. Festivals like Durga Puja and Chhath drive concentrated spending.",
        "gender": "Women's work is rising in some pockets but mobility remains constrained; migration of men reshapes households.",
        "status": "Education, government jobs, land and house; Kolkata's cultural capital carries regional prestige.",
        "constraints": "Floods, weak industrial base, transport costs, limited formal credit, out-migration.",
        "culture": "Bengali, Odia, Assamese and tribal identities; tea, fish, rice and strong literary/film traditions.",
        "source_ids": ["census2011", "nfhs5", "hces2223", "plfs2324", "census_migration", "niti_mpi"],
    },
    {
        "id": "central", "name": "Central", "states": ["Madhya Pradesh", "Chhattisgarh"],
        "summary": "Agrarian and forest-dependent, with large tribal populations and significant poverty concentration.",
        "consumption": "Food and fuel dominate budgets; durable purchases are deferred and often financed through informal credit or gold.",
        "gender": "Early marriage and low female mobility persist in many districts; SHG networks are a countervailing force.",
        "status": "Land, house, motorcycle and children's education; display is moderated by community norms.",
        "constraints": "Rainfed agriculture, forest rights, poor connectivity, health and education gaps.",
        "culture": "Tribal festivals, folk music, pilgrimage towns and Hindi-language media.",
        "source_ids": ["census2011", "nfhs5", "hces2223", "niti_mpi", "sec_census", "jjm"],
    },
    {
        "id": "northeast", "name": "Northeast", "states": ["Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Tripura"],
        "summary": "Distinct ethnic and linguistic identities, high literacy in places, and severe logistics constraints.",
        "consumption": "Small markets, high landed costs and strong community networks. Christianity, tribal customs and local languages shape trust.",
        "gender": "Matrilineal pockets (Khasi, Garo) contrast with patrilineal communities; women's market presence is visible.",
        "status": "Community standing, education and government employment; outside brands must earn local legitimacy.",
        "constraints": "Terrain, inner-line permits, small market size, poor road/air connectivity, limited service networks.",
        "culture": "Hornbill, Bihu, Sangai and tribal festivals; music, football and local fashion are strong identity markers.",
        "source_ids": ["census2011", "nfhs5", "census_religion", "niti_adp", "worldbank", "iamai"],
    },
]


NORMS = [
    ("norm_family_permission", "Family permission for large purchases", "Big-ticket decisions are negotiated with parents, spouses and sometimes elders; a lone 'consumer' is the exception.", ["1", "2", "3", "4"], ["north", "east", "central"], "Raises the bar for high-involvement categories; family demos and guarantor-friendly finance help.", ["nfhs5", "ihds"]),
    ("norm_neighbour_proof", "Neighbour proof", "One visible owner in the same street, block or WhatsApp group is stronger evidence than a national ad.", ["2", "3", "4"], ["north", "west", "east", "central"], "Accelerates adoption after first local owner; also accelerates rejection after a visible failure.", ["meta_bcg", "kantar"]),
    ("norm_dealer_trust", "Dealer as guarantor", "The local dealer is judged on service, resale and whether they will still be there next year.", ["2", "3", "4"], ["north", "east", "central", "northeast"], "Service density and dealer reputation are adoption infrastructure.", ["siam", "hul"]),
    ("norm_log_kya", "Log kya kahenge", "Visible consumption is read as character; families avoid shame and envy as much as they seek prestige.", ["2", "3", "4"], ["north", "central", "east"], "Can suppress show-off categories and boost 'safe' premium signals (education, gold, house).", ["pew", "lokniti"]),
    ("norm_jugaad", "Jugaad and repair", "Households optimise for repairability, local spare parts and informal service over official warranty.", ["2", "3", "4"], ["north", "east", "central", "west"], "Favours modular, repairable products; punishes sealed, service-dependent designs.", ["worldbank", "cmie"]),
    ("norm_scheme_legitimacy", "Government scheme legitimacy", "A scheme or subsidy can legitimise a category, but paperwork and last-mile delivery decide take-up.", ["2", "3", "4"], ["north", "east", "central"], "Policy scenarios should model friction, not just price cuts.", ["jjm", "pmayg", "niti_adp"]),
    ("norm_festival_timing", "Auspicious timing", "Purchases may be timed to festivals, muhurat or harvest cash; demand is lumpy and socially coordinated.", ["1", "2", "3", "4"], ["north", "south", "west", "east", "central"], "Festival scenarios should lift both demand and price tolerance, then decay.", ["nielseniq", "lokniti"]),
    ("norm_gold_security", "Gold as security", "Gold is savings, marriage insurance and status; it competes with financial products for the same rupee.", ["1", "2", "3", "4"], ["north", "south", "west", "east"], "Financial products must beat gold on trust and liquidity, not only returns.", ["rbi_payments", "worldbank"]),
    ("norm_education_sacrifice", "Education as sacrifice", "Families cut current consumption for English-medium schooling, coaching and college.", ["1", "2", "3"], ["north", "south", "west", "east", "central"], "Education categories have unusual price tolerance and long decision cycles.", ["aser", "aishe"]),
    ("norm_language_identity", "Language as identity", "Local-language creative signals respect; English-only creative signals distance.", ["1", "2", "3", "4"], ["north", "south", "west", "east", "central", "northeast"], "Localisation is not translation; idiom and reference matter.", ["iamai", "lokniti"]),
    ("norm_colourism", "Colourism", "Fairness and colour bias shape beauty, matrimony and self-presentation.", ["1", "2", "3", "4"], ["north", "south", "west", "east", "central"], "Model as a bias with ethical caveats; do not present it as a recommendation.", ["ihds", "nielseniq"]),
    ("norm_womens_safety", "Women's safety and reputation", "Mobility, evening use and solo travel are negotiated against family honour and safety.", ["1", "2", "3", "4"], ["north", "central", "east"], "Products that reduce safety friction (home delivery, verified drivers, women-only services) travel faster.", ["nfhs5", "ihds"]),
    ("norm_whatsapp_authority", "WhatsApp forward authority", "A forward from a trusted contact can outweigh an official correction.", ["2", "3", "4"], ["north", "south", "west", "east", "central", "northeast"], "Fact-checking must travel through the same network; mass media alone does not correct it.", ["iamai", "pew"]),
    ("norm_status_understatement", "Status understatement", "In small communities, visible excess can invite envy; understatement is sometimes safer.", ["3", "4"], ["north", "central", "east"], "Premium brands need a 'quiet' variant and a local legitimacy story.", ["lokniti", "ihds"]),
    ("norm_service_distance", "Service distance as risk", "The distance to a service centre is priced into the purchase, especially for vehicles and durables.", ["2", "3", "4"], ["north", "east", "central", "northeast"], "Service guarantees matter more than feature lists outside metros.", ["siam", "bnef"]),
    ("norm_migration_obligation", "Migration obligation", "Migrant earnings support a village household; spending is negotiated across two locations.", ["2", "3", "4"], ["east", "central", "north"], "Remittance cycles create seasonal demand and conservative risk appetite.", ["census_migration", "worldbank"]),
]


CATEGORY_PRIORS = [
    # topic_id, price_sensitivity, status_signal, supply_constraint, trust_barrier, peer_effect, penetration_note, source_ids
    ("ev-car", .72, .82, .78, .74, .62, "2.4% of new car sales; charging and resale anxiety dominate outside metros.", ["siam", "bnef"]),
    ("ev-scooter", .68, .58, .66, .62, .70, "5.4% of new two-wheeler sales; service density is the real constraint.", ["siam", "bnef"]),
    ("quick-commerce", .42, .38, .74, .46, .66, "Top-10-city phenomenon; density and rider supply decide economics.", ["redseer", "bain_flipkart"]),
    ("upi-rural", .18, .12, .52, .38, .72, "High transaction volume; rural usage is shallower and cash still dominates small purchases.", ["npci_upi", "rbi_payments"]),
    ("ai-jobs", .48, .66, .58, .52, .48, "Urban, educated adoption; anxiety about replacement is as strong as aspiration.", ["iamai", "plfs2324"]),
    ("edtech", .62, .72, .44, .58, .54, "Exam-driven demand; trust collapses after outcome failures.", ["aser", "aishe"]),
    ("health-insurance", .64, .48, .62, .78, .40, "~30% covered; hospital networks and claim rejection drive distrust.", ["nha", "irdai"]),
    ("rural-credit", .58, .34, .68, .64, .52, "Informal credit persists; formal loans are constrained by documentation and cash flow.", ["rbi_fi", "mgnrega"]),
    ("premium-fmcg", .46, .62, .38, .44, .58, "Premium packs grow in metros and affluent tier-2; sachets still dominate volume.", ["hul", "nielseniq"]),
    ("ott", .38, .42, .30, .34, .48, "500m+ reach, ~100m paid; telecom bundles and sharing blur conversion.", ["mpa", "iamai"]),
    ("solar-rooftop", .76, .54, .72, .70, .44, "Small base; financing, roof rights and installer trust are barriers.", ["mnre", "bnef"]),
    ("gig-work", .44, .38, .56, .52, .46, "7.7m+ gig workers; earnings volatility and safety are core objections.", ["niti_adp", "plfs2324"]),
    ("women-work", .52, .58, .64, .60, .56, "Female LFPR 41.7%; safety, care work and family permission bind.", ["plfs2324", "nfhs5"]),
    ("misinformation", .16, .24, .22, .72, .78, "WhatsApp-forward ecosystem; correction must travel through trusted networks.", ["iamai", "pew"]),
    ("agri-tech", .66, .36, .76, .62, .48, "Fragmented holdings, cold chain and credit access limit adoption.", ["worldbank", "ficci"]),
    ("bnpl", .52, .48, .36, .56, .50, "Young urban adoption; RBI tightening and default risk reshape the category.", ["rbi_payments", "crisil"]),
    ("language-ai", .34, .46, .44, .52, .52, "Most new users prefer Indic languages; trust and accuracy are unresolved.", ["iamai", "aishe"]),
    ("coaching", .70, .78, .38, .56, .62, "Exam coaching is a status and anxiety market with weak consumer protection.", ["ministry_education", "aser"]),
    ("generic", .55, .50, .50, .55, .50, "Generic category prior; use only when no topic pack matches.", ["worldbank", "hces2223"]),
]


ANCHORS = [
    # topic_id, conversion, low, high, basis, source_ids
    ("ev-car", .55, .40, .68, "Early-adopter conversion among affluent car buyers; 2.4% of new car sales with charging anxiety.", ["siam", "bnef"]),
    ("ev-scooter", .45, .32, .58, "5.4% of new two-wheeler sales; service density and resale concerns.", ["siam", "bnef"]),
    ("quick-commerce", .62, .48, .74, "High conversion among urban internet households in served pin codes.", ["redseer", "bain_flipkart"]),
    ("upi-rural", .78, .68, .86, "High conversion once a bank account and smartphone exist; usage intensity is lower.", ["npci_upi", "rbi_fi"]),
    ("ai-jobs", .40, .28, .54, "Urban educated adoption; anxiety and skill gaps limit conversion.", ["iamai", "plfs2324"]),
    ("edtech", .35, .24, .48, "Exam-driven trial is high; paid conversion and retention are lower.", ["aser", "aishe"]),
    ("health-insurance", .30, .20, .42, "~30% population covered; trust and claim experience bind.", ["nha", "irdai"]),
    ("rural-credit", .42, .30, .55, "Formal credit conversion among banked rural households; informal credit remains substitutive.", ["rbi_fi", "mgnrega"]),
    ("premium-fmcg", .38, .28, .50, "Premium pack conversion among affluent urban households; mass volume stays in sachets.", ["hul", "nielseniq"]),
    ("ott", .55, .42, .68, "Paid conversion among reachable OTT viewers; bundles and sharing inflate reach.", ["mpa", "iamai"]),
    ("solar-rooftop", .22, .14, .32, "Small base; financing and roof rights are hard constraints.", ["mnre", "bnef"]),
    ("gig-work", .48, .36, .60, "Platform work conversion among urban youth; earnings volatility is the objection.", ["niti_adp", "plfs2324"]),
    ("women-work", .28, .18, .40, "Female LFPR 41.7%; safety, care and permission constrain formal work.", ["plfs2324", "nfhs5"]),
    ("misinformation", .65, .52, .78, "Forwarding conversion is high; belief and correction are separate.", ["iamai", "pew"]),
    ("agri-tech", .30, .20, .42, "Fragmented holdings and cold-chain gaps limit paid adoption.", ["worldbank", "ficci"]),
    ("bnpl", .35, .24, .48, "Young urban thin-file adoption; regulatory tightening is a headwind.", ["rbi_payments", "crisil"]),
    ("language-ai", .45, .32, .58, "Indic-language preference is high; trust and accuracy limit paid use.", ["iamai", "aishe"]),
    ("coaching", .50, .38, .64, "Exam anxiety drives paid conversion; outcomes and refunds are contested.", ["ministry_education", "aser"]),
    ("generic", .40, .30, .52, "Generic anchor; use only when no topic pack matches.", ["worldbank", "hces2223"]),
]


def main():
    data = {
        "version": "2026.11-seed",
        "built": "2026-11-05",
        "scope_note": (
            "Curated public-data seed. It is not a census and not a trained foundation model. "
            "Indicators are cited; derived context nodes are generated from public distributions. "
            "Add documents with app/ingest.py to expand the corpus."
        ),
        "sources": SOURCES,
        "facts": FACTS,
        "regions": REGIONS,
        "norms": [
            dict(id=i, claim=c, detail=d, tiers=t, regions=r, effect=e, source_ids=s)
            for i, c, d, t, r, e, s in NORMS
        ],
        "category_priors": [
            dict(topic_id=t, price_sensitivity=p, status_signal=st, supply_constraint=sc,
                 trust_barrier=tb, peer_effect=pe, penetration_note=n, source_ids=s)
            for t, p, st, sc, tb, pe, n, s in CATEGORY_PRIORS
        ],
        "anchors": [
            dict(topic_id=t, conversion=c, low=lo, high=hi, basis=b, source_ids=s)
            for t, c, lo, hi, b, s in ANCHORS
        ],
    }
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    dims = {}
    for f in FACTS:
        dims[f["dimension"]] = dims.get(f["dimension"], 0) + 1
    print(f"wrote {OUT}")
    print(f"sources={len(SOURCES)} facts={len(FACTS)} regions={len(REGIONS)} norms={len(NORMS)} categories={len(CATEGORY_PRIORS)}")
    print("dims:", dict(sorted(dims.items())))


if __name__ == "__main__":
    main()
