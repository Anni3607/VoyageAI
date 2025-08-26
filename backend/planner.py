from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import math, os, json

# ---- Mock provider layer (to be swapped in Sprint 4 with real APIs) ----

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mock_pois.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    MOCK = json.load(f)

CITY_TRAVEL_TIME_MIN = {  # rough in-city transit between POIs (minutes)
    "default": 25,
    "Goa": 35,
    "Jaipur": 20,
    "Manali": 30,
    "Singapore": 15
}

CITY_BASE_COST = {  # rough avg per-day costs (stay + local transit) by city (INR)
    "default": 2500,
    "Goa": 3000,
    "Jaipur": 2200,
    "Manali": 2600,
    "Singapore": 9000
}

FLIGHT_ESTIMATE_INR = {
    ("Mumbai","Goa"): 5000,
    ("Mumbai","Jaipur"): 4500,
    ("Mumbai","Manali"): 0,   # assume bus/train to Kullu-Manali: ~3500
    ("Mumbai","Singapore"): 22000
}

STAY_PER_NIGHT_INR = {
    "budget": 1500,
    "mid": 3500,
    "premium": 7500
}

def pick_stay_tier(total_budget_inr: float, n_nights: int) -> str:
    # simple heuristic: 40% stay, 60% activities/food/transport
    per_night = (total_budget_inr * 0.4) / max(n_nights, 1)
    if per_night < 2000:
        return "budget"
    if per_night < 5000:
        return "mid"
    return "premium"

def inr_amount(budget: Optional[Dict[str,Any]]) -> Optional[float]:
    if not budget:
        return None
    cur = (budget.get("currency") or "INR").upper()
    amt = float(budget.get("amount", 0))
    # naive FX (will replace in Sprint 4 currency API)
    fx = {"INR":1.0, "USD":83.0, "EUR":90.0}
    return amt * fx.get(cur, 1.0)

def _city_key(dest: Optional[str]) -> str:
    if not dest:
        return "default"
    d = dest.title()
    return d if d in CITY_BASE_COST else "default"

def _travel_estimate_inr(origin: Optional[str], dest: Optional[str]) -> int:
    if not origin or not dest:
        return 0
    key = (origin, dest)
    rev = (dest, origin)
    if key in FLIGHT_ESTIMATE_INR:
        return FLIGHT_ESTIMATE_INR[key]
    if rev in FLIGHT_ESTIMATE_INR:
        return FLIGHT_ESTIMATE_INR[rev]
    # fallback rough
    return 8000

def _poi_filter(city: str, interests: Optional[List[str]]) -> List[Dict[str,Any]]:
    pois = [p for p in MOCK.get(city.title(), [])]
    if interests:
        lowered = set([i.lower() for i in interests])
        def score(p):
            tags = set([t.lower() for t in p.get("tags",[])])
            return len(tags & lowered)
        pois.sort(key=lambda p: (score(p), p.get("popularity", 0)), reverse=True)
    else:
        pois.sort(key=lambda p: p.get("popularity", 0), reverse=True)
    return pois

def _pack_days(pois: List[Dict[str,Any]], n_days: int, city: str) -> List[List[Dict[str,Any]]]:
    # Greedy packing: 4 main POIs per day, consider open_hours and travel gaps
    per_day = 4
    days = [[] for _ in range(max(n_days,1))]
    i = 0
    for p in pois:
        d = i % len(days)
        if len(days[d]) < per_day:
            days[d].append(p)
            i += 1
        if all(len(day) >= per_day for day in days):
            break
    return days

