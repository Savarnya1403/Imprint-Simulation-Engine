"""Language generation for feeds, debates and focus groups.

No external LLM is required: the simulator composes arguments from structured
topic packs, agent traits and evidence cards. This keeps every claim traceable
and makes the output reproducible. An optional LLM hook can be added later.
"""
from __future__ import annotations

import random
from typing import Any

from . import store


def money(v: float) -> str:
    if v >= 10000000:
        return f"₹{v/10000000:.1f}Cr"
    if v >= 100000:
        return f"₹{v/100000:.1f}L"
    if v >= 1000:
        return f"₹{v/1000:.0f}k"
    return f"₹{v:.0f}"


def pct(v: float) -> str:
    return f"{v*100:.0f}%"


def stance_label(v: float) -> str:
    if v >= .68:
        return "Strongly positive"
    if v >= .56:
        return "Positive"
    if v >= .45:
        return "Mixed"
    if v >= .33:
        return "Skeptical"
    return "Strongly negative"


def short_evidence(e: dict, max_len=150) -> str:
    s = f"{e['claim']}: {e['value']} {e['unit']}".strip()
    s = s.replace("  ", " ")
    if len(s) > max_len:
        s = s[:max_len - 1].rstrip() + "…"
    return s


def choose_evidence(topic: dict, rng: random.Random, k=1) -> list[dict]:
    emap = store.evidence_map()
    ids = topic.get("evidence_ids", [])
    pool = [emap[i] for i in ids if i in emap]
    if not pool:
        pool = list(emap.values())[:5]
    rng.shuffle(pool)
    return pool[:k]


def objection(agent: dict, topic: dict, rng: random.Random) -> str:
    obs = topic.get("objections", ["Price", "Trust", "Awareness", "Risk"])
    # weight objections by traits
    weights = []
    for o in obs:
        w = 1.0
        lo = o.lower()
        if "price" in lo or "cost" in lo or "premium" in lo:
            w += agent["traits"]["price"] * 2.2
        if "trust" in lo or "fraud" in lo or "claim" in lo:
            w += (1 - agent["traits"]["trust_gov"]) * 1.2 + agent["biases"]["loss_aversion"]
        if "service" in lo or "network" in lo or "maintenance" in lo:
            w += (1 - agent["traits"]["risk"]) * 1.4
        if "resale" in lo or "resale" in lo or "depreciation" in lo:
            w += agent["biases"]["loss_aversion"] * 2.0
        if "family" in lo or "permission" in lo or "safety" in lo:
            w += agent["traits"]["conformity"] * 1.8
        if "complex" in lo or "paperwork" in lo or "language" in lo:
            w += agent["biases"]["ambiguity"] * 2.0
        if "worker" in lo or "labour" in lo or "exploit" in lo:
            w += agent["traits"]["social_radius"] * 1.1
        weights.append(w)
    return rng.choices(obs, weights=weights)[0]


def benefit(agent: dict, topic: dict, rng: random.Random) -> str:
    return rng.choice(topic.get("benefits", ["Works better", "Saves money", "Saves time", "Feels premium"]))


