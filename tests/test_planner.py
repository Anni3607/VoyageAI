from voyagerai.backend.nlu import parse
from voyagerai.backend.planner import plan_itinerary

def test_plan_goa():
    q = "Plan a 3-day trip to Goa from Mumbai under ₹20000 in October with beaches and nightlife."
    nlu = parse(q)
    plan = plan_itinerary(nlu)
    assert plan["status"] == "ok"
    assert plan["summary"]["destination"] in ["Goa","goa"]
    assert plan["summary"]["n_days"] == 3
    assert len(plan["days"]) == 3
