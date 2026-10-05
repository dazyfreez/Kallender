# transit_service.py
from datetime import datetime, timedelta
import requests

HEADERS = {"User-Agent": "SmartCalendarDashboard/1.0"}

# Cache-Speicher: Verhindert minütliches Überlasten der API
_ROUTE_CACHE = {
    "key": None,
    "timestamp": None,
    "data": None
}

def get_location_id(query_str: str) -> str | None:
    """Löst einen Namen/eine Adresse in eine eindeutige HAFAS-ID auf."""
    url = "https://v6.db.transport.rest/locations"
    params = {"query": query_str, "results": 1}
    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=8)
        res.raise_for_status()
        results = res.json()
        if results and len(results) > 0:
            return results[0].get("id")
    except Exception as e:
        print(f"Fehler bei Locations-Suche für '{query_str}': {e}")
    return None


def query_route(origin_name: str, dest_name: str, target_arrival: datetime | None = None) -> dict | None:
    """Sucht eine Verbindung mit Umstiegen passend zur Zielzeit (inkl. Cache & 20s Timeout)."""
    global _ROUTE_CACHE
    
    # Cache-Schlüssel bilden (Start + Ziel + Ziel-Uhrzeit)
    arrival_str = target_arrival.strftime("%Y-%m-%d %H:%M") if target_arrival else "now"
    cache_key = f"{origin_name}->{dest_name}@{arrival_str}"

    # Wenn vor weniger als 3 Minuten abgefragt: Cache zurückgeben
    now = datetime.now()
    if _ROUTE_CACHE["key"] == cache_key and _ROUTE_CACHE["timestamp"]:
        if now - _ROUTE_CACHE["timestamp"] < timedelta(minutes=3):
            return _ROUTE_CACHE["data"]

    print(f"-> Berechne neue Route: '{origin_name}' -> '{dest_name}'...")

    origin_id = get_location_id(origin_name)
    dest_id = get_location_id(dest_name)

    if not origin_id or not dest_id:
        print(f"Start- oder Zielort konnte nicht aufgelöst werden.")
        return None

    url = "https://v6.db.transport.rest/journeys"
    params = {
        "from": origin_id,
        "to": dest_id,
        "results": 1,
        "stopovers": "false"
    }

    if target_arrival:
        # ISO-Format ohne Zeitzonen-Offset übergeben, um Encoding-Probleme zu vermeiden
        params["arrival"] = target_arrival.strftime("%Y-%m-%dT%H:%M:%S")

    try:
        # Timeout auf 20 Sekunden erhöht
        res = requests.get(url, params=params, headers=HEADERS, timeout=20)
        res.raise_for_status()
        data = res.json()

        journeys = data.get("journeys", [])
        if not journeys:
            print("Keine Route zur gewählten Zeit gefunden.")
            return None

        best = journeys[0]
        legs_data = []
        first_transit_departure = None

        for leg in best.get("legs", []):
            is_walk = leg.get("walking", False)
            
            if is_walk:
                line_name = "Fußweg"
                direction = leg.get("destination", {}).get("name", "Fußweg")
            else:
                line_name = leg.get("line", {}).get("name", "ÖPNV")
                direction = leg.get("direction", leg.get("destination", {}).get("name"))

            dep_raw = leg.get("plannedDeparture") or leg.get("departure")
            if not dep_raw:
                continue

            dep_dt = datetime.fromisoformat(dep_raw)
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

        first_dep = best["legs"][0].get("departure") or best["legs"][0].get("plannedDeparture")
        last_arr = best["legs"][-1].get("arrival") or best["legs"][-1].get("plannedArrival")

        total_duration = 0
        if first_dep and last_arr:
            duration_td = datetime.fromisoformat(last_arr) - datetime.fromisoformat(first_dep)
            total_duration = max(0, int(duration_td.total_seconds() / 60))

        fallback_dep = legs_data[0]["departure"] if legs_data else "00:00"

        result = {
            "departure": first_transit_departure or fallback_dep,
            "legs": legs_data,
            "total_duration": total_duration
        }

        # Cache aktualisieren
        _ROUTE_CACHE["key"] = cache_key
        _ROUTE_CACHE["timestamp"] = now
        _ROUTE_CACHE["data"] = result

        print(f"-> Route erfolgreich ermittelt ({len(legs_data)} Abschnitte).")
        return result

    except requests.exceptions.Timeout:
        print("-> Zeitüberschreitung: Routenserver hat nicht rechtzeitig geantwortet.")
        return _ROUTE_CACHE.get("data")  # Fallback auf alte Daten, falls vorhanden
    except Exception as e:
        print(f"Fehler bei Routenabfrage: {e}")
        return None