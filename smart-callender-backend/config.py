# config.py
HOME_STATION = "München Sendlinger Tor"  # Deine nächste Haltestelle

# Geheime iCal-URLs (aus Google Kalender & TUMonline)
ICAL_URLS = {
    "google": "https://calendar.google.com/calendar/ical/.../basic.ics", //das it noch nicht fix
    "tum": "https://campus.tum.de/tumonline/.../iCal?...&pToken=...",
}

# Gehzeit zur Heimathaltestelle + Sicherheitspuffer am Ziel (in Minuten)
WALK_TO_HOME_STATION_MIN = 5
ARRIVAL_BUFFER_MIN = 10