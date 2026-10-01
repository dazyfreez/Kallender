# calendar_service.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from icalendar import Calendar
import recurring_ical_events
import requests

LOCAL_TZ = ZoneInfo("Europe/Berlin")


def fetch_upcoming_events(ics_urls: dict, hours_ahead: int = 16) -> list:
  """Lädt iCal-Feeds herunter und liefert anstehende Termine sortiert zurück."""
  now = datetime.now(LOCAL_TZ)
  window_end = now + timedelta(hours=hours_ahead)

  all_events = []

  for source_name, url in ics_urls.items():
    if not url or "http" not in url:
      continue

    try:
      response = requests.get(url, timeout=10)
      response.raise_for_status()
      calendar = Calendar.from_ical(response.text)

      # recurring-ical-events entpackt alle RRULE-Serientermine für das Zeitfenster
      events_in_range = recurring_ical_events.of(calendar).between(
          now, window_end
      )

      for event in events_in_range:
        dtstart = event.get("DTSTART").dt

        # Ganztägige Termine (reines date) in timezone-aware datetime umwandeln
        if not isinstance(dtstart, datetime):
          dtstart = datetime.combine(dtstart, datetime.min.time(), tzinfo=LOCAL_TZ)
        elif dtstart.tzinfo is None:
          dtstart = dtstart.replace(tzinfo=LOCAL_TZ)
        else:
          dtstart = dtstart.astimezone(LOCAL_TZ)

        # Bereits vergangene Termine ignorieren
        if dtstart < now:
          continue

        all_events.append({
            "source": source_name,
            "title": str(event.get("SUMMARY", "Ohne Titel")),
            "start": dtstart,
            "location": str(event.get("LOCATION", "")).strip(),
        })

    except requests.RequestException as e:
      print(f"Fehler beim Laden des Kalenders '{source_name}': {e}")
    except Exception as e:
      print(f"Fehler beim Parsen von '{source_name}': {e}")

  # Chronologisch nach Startzeit sortieren
  all_events.sort(key=lambda item: item["start"])
  return all_events