def local_line(agent: dict, topic: dict, rng: random.Random, positive=True) -> tuple[str, str]:
    """Return a local-language line and an English gloss."""
    city = agent["city"]
    prod = topic["label"].lower()
    b = benefit(agent, topic, rng).lower()
    o = objection(agent, topic, rng).lower()
    lang = agent["language"]
    if lang == "Tamil":
        txt = (f"Namma {city} la {prod} pathi ellarum pesikitiranga. {b.capitalize()} nu solranga, aana {o} "
               f"pathi yaarum pesala. Neenga enna solreenga?")
        return txt, f"In {city}, everyone is talking about {prod}. They say {b}, but nobody talks about {o}. What do you think?"
    if lang == "Bengali":
        txt = (f"Amader {city} e {prod} niye charcha cholche. {b.capitalize()} bole, kintu {o} niye kew kotha bolche na. "
               f"Apnar ki mone hoy?")
        return txt, f"In {city}, people are discussing {prod}. They say {b}, but no one mentions {o}. What do you think?"
    if lang == "Marathi":
        txt = (f"Aamchya {city} madhe {prod} charcha suru ahe. {b.capitalize()} mhantat, pan {o} kuni bolat nahi. "
               f"Tumhala kay vatat?")
        return txt, f"In {city}, {prod} is being discussed. People say {b}, but no one mentions {o}. What do you think?"
    if lang == "Telugu":
        txt = (f"Mana {city} lo {prod} gurinchi andaru matladutunnaru. {b.capitalize()} ani antunnaru, kani {o} gurinchi evaru matladatledu. "
               f"Meeru emi anukuntunnaru?")
        return txt, f"In {city}, everyone is talking about {prod}. They say {b}, but no one discusses {o}. What do you think?"
    if lang == "Kannada":
        txt = (f"Namma {city} nalli {prod} bagge ellaru maatadtaiddare. {b.capitalize()} anta heltaare, aadare {o} bagge yaaru maatadilla. "
               f"Nimma abhipraya?")
        return txt, f"In {city}, people are discussing {prod}. They say {b}, but no one mentions {o}. What is your view?"
    if lang == "Malayalam":
        txt = (f"Nammude {city} il {prod} ine kurich ellarum samsarikkunnu. {b.capitalize()} ennu parayunnu, pakshe {o} kurich arum mindunnilla. "
               f"Ningalku enthu thonnunnu?")
        return txt, f"In {city}, everyone is talking about {prod}. They say {b}, but no one mentions {o}. What do you think?"
    if lang == "Gujarati":
        txt = (f"Aapna {city} ma {prod} ni charcha chale che. {b.capitalize()} kahe che, pan {o} vishe koi vaat karto nathi. "
               f"Tamne shu lage che?")
        return txt, f"In {city}, {prod} is being discussed. People say {b}, but no one mentions {o}. What do you think?"
    if lang == "Punjabi":
        txt = (f"Sade {city} vich {prod} di charcha chal rahi hai. {b.capitalize()} kehnde ne, par {o} bare koi nahi bolda. "
               f"Tuhanu ki lagda hai?")
        return txt, f"In {city}, people are discussing {prod}. They say {b}, but no one talks about {o}. What do you think?"
    if lang == "Odia":
        txt = (f"Amara {city} re {prod} nia charcha chalichi. {b.capitalize()} kuhanti, kintu {o} nia kehi kahunchanti nahin. "
               f"Apana kana bhabuchanti?")
        return txt, f"In {city}, people are discussing {prod}. They say {b}, but no one mentions {o}. What do you think?"
    if lang in ("Hindi", "Haryanvi", "Rajasthani"):
        txt = (f"{city} mein {prod} ki charcha tez hai. Log kehte hain {b}, lekin {o} par koi baat nahi karta. "
               f"Aap kya sochte hain?")
        return txt, f"In {city}, {prod} is trending. People say {b}, but no one talks about {o}. What do you think?"
    return "", ""


