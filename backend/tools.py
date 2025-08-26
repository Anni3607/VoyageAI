
import os, json, time, hashlib
from typing import Optional, Dict, Any, Tuple
import requests

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_path(key: str) -> str:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")

def cached_fetch(key: str, ttl: int, fetch_fn):
    '''
    Simple cache wrapper. `key` should be stable string for request.
    ttl in seconds.
    fetch_fn: function that returns serializable object.
    '''
    p = _cache_path(key)
    now = int(time.time())
    if os.path.exists(p):
        try:
            with open(p,"r",encoding="utf-8") as f:
                obj = json.load(f)
            if now - obj.get("_ts",0) < ttl:
                return obj.get("data")
        except Exception:
            pass
    data = fetch_fn()
    try:
        with open(p,"w",encoding="utf-8") as f:
            json.dump({"_ts": now, "data": data}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return data

# ---------- Tools clients ----------
TOOL_MODE = os.getenv("TOOL_MODE","mock").lower()
OPENTRIPMAP_KEY = os.getenv("OPENTRIPMAP_KEY","")
OPENROUTESERVICE_KEY = os.getenv("OPENROUTESERVICE_KEY","")

# ---------- POIs (OpenTripMap) ----------
def get_city_geocode(city: str) -> Optional[Tuple[float,float]]:
    '''Lightweight geocode using OpenTripMap geoname or REST Countries fallback for country.
       Returns (lat, lon) or None
    '''
    if TOOL_MODE == "mock":
        map_mock = {"Goa": (15.4909,73.8278), "Jaipur": (26.9124,75.7873), "Manali": (32.2396,77.1887), "Singapore": (1.3521,103.8198)}
        return map_mock.get(city.title())
    # Live: use OpenTripMap geoname
    try:
        q = {"name": city, "apikey": OPENTRIPMAP_KEY}
        r = requests.get("https://api.opentripmap.com/0.1/en/places/geoname", params=q, timeout=15)
        r.raise_for_status()
        j = r.json()
        return (j.get("lat"), j.get("lon"))
    except Exception:
        return None

def get_pois(city: str, radius_m: int=10000, limit: int=30):
    key = f"pois:{city}:{radius_m}:{limit}:{TOOL_MODE}"
    def fetch():
        if TOOL_MODE == "mock":
            # read mock from data/mock_pois.json (same structure as used earlier)
            try:
                here = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mock_pois.json")
                with open(here,"r",encoding="utf-8") as f:
                    data = json.load(f)
                return data.get(city.title(), [])
            except Exception:
                return []
        # Live: call OpenTripMap radius search (two-step: bbox -> places list -> details)
        coords = get_city_geocode(city)
        if not coords:
            return []
        lat, lon = coords
        try:
            params = {"apikey": OPENTRIPMAP_KEY, "radius": radius_m, "limit": limit, "offset":0, "lon":lon, "lat":lat}
            r = requests.get("https://api.opentripmap.com/0.1/en/places/radius", params=params, timeout=15)
            r.raise_for_status()
            j = r.json()
            features = []
            for item in j.get("features", []):
                props = item.get("properties",{})
                xid = props.get("xid")
                # get details
                if xid:
                    try:
                        dr = requests.get(f"https://api.opentripmap.com/0.1/en/places/xid/{xid}", params={"apikey":OPENTRIPMAP_KEY}, timeout=10)
                        dr.raise_for_status()
                        d = dr.json()
                    except Exception:
                        d = props
                else:
                    d = props
                features.append({
                    "name": d.get("name") or props.get("name") or "unknown",
                    "tags": list(d.get("kinds","").split(","))[:4],
                    "popularity": int(d.get("rate", 50)),
                    "notes": d.get("wikipedia_extracts", {}).get("text","")
                })
            return features
        except Exception:
            return []
    # ttl: 24 hours
    return cached_fetch(key, ttl=86400, fetch_fn=fetch)

# ---------- Weather (Open-Meteo) ----------
def get_weather(lat: float, lon: float, start_date: str, end_date: str) -> Dict[str,Any]:
    key = f"weather:{lat}:{lon}:{start_date}:{end_date}:{TOOL_MODE}"
    def fetch():
        if TOOL_MODE == "mock":
            # simple synthetic daily forecast
            from datetime import datetime, timedelta
            sd = datetime.fromisoformat(start_date)
            ed = datetime.fromisoformat(end_date)
            res = []
            cur = sd
            while cur <= ed:
                res.append({"date": cur.date().isoformat(), "temp_max": 30, "temp_min": 24, "weathercode": 0})
                cur += timedelta(days=1)
            return {"daily": res}
        # Live call
        try:
            params = {
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,weathercode",
                "start_date": start_date, "end_date": end_date, "timezone":"UTC"
            }
            r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
            r.raise_for_status()
            j = r.json()
            # transform
            days = []
            dates = j.get("daily", {}).get("time", [])
            tmax = j.get("daily", {}).get("temperature_2m_max", [])
            tmin = j.get("daily", {}).get("temperature_2m_min", [])
            wc = j.get("daily", {}).get("weathercode", [])
            for i, d in enumerate(dates):
                days.append({"date": d, "temp_max": tmax[i], "temp_min": tmin[i], "weathercode": wc[i]})
            return {"daily": days}
        except Exception:
            return {"daily": []}
    return cached_fetch(key, ttl=3600*6, fetch_fn=fetch)  # 6 hours

# ---------- Routing & Distance (OpenRouteService or OSRM) ----------
def get_route(lat1, lon1, lat2, lon2):
    key = f"route:{lat1}:{lon1}:{lat2}:{lon2}:{TOOL_MODE}"
    def fetch():
        if TOOL_MODE == "mock":
            # simple straight-line distance and 1h travel
            from math import radians, sin, cos, sqrt, atan2
            R = 6371.0
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            km = R * c
            return {"distance_km": round(km,1), "duration_min": int(km/40*60)+30}
        # Live with OpenRouteService if key present
        if OPENROUTESERVICE_KEY:
            try:
                headers = {"Authorization": OPENROUTESERVICE_KEY, "Accept":"application/json", "Content-Type":"application/json"}
                body = {"coordinates":[[lon1,lat1],[lon2,lat2]]}
                r = requests.post("https://api.openrouteservice.org/v2/directions/driving-car/geojson", json=body, headers=headers, timeout=15)
                r.raise_for_status()
                j = r.json()
                props = j["features"][0]["properties"]["summary"]
                return {"distance_km": round(props["distance"]/1000,1), "duration_min": int(props["duration"]/60)}
            except Exception:
                pass
        # fallback to OSRM public
        try:
            r = requests.get(f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false", timeout=15)
            r.raise_for_status()
            j = r.json()
            route = j.get("routes",[{}])[0]
            return {"distance_km": round(route.get("distance",0)/1000,1), "duration_min": int(route.get("duration",0)/60)}
        except Exception:
            return {"distance_km": 0, "duration_min": 0}
    return cached_fetch(key, ttl=86400, fetch_fn=fetch)

# ---------- Currency conversion (Frankfurter) ----------
def convert_currency(amount: float, frm: str, to: str):
    key = f"fx:{frm}:{to}:{TOOL_MODE}"
    def fetch():
        if TOOL_MODE == "mock":
            # naive static rates
            rates = {"USD_INR":83.0, "EUR_INR":90.0, "INR_USD":1/83.0}
            k = f"{frm.upper()}_{to.upper()}"
            r = rates.get(k, 1.0)
            return {"rate": r, "converted": round(amount * r, 2)}
        # Live: frankfurter
        try:
            r = requests.get(f"https://api.frankfurter.app/latest", params={"from":frm.upper(),"to":to.upper()}, timeout=10)
            r.raise_for_status()
            j = r.json()
            rate = list(j.get("rates", {}).values())[0]
            return {"rate": rate, "converted": round(amount * rate, 2)}
        except Exception:
            return {"rate":1.0, "converted": amount}
    return cached_fetch(key, ttl=3600*12, fetch_fn=fetch)

# ---------- Country info (REST Countries) ----------
def get_country_info(name: str):
    key = f"country:{name}:{TOOL_MODE}"
    def fetch():
        if TOOL_MODE == "mock":
            mock = {"India":{"cca2":"IN","name":"India","region":"Asia"}, "Singapore":{"cca2":"SG","name":"Singapore","region":"Asia"}}
            return mock.get(name.title(), {"name":name})
        try:
            r = requests.get(f"https://restcountries.com/v3.1/name/{name}", timeout=15)
            r.raise_for_status()
            j = r.json()
            return j[0]
        except Exception:
            return {"name": name}
    return cached_fetch(key, ttl=86400*30, fetch_fn=fetch)

# ---------- Holidays (Nager.Date) ----------
def get_public_holidays(country_code: str, year: int):
    key = f"holidays:{country_code}:{year}:{TOOL_MODE}"
    def fetch():
        if TOOL_MODE == "mock":
            return []
        try:
            r = requests.get(f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}", timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception:
            return []
    return cached_fetch(key, ttl=86400*30, fetch_fn=fetch)
