# main.py
from datetime import datetime, timedelta
import json
import time
from zoneinfo import ZoneInfo
from calendar_service import fetch_upcoming_events
from config import ARRIVAL_BUFFER_MIN, HOME_STATION, ICAL_URLS
from location_mapper import resolve_station
from transit_service import query_route

LOCAL_TZ = ZoneInfo("Europe/Berlin")


def build_dashboard_data():
  print(f"\n[{datetime.now(LOCAL_TZ).strftime('%H:%M:%S')}] Aktualisiere Daten...")

  # 1. Kalender abfragen
  upcoming = fetch_upcoming_events(ICAL_URLS, hours_ahead=12)

  if not upcoming:
    return {
        "status": "idle",
        "message": "Keine weiteren Termine für heute.",
        "next_event": None,
        "transit": None,
    }

  # 2. Nächsten Termin auswählen
  next_event = upcoming[0]
  event_title = next_event["title"]
  event_start = next_event["start"]
  location_raw = next_event["location"]

  dashboard_data = {
      "status": "ok",
      "next_event": {
          "title": event_title,
          "start_clock": event_start.strftime("%H:%M"),
          "raw_location": location_raw,
      },
      "transit": None,
  }

  # 3. Zielhaltestelle über Mapper auflösen
  target_station = resolve_station(location_raw)

  # 4. Route mit pyhafas berechnen (falls Ziel vorhanden)
  if target_station:
    # Gewünschte Ankunftszeit am Hörsaal (z. B. 10 Min vor Beginn)
    target_arrival = event_start - timedelta(minutes=ARRIVAL_BUFFER_MIN)

    route = query_route(
        origin_name=HOME_STATION,
        dest_name=target_station,
        target_arrival=target_arrival,
    )
    dashboard_data["transit"] = route
    dashboard_data["transit_target_station"] = target_station

  return dashboard_data


def main():
  # Testlauf: Fragt Daten ab und gibt das resultierende JSON lesbar im Terminal aus
  payload = build_dashboard_data()
  print("\nFertiges Datenpaket für das Display:")
  print(json.dumps(payload, indent=2, default=str, ensure_ascii=False))


if __name__ == "__main__":
  main()