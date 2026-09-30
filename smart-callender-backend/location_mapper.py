# location_mapper.py
def resolve_station(location_str: str) -> str:
  loc = location_str.lower()
  if any(k in loc for k in ["mw", "fmi", "garching", "boltzmann", "interim"]):
    return "Garching-Forschungszentrum"
  elif any(
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
  elif "karlstr" in loc:
    return "Karlstraße"

  # Fallback: String als Haltestellen-Suchbegriff belassen
  return location_str.strip()