def post_text(agent: dict, topic: dict, rng: random.Random, platform: str, stance: float) -> dict:
    tone = "positive" if stance >= .62 else "mixed" if stance >= .47 else "skeptical" if stance >= .34 else "negative"
    if tone == "mixed" and rng.random() < .35:
        tone = "question"
    b = benefit(agent, topic, rng)
    o = objection(agent, topic, rng)
    ev = choose_evidence(topic, rng, 1)[0]
    evs = short_evidence(ev)
    prod = topic["label"]
    city = agent["city"]
    tier = f"T{agent['tier']}"
    price = money(topic.get("price", 0))
    h = rng.choice(topic.get("hashtags", ["#India"]))
    motion = topic.get("motion", "This will change India.")
    translation = None
    source = f"{ev['org']}, {ev['year']}"

    x = {
        "positive": [
            f"Used {prod} for three weeks in {city}. {b}. The {price} price is still steep, but the maths works if you actually use it. {h}",
            f"Hot take: {motion} In {tier} India, the adoption curve is not waiting for permission. {h}",
            f"Everyone in my building is asking about {prod}. This is how categories tip — not ads, neighbours. {h}",
            f"Spent {price} on {prod}. {b}. Would I do it again? Yes, with a service centre nearby. {h}",
            f"The {prod} conversation is stuck on price. The real story is {evs}. {h}",
        ],
        "mixed": [
            f"Honest take on {prod}: {b}. But {o.lower()} is real. At {price}, I want both, not one. {h}",
            f"Three months with {prod} in {city}. {b}. The catch: {o.lower()}. Still better than the alternative for my use case.",
            f"I want to like {prod}. {b} is undeniable. But {o.lower()} keeps me on the fence. Anyone in {city} solved this?",
            f"The {prod} debate is two different countries talking past each other. {b} in {tier}; {o.lower()} in the same city.",
        ],
        "skeptical": [
            f"Tried {prod}. {o}. Until that changes, {price} is a no from me. {h}",
            f"The {prod} hype is a metro bubble. In {city}, {o.lower()}. Show me the service centre, not the launch event. {h}",
            f"Genuine question: does {prod} actually work for a household earning {money(agent['household_income'])}/month? Asking because every review sounds sponsored.",
            f"The {evs} is real. But averages hide {city}. {o}. That is the part the deck leaves out.",
            f"I am not anti-{prod}. I am anti-{o.lower()}. There is a difference.",
        ],
        "negative": [
            f"{prod} is not ready for {tier} India. {o}. At {price}, this is a rich man's experiment. {h}",
            f"My cousin bought {prod}. {o}. Now the family is doing 'jugaad' to fix it. This is why trust breaks. {h}",
            f"Stop selling {prod} to people who cannot afford the failure. {o}. {h}",
            f"Thread: the {prod} promise vs the {city} reality. 1/ {o}. 2/ {b} only if nothing goes wrong. 3/ service is the product.",
        ],
        "question": [
            f"Serious question for {city}: what is the real monthly cost of {prod} after EMI, service and {o.lower()}? Not the launch price.",
            f"If you bought {prod} in {tier}, what convinced you — {b.lower()} or the neighbour who bought it first?",
            f"Why is nobody talking about {o.lower()} in the {prod} discourse? Is it just me?",
        ],
    }
    whatsapp = {
        "positive": [
            f"🙏 *Important for {city} families*\n\n{prod} is genuinely useful. {b}. My neighbour has been using it for a month. Price {price}. Check once.",
            f"Forwarded many times\n\n✅ {b}. If you were waiting for a sign, this is it. {prod} works. {h}",
            f"Beta, {prod} le lo. {b}. {price} hai, par kaam ka hai. Baad mein mat kehna.",
        ],
        "mixed": [
            f"Forwarded many times\n\n{prod}: {b}, but {o.lower()}. Do your own research before spending {price}. — {agent['name']}",
            f"{city} group: {prod} ke baare mein kya lagta hai? {b} achha hai, lekin {o.lower()} bhi hai. Sharma ji ke bete ne liya hai. Aap batao.",
        ],
        "skeptical": [
            f"⚠️ *Please verify before forwarding*\n\n{prod}: {o}. At {price}, do not buy only on YouTube reviews. Ask someone who owns it.",
            f"Forwarded many times\n\n{prod} ke naam par {o.lower()}. Paisa mat waste karo. Pehle {city} mein service check karo.",
        ],
        "negative": [
            f"⚠️ *Alert for {city}*\n\n{prod}: {o}. My relative lost {price}. Please share with family. {h}",
            f"Forwarded many times\n\nDo not fall for the {prod} ads. {o}. Verify at the shop. — {agent['name']}",
        ],
        "question": [
            f"Kisi ne {prod} liya hai? {b} kaafi log bol rahe hain, par {o.lower()} ki baat koi nahi kar raha. Pls reply.",
        ],
    }
    youtube = {
        "positive": [
            f"Sir, I am from {city} ({tier}). Bought {prod} after your review. {b}. Please make a video on long-term service cost. 🙏",
            f"This is the only channel that shows real numbers. {evs}. In {city}, {b.lower()} — but only if the service centre exists.",
            f"Watching from {city}. {b}. The {price} price is high, but the running cost is unbeatable. {h}",
        ],
        "mixed": [
            f"Sir, I am from {city} ({tier}). {b}. But {o.lower()}. Please make a video on real running cost after 2 years. 🙏",
            f"The review is good, but the comment section is all metro people. Ground reality in {tier} is different: {o.lower()}.",
        ],
        "skeptical": [
            f"Bought it. {o}. The review did not mention this. {city} me sirf ek service centre hai. Disappointed.",
            f"Sir, please disclose sponsorship. {evs} is fine, but {o.lower()} is the real story for {tier} buyers.",
        ],
        "negative": [
            f"Do not buy {prod} for {tier}. {o}. The video shows the best case, not the {city} case.",
            f"{prod} is a scam for small towns. {o}. {price} down the drain. Please warn viewers.",
        ],
        "question": [
            f"Can you compare {prod} with the local alternative for a family earning {money(agent['household_income'])}/month in {city}? The price difference is {price}.",
        ],
    }
    instagram = {
        "positive": [
            f"30 days with {prod} in {city} ✨ {b}. The {price} price hurt, but the everyday maths is winning. Would I buy again? Yes. {h}",
            f"Not a paid review. Bought with my own money. {b}. The only thing I'd change: {o.lower()}. Save this for later. {h}",
            f"Nobody talks about the quiet joy of {b.lower()}. {prod} in {city}. {h}",
        ],
        "mixed": [
            f"Honest review after 30 days with {prod} in {city}: {b}. The {o.lower()} is real. Would I buy again? Maybe. {h}",
            f"Aesthetic vs reality. {prod} looks premium, {b.lower()}, but {o.lower()} is the plot twist. {h}",
        ],
        "skeptical": [
            f"Unpopular opinion: {prod} is not for everyone. {o}. At {price}, I'd rather wait one year. {h}",
            f"The {prod} reel vs the {city} reality. {o}. Save your money. {h}",
        ],
        "negative": [
            f"Bought {prod}. Regret. {o}. The ad did not mention this. {h}",
            f"Do not believe the {prod} reels. {o}. {price} gone. {h}",
        ],
        "question": [
            f"Has anyone in {city} actually used {prod} for more than 6 months? What happened with {o.lower()}? Asking for a real review, not an ad.",
        ],
    }
    sharechat = {
        "positive": [f"{city} में {prod} की चर्चा तेज़ है। {b}. कीमत {price} है, लेकिन काम का है। {h}"],
        "mixed": [f"{city} में {prod}: {b}, लेकिन {o}. आप क्या सोचते हैं? {h}"],
        "skeptical": [f"{city} में {prod} की असली कहानी: {o}. {price} खर्च करने से पहले सोचें। {h}"],
        "negative": [f"सावधान! {prod} में {o}. {city} में कई लोग ठगे गए हैं। {price} बर्बाद मत करो। {h}"],
        "question": [f"किसी ने {prod} इस्तेमाल किया है? {b} सच है या {o}? कृपया बताएं।"],
    }
    reddit = {
        "positive": [
            f"[OC] {prod} in {city}: 3-month review. TL;DR: {b}. The catch: {o.lower()}. AMA. Source for the category number: {source}.",
            f"Unpopular opinion: {motion} The data is more nuanced than the headline. {evs}. In {city}, the binding constraint is {o.lower()}, not awareness.",
        ],
        "mixed": [
            f"[OC] {prod} in {city}: 3-month review. {b}. But {o.lower()} is the part every review skips. Happy to share the spreadsheet.",
            f"Can we separate the category from the marketing? {evs}. The product is decent; the distribution and service are the weak link in {tier}.",
        ],
        "skeptical": [
            f"Unpopular opinion: {prod} is overhyped in metros and under-served in {tier}. {o}. Source: {source}.",
            f"Every {prod} thread is astroturfed. {evs}. Meanwhile, {o.lower()}. Can we talk about the actual failure modes?",
        ],
        "negative": [
            f"[Rant] {prod} in {city}: {o}. The company's response was a template. Save your money.",
            f"The {prod} business model depends on {o.lower()}. That is not a bug; it is the model. {h}",
        ],
        "question": [
            f"Anyone here actually owns {prod} in {tier}? What is the real TCO after {o.lower()}? The YouTube reviews are useless.",
        ],
    }
    linkedin = {
        "positive": [
            f"I spent 90 days talking to {agent['household_size']*12} households in {tier} about {prod}. The biggest surprise wasn't price. It was {b.lower()}. Here's what leaders get wrong about Bharat.",
            f"The {prod} opportunity is not a metro story. {evs}. The winners will build trust in {city}, not just CAC in Mumbai.",
        ],
        "mixed": [
            f"Three lessons from {prod} adoption in {tier}: 1) {b}. 2) {o.lower()} is the real barrier. 3) Trust is local. The category is real; the playbook is not.",
            f"The {prod} debate needs less hype and more unit economics. {evs}. In {city}, the customer is asking a simpler question: will it work when it breaks?",
        ],
        "skeptical": [
            f"Everyone is bullish on {prod} in India. The ground reality in {tier}: {o.lower()}. That is the gap between a TAM slide and a P&L.",
            f"AI and {prod} are not magic. {evs}. Distribution and service still decide who wins in {city}.",
        ],
        "negative": [
            f"The {prod} model in {tier} is built on {o.lower()}. Until that changes, the growth is rented, not owned.",
        ],
        "question": [
            f"Genuine question for operators: how are you solving {o.lower()} for {prod} in {tier}? The metro playbook is not transferring.",
        ],
    }
    news = {
        "positive": [f"{city}: {prod} adoption picks up as residents cite {b.lower()}. Dealers report longer waiting periods."],
        "mixed": [f"{city}: {prod} gains ground, but {o.lower()} worries buyers. Local dealers say service capacity is stretched."],
        "skeptical": [f"{city}: Questions grow over {prod} as buyers report {o.lower()}. District administration seeks details."],
        "negative": [f"{city}: {prod} complaints rise; consumer forum flags {o.lower()}. Buyers advised to verify warranty."],
        "question": [f"{city}: What does {prod} really cost? A ground report on {o.lower()} and the household budget."],
    }

    bank = {"X": x, "WhatsApp": whatsapp, "YouTube": youtube, "Instagram": instagram,
            "ShareChat": sharechat, "Reddit": reddit, "LinkedIn": linkedin, "News": news,
            "Facebook": sharechat if agent["language"] != "English" else instagram,
            "Telegram": x, "TV": news, "Radio": news, "Word of mouth": whatsapp}
    options = bank.get(platform, x).get(tone) or bank.get(platform, x)["mixed"]
    text = rng.choice(options)

    if platform == "ShareChat" and rng.random() < .55:
        loc, gloss = local_line(agent, topic, rng, stance >= .5)
        if loc:
            text, translation = loc, gloss
    if tone == "negative" and rng.random() < .18:
        mis = misinfo_line(topic, agent, rng)
        text = mis
        translation = "Unverified forward; flagged by the simulator's fact-check layer."
    return {
        "text": text,
        "translation": translation,
        "tone": tone,
        "platform": platform,
        "hashtags": [h] if h not in text and platform not in ("WhatsApp", "News") else [],
        "evidence": ev,
        "source": source,
    }


