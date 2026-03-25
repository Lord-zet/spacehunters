from django.utils import timezone
from .models import Fleet

def send_transport_fleet(source_planet, target_planet, transporter_count, metal, crystal, user):
    if source_planet.id == target_planet.id:
        source_planet.save()
        return False, "Nie można wysłać floty na tę samą planetę."

    if not source_planet.has_enough_transporters(transporter_count):
        source_planet.save()
        return False, "Nie masz wystarczającej liczby transportowców."

    if not source_planet.has_enough_resources_for_transport(metal, crystal):
        source_planet.save()
        return False, "Nie masz wystarczających zasobów."

    if not source_planet.can_carry_resources(transporter_count, metal, crystal):
        source_planet.save()
        return False, "Ładunek nie mieści się w pojemności transportowców."

    source_planet.transporter_count -= transporter_count
    source_planet.metal -= metal
    source_planet.crystal -= crystal
    source_planet.save()

    target_planet.transporter_count += transporter_count
    target_planet.metal += metal
    target_planet.crystal += crystal
    target_planet.save()

    Fleet.objects.create(
        owner=user,
        source_planet=source_planet,
        target_planet=target_planet,
        transporter_count=transporter_count,
        metal=metal,
        crystal=crystal,
        status=Fleet.Status.OUTBOUND,
        departure_time=timezone.now(),
        arrival_time=timezone.now() + timedelta(minutes=1),
    )
    return True, f"Wysłano flotę ({transporter_count} szt) transportową z planety {source_planet.name} na {target_planet.name}."
