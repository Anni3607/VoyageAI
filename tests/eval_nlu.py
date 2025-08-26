
"""
Run: python tests/eval_nlu.py
This script will call the local backend /nlu/parse and /plan endpoints to:
 - measure intent detection correctness (simple label match)
 - measure entity extraction correctness for key fields (destination,budget,n_days)
 - record fallback rate (planner asking for more info)
 - measure avg latency for endpoints
Requires backend running at BACKEND_URL env or default http://127.0.0.1:8000
"""
import os, time, requests, json
BACKEND = os.getenv("BACKEND_URL","http://127.0.0.1:8000")

# Synthetic test cases
TESTS = [
    {"text":"Plan a 3-day trip to Goa from Mumbai under ₹20000 in October with beaches and nightlife.", "intent":"plan_trip", "destination":"Goa", "n_days":3, "budget_currency":"INR"},
    {"text":"Suggest visa-free countries for Indians in June under 800 USD.", "intent":"plan_trip", "destination":None, "n_days":None, "budget_currency":"USD", "visa_free":True},
    {"text":"I want a weekend trip to Jaipur for heritage and shopping from Delhi.", "intent":"plan_trip", "destination":"Jaipur", "n_days":2},
    {"text":"Cheap 5 day manali trip from Mumbai in Jan under 30000", "intent":"plan_trip", "destination":"Manali", "n_days":5},
]

results = []
for t in TESTS:
    start = time.time()
    r = requests.get(f"{BACKEND}/nlu/parse", params={"text": t["text"]}, timeout=10)
    latency = (time.time() - start)*1000
    j = r.json()
    ents = j.get("entities",{})
    intent_ok = (j.get("intent")==t["intent"])
    dest_ok = (t.get("destination") is None) or (ents.get("destination") and t["destination"].lower() in ents.get("destination","").lower())
    n_days_ok = (t.get("n_days") is None) or (ents.get("n_days")==t["n_days"])
    budget_ok = True
    if t.get("budget_currency"):
        b = ents.get("budget")
        budget_ok = (b is not None and b.get("currency") and t["budget_currency"].upper() in b.get("currency","").upper())
    # call /plan to see if it needs info
    start2 = time.time()
    rp = requests.post(f"{BACKEND}/plan", json={"text": t["text"]}, timeout=20)
    latency2 = (time.time() - start2)*1000
    plan_resp = rp.json().get("plan",{})
    fallback = (plan_resp.get("status") == "need_info")
    results.append({
        "text": t["text"],
        "intent_ok": intent_ok,
        "dest_ok": dest_ok,
        "n_days_ok": n_days_ok,
        "budget_ok": budget_ok,
        "nlu_latency_ms": int(latency),
        "plan_latency_ms": int(latency2),
        "fallback": fallback
    })

# Summary
total = len(results)
intent_acc = sum(1 for r in results if r["intent_ok"]) / total
entity_acc = sum(1 for r in results if r["dest_ok"] and r["n_days_ok"]) / total
fallback_rate = sum(1 for r in results if r["fallback"]) / total
avg_nlu_lat = sum(r["nlu_latency_ms"] for r in results)/total
avg_plan_lat = sum(r["plan_latency_ms"] for r in results)/total

out = {"per_test": results, "summary":{"intent_acc": intent_acc, "entity_acc": entity_acc, "fallback_rate": fallback_rate, "avg_nlu_latency_ms": avg_nlu_lat, "avg_plan_latency_ms": avg_plan_lat}}
print(json.dumps(out, indent=2))
# Save to file
os.makedirs("voyagerai/results", exist_ok=True)
with open("voyagerai/results/eval_nlu.json","w",encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