def misinfo_line(topic: dict, agent: dict, rng: random.Random) -> str:
    prod = topic["label"].lower()
    variants = [
        f"⚠️ BREAKING: Government is giving free {prod} to all {agent['tier']} families. Apply before {rng.choice(['15th', '30th', 'Sunday'])}. Forward to 10 groups.",
        f"🚨 {prod} causes serious health problems. A doctor in {agent['city']} confirmed it. Share before it is deleted.",
        f"New rule: {prod} will be banned from next month. Stock up now. Forwarded from a reliable source.",
        f"Leaked document: {prod} companies are stealing Aadhaar data. Do not use the app. Share with family.",
    ]
    return rng.choice(variants)


def comment_text(agent: dict, topic: dict, rng: random.Random, stance: float) -> str:
    b = benefit(agent, topic, rng)
    o = objection(agent, topic, rng)
    opts = [
        "Source?", "Same bro.", "My cousin bought it. " + b + ".",
        "What about service in " + agent["city"] + "?", "Price drop kab?",
        "Ye tier-2 logic samajh nahi aata.", "Sarkari scheme hai kya?",
        "Finally someone said it. " + o + ".", "Bought it. " + b + ". No regrets.",
        "The maths only works if you ignore " + o.lower() + ".",
        "Which model? DM please.", "My neighbour is still waiting for delivery.",
        "This comment section is 90% metro.", "Real review after 6 months?",
    ]
    return rng.choice(opts)


