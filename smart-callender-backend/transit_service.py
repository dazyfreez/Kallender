# transit_service.py
from datetime import datetime
import requests

# WICHTIG: Die API blockiert Anfragen gnadenlos, wenn hier keine E-Mail-Adresse steht!
HEADERS = {"User-Agent": "SmartCalendarDashboard/1.0 (christian@example.com)"}

# Doppel-Server-Strategie: Wenn DB hängt, springt sofort der Berliner HAFAS ein (kennt auch München!)
API_SERVERS = [
    "https://v6.db.transport.rest",
    "https://v6.bvg.transport.rest"
]

# Speichert Haltestellen-IDs lokal, um Netzwerk-Ladezeiten zu sparen
_LOC_CACHE = {}

def get_location_id(query_str: str, base_url: str) -> str | None:
    if query_str in _LOC_CACHE:
        return _LOC_CACHE[query_str]

    try:
        # Kurzer Timeout, damit wir bei einem Hänger sofort zum nächsten Server springen
        res = requests.get(f"{base_url}/locations", params={"query": query_str, "results": 1}, headers=HEADERS, timeout=4)
        res.raise_for_status()
        data = res.json()
        if data:
            loc_id = data[0].get("id")
            _LOC_CACHE[query_str] = loc_id
            return loc_id
    except Exception:
        pass
    return None

def query_route(origin_name: str, dest_name: str, target_arrival: datetime) -> dict | None:
    print(f"-> Suche vollständige Route: '{origin_name}' -> '{dest_name}'...")
    
    for base_url in API_SERVERS:
        origin_id = get_location_id(origin_name, base_url)
        dest_id = get_location_id(dest_name, base_url)

        if not origin_id or not dest_id:
            continue  # Fallback: Direkt den nächsten Server probieren

        params = {
            "from": origin_id,
            "to": dest_id,
            "results": 1,
            "stopovers": "false",
            "arrival": target_arrival.strftime("%Y-%m-%dT%H:%M:%S")
        }

        try:
            res = requests.get(f"{base_url}/journeys", params=params, headers=HEADERS, timeout=6)
            res.raise_for_status()
            data = res.json()
            
            journeys = data.get("journeys", [])
            if not journeys:
                continue
                
            best = journeys[0]
            legs_data = []
            first_transit_departure = None

            for leg in best.get("legs", []):
                is_walk = leg.get("walking", False)
                line_name = "Fußweg" if is_walk else leg.get("line", {}).get("name", "ÖPNV")
                direction = leg.get("direction", leg.get("destination", {}).get("name", ""))

                dep_raw = leg.get("plannedDeparture") or leg.get("departure")
                if not dep_raw:
                    continue

                # Die API liefert Zeiten mit Zeitzone (z.B. +02:00). [:19] schneidet das ab für eine saubere Berechnung.
                dep_dt = datetime.fromisoformat(dep_raw[:19])
                dep_clock = dep_dt.strftime("%H:%M")
                
                delay_sec = leg.get("departureDelay")
                delay_min = int(delay_sec / 60) if delay_sec else 0

                legs_data.append({
                    "name": line_name,
                    "direction": direction,
                    "departure": dep_clock,
                    "delay": delay_min
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

            print(f"-> Route erfolgreich über {base_url} berechnet.")

            return {
                "departure": first_transit_departure or (legs_data[0]["departure"] if legs_data else "00:00"),
                "legs": legs_data,
                "total_duration": total_duration
            }

        except Exception:
            # Bei Server-Timeout geräuschlos zum Ersatz-Server springen
            continue

    print("-> Alle Server haben einen Timeout gemeldet oder keine Route gefunden.")
    return None