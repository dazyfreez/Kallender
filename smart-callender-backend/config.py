# config.py
import os
from dotenv import load_dotenv

# Lädt die Variablen aus der .env-Datei in die Umgebung
load_dotenv()

HOME_STATION = os.getenv("HOME_STATION", "München Hauptbahnhof")

ICAL_URLS = {
    "google": os.getenv("GOOGLE_ICAL_URL", ""),
    "tum": os.getenv("TUM_ICAL_URL", ""),
}

# Gehzeit zur Station & Puffer vor der Vorlesung
WALK_TO_HOME_STATION_MIN = 5
ARRIVAL_BUFFER_MIN = 10