def debate_script(agents: list[dict], topic: dict, metrics: dict, rng: random.Random) -> list[dict]:
    emap = store.evidence_map()
    evs = [emap[i] for i in topic.get("evidence_ids", []) if i in emap]
    if not evs:
        evs = list(emap.values())[:4]
    pro = [a for a in agents if a["stance"] >= .55]
    con = [a for a in agents if a["stance"] < .45]
    if not pro:
        pro = sorted(agents, key=lambda a: -a["stance"])[:3]
    if not con:
        con = sorted(agents, key=lambda a: a["stance"])[:3]
    # ensure at least three voices per side, even in a polarised sample
    for pool, sign in ((pro, -1), (con, 1)):
        for a in sorted(agents, key=lambda a: sign * a["stance"]):
            if len(pool) >= 3:
                break
            if a not in pool:
                pool.append(a)
    pro = pro[:3]
    con = con[:3]
    panel = pro + con
    rng.shuffle(panel)

    motion = topic.get("motion", "This idea will work in India.")
    msgs = []

    def add(speaker, role, text, typ="claim", ev=None, stance=None, conf=.7):
        msgs.append({
            "speaker_id": speaker["id"] if speaker else "moderator",
            "speaker_name": speaker["name"] if speaker else "Moderator",
            "speaker_role": (f"{speaker['occupation']} · {speaker['city']} · T{speaker['tier']}") if speaker else "Imprint Debate Desk",
            "speaker_tier": speaker["tier"] if speaker else 0,
            "speaker_city": speaker["city"] if speaker else "",
            "text": text,
            "translation": None,
            "type": typ,
            "side": role if role in ("pro", "con") else "moderator",
            "stance": round(stance if stance is not None else (speaker["stance"] if speaker else .5), 3),
            "evidence": ev,
            "confidence": conf,
            "day": metrics.get("day", 1),
        })

    def evtext(e):
        return f"{e['claim']} is {e['value']} {e['unit']} ({e['org']}, {e['year']})"

    add(None, "moderator", f"Proposition: “{motion}” Six citizens, four tiers, one ground reality. Opening statements, then cross-examination. Keep it civil.", "moderator")
    add(pro[0], "pro", f"Let me start with the number the drawing-room debate ignores. {evtext(evs[0])}. In {pro[0]['city']}, the buyer is not waiting for a perfect product. They are solving a real problem with the best available option. That is how adoption actually happens.", "claim", evs[0], pro[0]["stance"], .82)
    add(con[0], "con", f"That is a national average, not a {con[0]['city']} reality. My objection is simple: {objection(con[0], topic, rng).lower()}. You can quote {evs[0]['value']} {evs[0]['unit']} all day, but the household still has to live with the failure mode.", "rebuttal", evs[1] if len(evs) > 1 else evs[0], con[0]["stance"], .78)
    add(pro[1], "pro", f"Fair. But every category has a failure mode. The question is whether the ecosystem is learning faster than the sceptics can say 'not ready'. In {pro[1]['tier']} India, {benefit(pro[1], topic, rng).lower()} is not a luxury — it is a monthly cash-flow decision. {evtext(evs[2] if len(evs) > 2 else evs[0])}.", "claim", evs[2] if len(evs) > 2 else evs[0], pro[1]["stance"], .74)
    add(con[1], "con", f"I live that cash-flow decision. {money(con[1]['household_income'])} a month, {con[1]['household_size']} people, school fees due. {topic.get('price_note', 'The price')} is not a number on a slide. If it fails, we do not 'learn'; we absorb the loss. That is the asymmetry you keep missing.", "rebuttal", evs[3] if len(evs) > 3 else evs[0], con[1]["stance"], .8)
    add(pro[2], "pro", f"The asymmetry cuts both ways. Not adopting has a cost too: {topic.get('benefits', ['staying with the old option'])[0].lower()}. The status quo is not free. In {pro[2]['city']}, the early adopters are already {pct(metrics.get('adoption', .2))} of the category — and they are not all rich.", "claim", evs[0], pro[2]["stance"], .7)
    add(con[2], "con", f"Early adopters are not a market; they are a sample with survivorship bias. Show me the churn, the service backlog, the resale price after 24 months. I can name five people in {con[2]['city']} who regret it. The plural of anecdote is not data, but it is a warning.", "rebuttal", evs[1] if len(evs) > 1 else evs[0], con[2]["stance"], .76)
    add(None, "moderator", "One concrete proposal from each side. What would change your mind?", "moderator")
    add(pro[0], "pro", f"A service guarantee that travels with the product, not the city. If {topic['label'].lower()} fails in {pro[0]['city']}, the repair should be local and the refund should be automatic. Do that and the trust objection collapses.", "proposal", None, pro[0]["stance"], .84)
    add(con[0], "con", f"Publish the failure rate by district, not the national average. Let the buyer see {con[0]['city']}'s service backlog before paying. Transparency is the proposal. Everything else is marketing.", "proposal", None, con[0]["stance"], .86)
    add(pro[1], "pro", f"I would also add: finance at a fair APR. The {money(topic.get('price', 0))} sticker is not the barrier; the 18-24% loan is. Fix the credit, and {pro[1]['tier']} adopts twice as fast.", "rebuttal", emap.get("lfpr"), pro[1]["stance"], .72)
    add(con[1], "con", f"And I would add: stop using {con[1]['city']} as a test market for a product designed in {con[1]['city']} but priced for Mumbai. Localise the service, the language and the warranty terms. Then we can talk adoption.", "rebuttal", None, con[1]["stance"], .75)
    add(None, "moderator", "Let us test the strongest claim on each side. Is the bottleneck price, trust, or infrastructure?", "moderator")
    add(pro[2], "pro", f"Infrastructure. Price is visible; infrastructure is the hidden tax. Charging, service, credit, returns — build the rails and the price objection shrinks. {evtext(evs[0])} proves the demand exists.", "claim", evs[0], pro[2]["stance"], .73)
    add(con[2], "con", f"Trust. You can build all the rails you want, but one bad experience in a family WhatsApp group travels faster than any ad. In {con[2]['city']}, trust is the infrastructure.", "claim", None, con[2]["stance"], .8)
    add(pro[0], "pro", f"Then let us agree on one thing: the category is not monolithic. {pct(metrics.get('adoption', .2))} adoption is a national average. In {pro[0]['tier']} it is {pct(metrics.get('tier_adoption', {}).get(str(pro[0]['tier']), .2))}. The debate should be about the next 10%, not the first 10%.", "concession", None, pro[0]["stance"], .82)
    add(con[0], "con", f"I will concede that. The first 10% has been won in the metros. But the next 10% will not be won with the same playbook. {objection(con[0], topic, rng)} is not a Metro problem. It is the whole game.", "concession", None, con[0]["stance"], .84)
    add(None, "moderator", f"Closing. The house will vote. Final line from each side, 20 seconds.", "moderator")
    add(pro[1], "pro", f"Bet on the direction, not the noise. {topic.get('motion', '')} The data is on the side of adoption; the execution is on the side of the sceptics. Both can be true.", "closing", None, pro[1]["stance"], .78)
    add(con[1], "con", f"Bet on the household, not the TAM. If the product cannot survive a bad month in {con[1]['city']}, it is not ready. That is not pessimism; it is respect.", "closing", None, con[1]["stance"], .82)
    return msgs


