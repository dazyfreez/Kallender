# transit_service.py
from datetime import datetime, timedelta
import requests

HEADERS = {"User-Agent": "SmartCalendarDashboard/1.0 (christian.gragert.dev@gmail.com)"}

# Wir nutzen 2 HAFAS-Server: Die DB (Standard) und BVG (als Ausweich-Server)
# Beide greifen auf exakt dieselben bundesweiten HAFAS-Fahrpläne zu!
API_SERVERS = [
    "https://v6.db.transport.rest",
    "https://v6.bvg.transport.rest"
]
MVG_BASE_URL = "https://www.mvg.de/api/bgw-pt/v3"

_LOC_CACHE = {}
_ROUTE_CACHE = {"key": None, "timestamp": None, "data": None}


def get_hafas_location(query_str: str, base_url: str) -> str | None:
    clean_query = query_str.replace(",", " ").strip()
    cache_key = f"{base_url}_{clean_query}"
    if cache_key in _LOC_CACHE:
        return _LOC_CACHE[cache_key]
        
    try:
        res = requests.get(
            f"{base_url}/locations",
            params={"query": clean_query, "results": 1},
            headers=HEADERS,
            timeout=5
        )
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                loc_id = data[0].get("id")
                _LOC_CACHE[cache_key] = loc_id
                return loc_id
    except Exception as e:
        print(f"   -> Location-Timeout bei {base_url} für '{clean_query}'")
    return None


def get_mvg_fallback(origin_name: str, dest_name: str) -> dict | None:
    """Der allerletzte Notnagel: Die nächste Abfahrt an deiner Haustür via MVG."""
    print(f"-> Alle Server down. Nutze Notfall-Abfahrtstafel (MVG) für '{origin_name}'...")
    try:
        clean_origin = origin_name.replace(",", " ").strip()
        loc_res = requests.get(f"{MVG_BASE_URL}/locations", params={"query": clean_origin}, headers=HEADERS, timeout=5)
        if loc_res.status_code != 200: return None
        
        loc_data = loc_res.json()
        if not loc_data: return None
        origin_id = loc_data[0].get("globalId")

        dep_res = requests.get(f"{MVG_BASE_URL}/departures", params={"globalId": origin_id, "limit": 10}, headers=HEADERS, timeout=5)
        if dep_res.status_code != 200: return None
        
        departures = dep_res.json()
        if not departures: return None

        best_dep = departures[0]
        dest_lower = dest_name.lower()
        for dep in departures:
            dest_str = dep.get("destination", "").lower()
            if any(p in dest_str for p in dest_lower.split() if len(p) > 2):
                best_dep = dep
                break

        # Robuste Zeit-Auslese, die Fehler abfängt
        planned_ms = best_dep.get("plannedDepartureTime") or best_dep.get("realtimeDepartureTime")
        if not planned_ms:
            return None
            
        planned = datetime.fromtimestamp(planned_ms / 1000)
        actual_ms = best_dep.get("realtimeDepartureTime") or planned_ms
        actual = datetime.fromtimestamp(actual_ms / 1000)
        
        delay_min = max(0, int((actual - planned).total_seconds() / 60))
        dep_clock = planned.strftime("%H:%M")
        
        return {
            "departure": dep_clock,
            "legs": [{
                "name": best_dep.get("label", "ÖPNV"),
                "direction": best_dep.get("destination", dest_name),
                "departure": dep_clock,
                "delay": delay_min
            }],
            "total_duration": 25 # Fallback-Wert
        }
    except Exception as e:
        print(f"-> MVG Notfall-Fallback ist ebenfalls abgestürzt: {e}")
        return None


