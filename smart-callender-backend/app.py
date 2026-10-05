# app.py
from flask import Flask, jsonify, render_template
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Eure bisherigen Importe:
from calendar_service import fetch_upcoming_events
from config import ARRIVAL_BUFFER_MIN, HOME_STATION, ICAL_URLS, WALK_TO_HOME_STATION_MIN
from location_mapper import resolve_station
from transit_service import query_route

app = Flask(__name__)
LOCAL_TZ = ZoneInfo("Europe/Berlin")


def build_dashboard_data():
  print(f"\n[{datetime.now(LOCAL_TZ).strftime('%H:%M:%S')}] Aktualisiere API Daten...")

  # 1. Kalender abfragen
  upcoming = fetch_upcoming_events(ICAL_URLS, hours_ahead=12)

  # 2. Termine für das Frontend aufbereiten (Farben & JS-lesbare Zeiten)
  frontend_events = []
  for event in upcoming:
    color = "#3070b3" if event.get("source") == "tum" else "#e67e22"
    frontend_events.append({
        "title": event["title"],
        "start_clock": event["start"].strftime("%H:%M"),
        # ISO-Format ist wichtig, damit JavaScript später die Pixel-Position ausrechnen kann
        "start_iso": event["start"].isoformat(),
        "location": event["location"],
        "color": color
    })

  if not upcoming:
    return {
        "status": "idle",
        "message": "Keine weiteren Termine für heute.",
        "events": [],
        "transit": None,
        "leave_time": None,
    }

  # 3. Nächsten Termin für das ÖPNV-Routing auswählen
  next_event = upcoming[0]
  target_station = resolve_station(next_event["location"])
  
  route = None
  leave_time_str = None

  # 4. Route mit MVG berechnen (falls Ziel vorhanden)
  if target_station:
    target_arrival = next_event["start"] - timedelta(minutes=ARRIVAL_BUFFER_MIN)
    
    route = query_route(
        origin_name=HOME_STATION,
        dest_name=target_station,
        target_arrival=target_arrival,
    )

    # 5. Die "LOSGEHEN"-Zeit berechnen für die rote Linie im Kalender
    if route and route.get("departure"):
      # "departure" ist z.B. "09:30" - wir wandeln das kurz um, ziehen den Fußweg ab
      dep_time = datetime.strptime(route["departure"], "%H:%M")
      leave_time = dep_time - timedelta(minutes=WALK_TO_HOME_STATION_MIN)
      leave_time_str = leave_time.strftime("%H:%M")

  # Fertiges Paket für den Browser schnüren
  return {
      "status": "ok",
      "events": frontend_events,  # Jetzt schicken wir ALLE Termine ans Display
      "transit": route,
      "transit_target_station": target_station,
      "leave_time": leave_time_str,
  }


# --- FLASK WEB-ROUTEN ---

@app.route("/")
def index():
  # Lädt die HTML-Datei, die wir im Ordner 'templates' anlegen werden
  return render_template("index.html")

@app.route("/api/data")
def api_data():
  # Gibt das Dictionary automatisch als sauberes JSON an JavaScript zurück
  data = build_dashboard_data()
  return jsonify(data)

if __name__ == "__main__":
  # Startet den Server im lokalen Netzwerk auf Port 5000
  app.run(debug=True, host="0.0.0.0", port=5000)