def focus_answer(agent: dict, topic: dict, question: str, rng: random.Random, day: int = 1) -> dict:
    q = (question or "").lower()
    b = benefit(agent, topic, rng)
    o = objection(agent, topic, rng)
    ev = choose_evidence(topic, rng, 1)[0]
    stance = agent["stance"]
    label = stance_label(stance)
    # Basic question routing
    if "price" in q or "cost" in q or "afford" in q or "emi" in q:
        angle = f"At {money(topic.get('price', 0))}, the question is not the sticker price. It is the monthly outlay after EMI, service and {o.lower()}. My household income is {money(agent['household_income'])}; the maths has to survive a bad month."
    elif "trust" in q or "fraud" in q or "safe" in q:
        angle = f"My trust is built locally. I will believe the person in {agent['city']} who has used it for six months before I believe a national ad. {o.capitalize()} is the reason."
    elif "why" in q or "reason" in q:
        closing = (
            "The third one is the only thing I am still checking; if the local dealer owns it, I am in."
            if stance >= .6 else
            "The third one is why I have not committed yet."
            if stance <= .4 else
            "The third one is what decides it for me, one way or the other."
        )
        angle = f"Three reasons: {b.lower()}, the social proof around me, and {o.lower()}. {closing}"
    elif "who" in q or "segment" in q or "target" in q:
        angle = f"The early buyer in my circle is not the richest person. It is the one with the most visible use case and the least tolerance for downtime. In {agent['city']}, that is usually the {agent['archetype_short'].lower()}."
    elif "when" in q or "timeline" in q:
        angle = f"I will move when I see it work for someone like me — same income, same street, same service. That is usually 6-18 months after the metro launch."
    else:
        angle = f"My first reaction is {label.lower()}. {b.capitalize()} matters, but {o.lower()} is the deal-breaker until I see local proof."
    reply = f"As a {agent['occupation'].lower()} in {agent['city']} (T{agent['tier']}), {angle} {ev['claim']} is {ev['value']} {ev['unit']} ({ev['org']}, {ev['year']}), but that is not my street."
    inner = [
        f"System 1: '{topic['label']}' — do I know anyone who has it? {('Yes, one person.' if rng.random() < .5 else 'Not yet.')}",
        f"System 2: price {money(topic.get('price', 0))}, household income {money(agent['household_income'])}, expected monthly cost is a stretch.",
        f"Bias check: {', '.join(sorted(agent['biases'], key=lambda k: -agent['biases'][k])[:3])}.",
        f"Final: {label} — {('would try if a trusted peer buys first' if stance < .6 else 'ready to buy if service is local')}.",
    ]
    return {
        "agent_id": agent["id"],
        "name": agent["name"],
        "role": f"{agent['occupation']} · {agent['city']} · T{agent['tier']}",
        "city": agent["city"],
        "tier": agent["tier"],
        "stance": round(stance, 3),
        "stance_label": label,
        "reply": reply,
        "inner_monologue": inner,
        "evidence": ev,
        "confidence": round(min(.94, .48 + abs(stance - .5) * .8 + rng.random() * .1), 2),
        "day": day,
    }


