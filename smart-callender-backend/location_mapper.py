# location_mapper.py
def resolve_station(location_str: str) -> str:
  if not location_str:
    return ""

  loc = location_str.lower().strip()

  # 1. Bekannte TUM-Standorte
  if any(k in loc for k in ["mw", "fmi", "garching", "boltzmann", "interim"]):
    return "Garching-Forschungszentrum"
  if any(
      k in loc
      for k in [
          "stammgelände",
          "theresien",
          "arcis",
          "n1179",
          "audimax",
          "hörsaal 1",
      ]
  ):
    return "Theresienstraße"

  # 2. Eigene Alltags-Orte (Supermärkte, Gyms, etc.)
  # Hier die nächstgelegene Haltestelle eintragen:
  if "hit" in loc:
    return "München, Fasangarten"  # oder z. B. "Pasing", je nachdem welcher HIT gemeint ist
  if "fitness" in loc or "gym" in loc:
    return "München Marienplatz"

  # 3. Fallback: Erstes Wort/Straße zurückgeben
  return location_str.split(",")[0].strip()