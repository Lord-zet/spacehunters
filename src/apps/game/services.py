from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from .models import Fleet


@transaction.atomic
def send_transport_fleet(source_planet, target_planet, transporter_count, metal, crystal, user):
    if source_planet.id == target_planet.id:
        return False, "Nie można wysłać floty na tę samą planetę."

    if not source_planet.has_enough_transporters(transporter_count):
        return False, "Nie masz wystarczającej liczby transportowców."

    if not source_planet.has_enough_resources_for_transport(metal, crystal):
        return False, "Nie masz wystarczających zasobów."

    if not source_planet.can_carry_resources(transporter_count, metal, crystal):
        return False, "Ładunek nie mieści się w pojemności transportowców."

    source_planet.transporter_count -= transporter_count
    source_planet.metal -= metal
    source_planet.crystal -= crystal
    source_planet.save()

    now = timezone.now()
    flight_duration = timedelta(minutes=1)

    arrival_time = now + flight_duration
    return_time = arrival_time + flight_duration

    Fleet.objects.create(
        owner=user,
        source_planet=source_planet,
        target_planet=target_planet,
        transporter_count=transporter_count,
        metal=metal,
        crystal=crystal,
        status=Fleet.Status.OUTBOUND,
        departure_time=now,
        arrival_time=arrival_time,
        return_time=return_time,
    )
    return True, f"Wysłano flotę ({transporter_count} szt) transportową z planety {source_planet.name} na {target_planet.name}."


@transaction.atomic
def process_fleets_for_user(user):
    now = timezone.now()

    outbound_fleets = Fleet.objects.select_for_update().filter(
        Q(owner=user) | Q(target_planet__owner=user),
        status=Fleet.Status.OUTBOUND,
        arrival_time__lte=now,
    )

    for fleet in outbound_fleets:
        target_planet = fleet.target_planet
        target_planet.update_resources()

        target_planet.metal += fleet.metal
        target_planet.crystal += fleet.crystal
        target_planet.save()

        fleet.metal = 0
        fleet.crystal = 0
        fleet.status = Fleet.Status.RETURNING
        fleet.save()

    returning_fleets = Fleet.objects.select_for_update().filter(
        owner=user,
        status=Fleet.Status.RETURNING,
        return_time__lte=now,
    )

    for fleet in returning_fleets:
        source_planet = fleet.source_planet
        source_planet.update_resources()

        source_planet.transporter_count += fleet.transporter_count
        source_planet.save()

        fleet.status = Fleet.Status.COMPLETED
        fleet.completed_at = now
        fleet.save()
