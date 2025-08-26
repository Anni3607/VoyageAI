import re, math
from typing import Dict, Any, List, Optional
from datetime import datetime
import dateutil.parser as dateparser

CURRENCY_ALIASES = {
    "₹": "INR", "rs": "INR", "inr": "INR",
    "$": "USD", "usd": "USD",
    "eur": "EUR", "€": "EUR",
}

INTERESTS = [
    "beach","museums","food","nightlife","hiking","history","nature",
    "shopping","adventure","romantic","family","wildlife","architecture",
    "waterfalls","temples","cafes","photography"
]

DEST_HINT_WORDS = ["to","for","in","at","around","near","visiting","visit","trip to"]

INTENTS = {
    "plan_trip": [
        r"plan.*trip", r"itinerary", r"travel plan", r"3[- ]?day", r"week(end)?"
    ],
    "ask_visa_free": [
        r"visa[- ]?free", r"no visa needed", r"without visa"
    ],
    "budget_focus": [
        r"under\s*\d+", r"budget", r"cost", r"cheapest", r"low cost"
    ]
}

def _detect_intent(text: str) -> str:
    t = text.lower()
    for intent, pats in INTENTS.items():
        for p in pats:
            if re.search(p, t):
                return intent
    # default
    return "plan_trip"

def _extract_currency_amount(text: str):
    t = text.lower().replace(",","")
    # patterns like ₹20000, rs 30k, 1.2 lakh, $500, 800 usd
    # handle lakh/crore rough conversions
    m = re.search(r"(₹|rs\.?|inr|\$|usd|eur|€)?\s*(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lac|crore|m)?", t)
    if not m:
        return None
    cur_raw, num, scale = m.groups()
    cur = None
    if cur_raw:
        cur = CURRENCY_ALIASES.get(cur_raw.strip(), None)
        if not cur:
            cur = cur_raw.strip().upper().replace(".","")
    amt = float(num)
    if scale:
        s = scale.lower()
        if s in ["k","thousand"]:
            amt *= 1_000
        elif s in ["lakh","lac"]:
            amt *= 100_000
        elif s in ["crore"]:
            amt *= 10_000_000
        elif s in ["m"]:
            amt *= 1_000_000
    return {"amount": round(amt, 2), "currency": cur or "INR"}


def _extract_dates(text: str):
    # Default month references to the CURRENT YEAR (as per project decision)
    from datetime import datetime
    import re
    import dateutil.parser as dateparser
    cur_year = datetime.now().year
    t = text

    # normalize 'to' -> hyphen for ranges like "12 to 15 Oct"
    t = re.sub(r"(\d{1,2})\s*(to|-)\s*(\d{1,2})", r"\1-\3", t, flags=re.I)

    start = end = None
    try:
        months = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)"
        rng = re.search(rf"(\d{{1,2}})[\s-]*(\d{{1,2}})?\s*({months})", t, flags=re.I)
        if rng:
            d1 = f"{rng.group(1)} {rng.group(3)} {cur_year}"
            start = dateparser.parse(d1, fuzzy=True, dayfirst=True)
            if rng.group(2):
                d2 = f"{rng.group(2)} {rng.group(3)} {cur_year}"
                end = dateparser.parse(d2, fuzzy=True, dayfirst=True)
        else:
            single = re.search(rf"(\d{{1,2}}\s*{months})", t, flags=re.I)
            if single:
                d1 = f"{single.group(0)} {cur_year}"
                start = dateparser.parse(d1, fuzzy=True, dayfirst=True)
    except Exception:
        pass

    # duration: '3 days', 'a week', '5-day'
    dur = None
    md = re.search(r"(\d+)\s*(day|days|night|nights)", t, flags=re.I)
    if md:
        dur = int(md.group(1))
    else:
        if re.search(r"week(end)?", t, flags=re.I):
            dur = 2

    out = {}
    if start: out["start_date"] = start.date().isoformat()
    if end: out["end_date"] = end.date().isoformat()
    if dur: out["n_days"] = dur
    return out if out else None


def _extract_places(text: str):
    # lightweight heuristic: look for 'to|in <Word(/Word)>' capturing capitalized tokens
    # also allow common Indian destinations
    common = ["goa","manali","lonavala","jaipur","kerala","ladakh","mumbai",
              "delhi","bangkok","bali","sri lanka","maldives","singapore",
              "dubai","paris","london","tokyo","new york","paris"]
    t = text
    # capture after prepositions
    m = re.search(r"\b(to|in|for|at)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", t)
    dest = None
    if m:
        dest = m.group(2)
    # lower-case scan for common
    for c in common:
        if c in t.lower():
            dest = c.title()
    # origin mention: 'from Mumbai'
    o = re.search(r"\bfrom\s+([A-Z][a-zA-Z]+)", t)
    origin = o.group(1) if o else None
    return {"destination": dest, "origin": origin}

def _extract_interests(text: str):
    t = text.lower()
    found = [i for i in INTERESTS if i in t]
    # synonyms
    if "party" in t or "club" in t: found.append("nightlife")
    if "heritage" in t or "fort" in t: found.append("history")
    if "trek" in t: found.append("hiking")
    # unique
    return sorted(list(set(found))) if found else None

def parse(text: str) -> Dict[str, Any]:
    intent = _detect_intent(text)
    places = _extract_places(text)
    budget = _extract_currency_amount(text)
    dates = _extract_dates(text)
    interests = _extract_interests(text)
    visa_free = bool(re.search(r"visa[- ]?free|without visa|no visa", text, flags=re.I))

    entities = {}
    entities.update(places or {})
    if budget: entities["budget"] = budget
    if dates: entities.update(dates)
    if interests: entities["interests"] = interests
    if visa_free: entities["visa_free_hint"] = True

    return {"intent": intent, "entities": entities}
