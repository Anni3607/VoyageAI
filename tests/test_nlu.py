from voyagerai.backend.nlu import parse

def test_basic_goa_trip():
    q = "Plan a 3-day trip to Goa from Mumbai under ₹20000 in October with beaches and nightlife."
    out = parse(q)
    assert out["intent"] == "plan_trip"
    ents = out["entities"]
    assert ents.get("destination") in ["Goa","goa"]
    assert ents.get("origin") in ["Mumbai","mumbai"]
    assert "budget" in ents and ents["budget"]["currency"] == "INR"
    assert any(i in ents.get("interests",[]) for i in ["beach","nightlife"])
    assert "n_days" in ents

def test_visa_free_intent():
    q = "Suggest visa-free countries for Indians in June under 800 USD."
    out = parse(q)
    assert out["entities"].get("visa_free_hint") == True
    assert out["entities"]["budget"]["currency"] in ["USD"]
