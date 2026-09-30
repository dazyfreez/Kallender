# transit_service.py
from datetime import datetime
from pyhafas import HafasClient
from pyhafas.profile import DBProfile

client = HafasClient(DBProfile())


def query_route(origin_name: str, dest_name: str, target_arrival: datetime):
  origin = client.locations(origin_name)[0]
  dest = client.locations(dest_name)[0]

  journeys = client.journeys(
      origin=origin,
      destination=dest,
      date=target_arrival,  # HAFAS plant Verbindungen passend zur Ankunftszeit
  )

  if not journeys:
    return None

  best = journeys[0]
  first_leg = (
      best.legs[1]
      if best.legs[0].name == "Fußweg" and len(best.legs) > 1
      else best.legs[0]
  )

  delay_min = (
      int(first_leg.departureDelay.total_seconds() / 60)
      if first_leg.departureDelay
      else 0
  )

  return {
      "line": first_leg.name,
      "direction": first_leg.direction,
      "departure": first_leg.departure.strftime("%H:%M"),
      "delay": delay_min,
      "total_duration": int(best.duration.total_seconds() / 60),
  }