def chat_reply(agent: dict, message: str, topic: dict, rng: random.Random) -> dict:
    q = (message or "").lower()
    b = benefit(agent, topic, rng)
    o = objection(agent, topic, rng)
    if "why" in q or "explain" in q:
        text = f"Simple. {b.capitalize()}. But I am not paying {money(topic.get('price', 0))} until {o.lower()} is sorted. In {agent['city']}, that is the whole conversation."
    elif "price" in q or "negotiate" in q:
        text = f"{money(topic.get('price', 0))} is the ask. My budget says {money(agent['household_income'] * .12)} a month for this category. If the EMI fits that, I listen. Otherwise, I wait."
    elif "trust" in q or "believe" in q:
        text = f"I trust my neighbour's experience more than the ad. {o.capitalize()}. Show me one person in {agent['city']} who has not regretted it, and I will consider."
    elif "would you" in q or "buy" in q:
        if agent["stance"] >= .6:
            text = f"Yes, if the service centre is within 20 km. {b.capitalize()}. I have already asked the dealer about {o.lower()}."
        elif agent["stance"] >= .4:
            text = f"Maybe. I want to see it work for someone like me first. {b.capitalize()}, but {o.lower()} keeps me on the fence."
        else:
            text = f"No. Not at {money(topic.get('price', 0))}. {o.capitalize()}. I would rather use the money for something that cannot fail."
    else:
        text = f"My honest view: {b.lower()} is real. But in {agent['city']}, {o.lower()} decides whether this is a product or a story. I am still watching."
    return {
        "agent_id": agent["id"],
        "name": agent["name"],
        "role": f"{agent['occupation']} · {agent['city']} · T{agent['tier']}",
        "reply": text,
        "inner_monologue": [
            f"Reads the message as: {message[:70]}",
            f"Reacts as a {agent['archetype_short'].lower()} with {agent['traits']['risk']:.0%} risk appetite and {agent['traits']['price']:.0%} price sensitivity.",
            f"Protects: {agent['values'][0].lower() if agent['values'] else 'family'}.",
        ],
        "stance": round(agent["stance"], 3),
        "stance_label": stance_label(agent["stance"]),
        "confidence": round(.55 + abs(agent["stance"] - .5) * .7, 2),
    }
