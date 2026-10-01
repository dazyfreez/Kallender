# transit_service.py
from datetime import datetime
import requests


def get_station_id(station_name: str) -> str | None:
  """Sucht nach einer Station und liefert deren globale MVG-ID."""
  url = "https://www.mvg.de/api/bgw-pt/v3/locations"
  params = {"query": station_name}
  headers = {"User-Agent": "SmartCalendar/1.0"}

  try:
    res = requests.get(url, params=params, headers=headers, timeout=5)
    res.raise_for_status()
    locations = res.json()
    if locations:
      # Erste gefundene Haltestelle
      return locations[0].get("globalId")
  except Exception as e:
    print(f"Fehler bei Haltestellensuche ({station_name}): {e}")
  return None


def query_route(
    origin_name: str, dest_name: str, target_arrival: datetime
) -> dict | None:
  """Holt Live-Abfahrten an der Heimathaltestelle passend zur Richtung."""
  origin_id = get_station_id(origin_name)
  if not origin_id:
    print(f"Start-Haltestelle '{origin_name}' nicht gefunden.")
    return None

  url = "https://www.mvg.de/api/bgw-pt/v3/departures"
  params = {
      "globalId": origin_id,
      "limit": 10,
      "offsetInMinutes": 0,  # Abfahrten ab jetzt
  }
  headers = {"User-Agent": "SmartCalendar/1.0"}

  try:
    res = requests.get(url, params=params, headers=headers, timeout=5)
    res.raise_for_status()
    departures = res.json()

    if not departures:
      return None

    # Suche nach einer Abfahrt, die grob zur Zielrichtung passt,
    # oder nimm die nächste reguläre Verbindung:
    matching_dep = None
    dest_lower = dest_name.lower()

    for dep in departures:
      dest_title = dep.get("destination", "").lower()
      # Prüfen, ob der Zug in Richtung des Ziels fährt (z. B. U6 Richtung Garching)
      if dest_lower in dest_title or any(
          part in dest_title for part in dest_lower.split()
      ):
        matching_dep = dep
        break

    # Falls kein exakter Richtungs-Match, nimm die allernächste Abfahrt
    best = matching_dep if matching_dep else departures[0]

    planned_time = datetime.fromtimestamp(best.get("plannedDepartureTime") / 1000)
    actual_time = datetime.fromtimestamp(
        best.get("realtimeDepartureTime", best.get("plannedDepartureTime")) / 1000
    )
    delay_min = max(0, int((actual_time - planned_time).total_seconds() / 60))

    return {
        "line": best.get("label"),  # z. B. "U6"
        "direction": best.get("destination"),  # z. B. "Garching-Forschungszentrum"
        "departure": planned_time.strftime("%H:%M"),
        "delay": delay_min,
        "is_cancelled": best.get("cancelled", False),
    }

  except Exception as e:
    print(f"Fehler beim Abruf der MVG-Abfahrten: {e}")
    return None