def _day_schedule(day_pois: List[Dict[str,Any]], city: str, start_time="09:00") -> List[Dict[str,Any]]:
    # Build a timed schedule assuming CITY_TRAVEL_TIME_MIN between POIs and ~90 min per POI
    travel_min = CITY_TRAVEL_TIME_MIN.get(city.title(), CITY_TRAVEL_TIME_MIN["default"])
    blocks = []
    t = datetime.strptime(start_time, "%H:%M")
    for idx, p in enumerate(day_pois):
        # visit block
        end_visit = t + timedelta(minutes=90)
        blocks.append({
            "time": f"{t.strftime('%H:%M')} - {end_visit.strftime('%H:%M')}",
            "name": p["name"],
            "category": ", ".join(p.get("tags",[])),
            "notes": p.get("notes","")
        })
        # travel block (skip after last)
        if idx < len(day_pois)-1:
            tt = end_visit + timedelta(minutes=travel_min)
            blocks.append({
                "time": f"{end_visit.strftime('%H:%M')} - {tt.strftime('%H:%M')}",
                "name": "Transit",
                "category": "travel",
                "notes": f"In-city travel approx {travel_min} min"
            })
            t = tt
        else:
            t = end_visit
    return blocks

def plan_itinerary(nlu: Dict[str,Any]) -> Dict[str,Any]:
    ents = nlu.get("entities", {})
    dest = ents.get("destination")
    origin = ents.get("origin")
    budget = ents.get("budget")
    interests = ents.get("interests", [])
    start_date = ents.get("start_date")
    end_date = ents.get("end_date")
    n_days = ents.get("n_days")

    # Minimal required info
    missing = []
    if not dest: missing.append("destination")
    if not (n_days or (start_date and end_date)):
        missing.append("dates or duration")
    if missing:
        return {
            "status": "need_info",
            "ask": f"Please provide {', '.join(missing)} to plan your trip.",
            "entities_seen": ents
        }

    # derive duration if needed
    if not n_days and start_date and end_date:
        sd = datetime.fromisoformat(start_date)
        ed = datetime.fromisoformat(end_date)
        n_days = max((ed - sd).days + 1, 1)
    elif n_days and start_date and not end_date:
        sd = datetime.fromisoformat(start_date)
        ed = sd + timedelta(days=n_days-1)
        end_date = ed.date().isoformat()
    elif n_days and not start_date:
        # default start: next Saturday? keep simple: today
        sd = datetime.now().date()
        start_date = sd.isoformat()
        ed = datetime.now() + timedelta(days=n_days-1)
        end_date = ed.date().isoformat()

    # Budget + cost tiers
    budget_inr = inr_amount(budget) if budget else None
    stay_tier = pick_stay_tier(budget_inr or 40000, max(n_days-1, 1))
    stay_cost = STAY_PER_NIGHT_INR[stay_tier] * max(n_days-1, 1)
    travel_cost = _travel_estimate_inr(origin, dest)
    city_key = _city_key(dest)
    daily_misc = CITY_BASE_COST.get(city_key, CITY_BASE_COST["default"]) * n_days

    est_total = travel_cost + stay_cost + daily_misc
    if budget_inr:
        budget_note = f"Estimated total ~₹{int(est_total)} vs your budget ₹{int(budget_inr)}."
    else:
        budget_note = f"Estimated total ~₹{int(est_total)} (no budget provided)."

    # POI selection & packing
    pois = _poi_filter(dest, interests)
    day_bins = _pack_days(pois, n_days, dest)

    # Build per-day schedules
    schedules = []
    cur = datetime.fromisoformat(start_date) if start_date else datetime.now()
    for day_idx, dp in enumerate(day_bins):
        date_label = (cur + timedelta(days=day_idx)).date().isoformat()
        schedule = _day_schedule(dp, dest)
        schedules.append({
            "date": date_label,
            "items": schedule
        })

    return {
        "status": "ok",
        "summary": {
            "destination": dest,
            "origin": origin,
            "start_date": start_date,
            "end_date": end_date,
            "n_days": n_days,
            "stay_tier": stay_tier,
            "est_cost_inr": int(est_total),
            "travel_cost_inr": int(travel_cost),
            "stay_cost_inr": int(stay_cost),
            "misc_cost_inr": int(daily_misc),
            "notes": budget_note
        },
        "days": schedules,
        "assumptions": [
            "In-city travel ~25–35 min between POIs",
            "90 minutes per POI",
            "Costs are rough heuristics (Sprint 4 adds live APIs)"
        ]
    }