def query_route(origin_name: str, dest_name: str, target_arrival: datetime) -> dict | None:
    global _ROUTE_CACHE
    
    cache_key = f"{origin_name}-{dest_name}-{target_arrival.strftime('%H:%M')}"
    now = datetime.now()
    
    if _ROUTE_CACHE["key"] == cache_key and _ROUTE_CACHE["timestamp"]:
        if now - _ROUTE_CACHE["timestamp"] < timedelta(minutes=4):
            return _ROUTE_CACHE["data"]

    print(f"\n-> Suche Route: '{origin_name}' -> '{dest_name}' (Ankunft vor {target_arrival.strftime('%H:%M')})")
    target_cmp = target_arrival.replace(tzinfo=None) if target_arrival.tzinfo else target_arrival
    
    # Versuche der Reihe nach alle Server (DB -> dann BVG)
    for base_url in API_SERVERS:
        print(f"   -> Probiere Server: {base_url} ...")
        origin_id = get_hafas_location(origin_name, base_url)
        dest_id = get_hafas_location(dest_name, base_url)

        if not origin_id or not dest_id:
            print("   -> Ort nicht gefunden oder Timeout. Probiere nächsten Server...")
            continue

        params = {
            "from": origin_id,
            "to": dest_id,
            "results": 3,
            "stopovers": "false",
            "arrival": target_cmp.strftime("%Y-%m-%dT%H:%M:%S")
        }

        try:
            res = requests.get(f"{base_url}/journeys", params=params, headers=HEADERS, timeout=8)
            if res.status_code != 200:
                print(f"   -> Server gab Fehlercode {res.status_code} zurück.")
                continue
                
            data = res.json()
            journeys = data.get("journeys", [])
            if not journeys:
                print("   -> Keine Verbindungen auf diesem Server gefunden.")
                continue

            valid_journeys = []
            for j in journeys:
                last_arr = j["legs"][-1].get("plannedArrival") or j["legs"][-1].get("arrival")
                if last_arr:
                    arr_dt = datetime.fromisoformat(last_arr[:19])
                    if arr_dt <= target_cmp:
                        valid_journeys.append(j)

            best = valid_journeys[-1] if valid_journeys else journeys[0]
            
            legs_data = []
            first_transit_departure = None
            
            for leg in best.get("legs", []):
                is_walk = leg.get("walking", False)
                line_info = leg.get("line") or {}
                dest_info = leg.get("destination") or {}

                line_name = "Fußweg" if is_walk else line_info.get("name", "ÖPNV")
                direction = leg.get("direction") or dest_info.get("name", "")
                
                dep_raw = leg.get("plannedDeparture") or leg.get("departure")
                if not dep_raw: continue
                
                dep_clock = datetime.fromisoformat(dep_raw[:19]).strftime("%H:%M")
                delay_sec = leg.get("departureDelay")
                
                legs_data.append({
                    "name": line_name,
                    "direction": direction,
                    "departure": dep_clock,
                    "delay": int(delay_sec / 60) if delay_sec else 0
                })
                if not is_walk and not first_transit_departure:
                    first_transit_departure = dep_clock

            first_dep = best["legs"][0].get("plannedDeparture") or best["legs"][0].get("departure")
            last_arr = best["legs"][-1].get("plannedArrival") or best["legs"][-1].get("arrival")

            total_duration = 0
            if first_dep and last_arr:
                f_dt = datetime.fromisoformat(first_dep[:19])
                l_dt = datetime.fromisoformat(last_arr[:19])
                total_duration = max(0, int((l_dt - f_dt).total_seconds() / 60))

            departure = first_transit_departure or (legs_data[0]["departure"] if legs_data else "00:00")
            
            result = {
                "departure": departure,
                "legs": legs_data,
                "total_duration": total_duration
            }

            _ROUTE_CACHE["key"] = cache_key
            _ROUTE_CACHE["timestamp"] = now
            _ROUTE_CACHE["data"] = result
            
            print(f"-> ERFOLG über {base_url}! Abfahrt {departure}, {len(legs_data)} Etappen.")
            return result

        except Exception as e:
            print(f"   -> Timeout/Absturz bei {base_url}: {e}")
            continue

    # Wenn BEIDE Server versagen -> MVG Fallback
    fallback_route = get_mvg_fallback(origin_name, dest_name)
    if fallback_route:
        # Auch den Notfall-Fallback kurz cachen
        _ROUTE_CACHE["key"] = cache_key
        _ROUTE_CACHE["timestamp"] = now
        _ROUTE_CACHE["data"] = fallback_route
        return fallback_route
        
    print("-> FEHLER: Alle Server und Fallbacks sind gescheitert. Keine Route möglich.")
    return None