# transit_service.py
from datetime import datetime
from pyhafas import HafasClient
from pyhafas.profile import OEBBProfile

# Trick: Das ÖBB-Profil liefert uns problemlos alle MVG-Echtzeitdaten!
client = HafasClient(OEBBProfile())

def query_route(origin_name: str, dest_name: str, target_arrival: datetime):
    try:
        # 1. Start und Ziel in IDs auflösen
        origin = client.locations(origin_name)[0]
        dest = client.locations(dest_name)[0]

        # 2. Komplette Route (Journey) passend zur Ankunftszeit suchen
        journeys = client.journeys(
            origin=origin,
            destination=dest,
            date=target_arrival
        )

        if not journeys:
            return None

        best = journeys[0]
        legs_data = []

        # 3. Alle Umstiege (Legs) auslesen
        for leg in best.legs:
            delay_min = int(leg.departureDelay.total_seconds() / 60) if leg.departureDelay else 0
            
            # Falls es ein Fußweg ist, nehmen wir den Zielort als Richtung
            direction = leg.direction if leg.direction else leg.destination.name

            legs_data.append({
                "name": leg.name,  # z. B. "U 6" oder "Fußweg"
                "direction": direction,
                "departure": leg.departure.strftime("%H:%M"),
                "delay": delay_min
            })

        # Für die rote Kalender-Linie brauchen wir den allerersten Start (nach einem möglichen Fußweg)
        first_transit_leg = best.legs[1] if best.legs[0].name == "Fußweg" and len(best.legs) > 1 else best.legs[0]

        return {
            "departure": first_transit_leg.departure.strftime("%H:%M"),
            "legs": legs_data,
            "total_duration": int(best.duration.total_seconds() / 60)
        }

    except Exception as e:
        print(f"Fehler bei Routenabfrage über ÖBB: {e}")
        return None