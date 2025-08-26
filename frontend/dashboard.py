
import streamlit as st, os, requests, json
st.set_page_config(page_title="VoyagerAI — Telemetry", layout="centered")
st.title("VoyagerAI — Telemetry & Evaluation Dashboard")

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL","http://127.0.0.1:8000"))

st.header("Live telemetry (last 200 events)")
try:
    r = requests.get(f"{BACKEND_URL}/telemetry/metrics", params={"limit":200}, timeout=6)
    if r.status_code==200:
        metrics = r.json().get("metrics",[])
        st.metric("Events (fetched)", len(metrics))
        # compute avg latency
        lat = [m["latency_ms"] for m in metrics if m.get("latency_ms") is not None]
        if lat:
            st.metric("Avg latency (ms)", int(sum(lat)/len(lat)))
        st.dataframe(metrics[:200])
    else:
        st.warning("Telemetry endpoint error")
except Exception as e:
    st.error("Could not fetch telemetry: " + str(e))

st.header("Latest evaluation results")
eval_file = os.path.join("voyagerai","results","eval_nlu.json")
if os.path.exists(eval_file):
    with open(eval_file,"r",encoding="utf-8") as f:
        ev = json.load(f)
    st.json(ev["summary"])
    st.table(ev["per_test"])
else:
    st.info("No evaluation results found. Run `python voyagerai/tests/eval_nlu.py` to generate results.")
