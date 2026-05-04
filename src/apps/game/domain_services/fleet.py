from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from apps.game.models import Fleet, Planet
from apps.game.domain.exceptions import (
    FleetError,
    CargoCapacityExceededError,
    NotEnoughResourcesError,
    NotEnoughTransportersError,
    SamePlanetTransportError,
)
from apps.game.domain_services.travel import calculate_distance, calculate_flight_time_seconds
from .resources import synchronize_resources

TRANSPORTER_CAPACITY = 1000


def transport_capacity(transporter_count: int) -> int:
    return TRANSPORTER_CAPACITY * transporter_count


def can_carry_resources(transporter_count: int, metal: int, crystal: int) -> bool:
    return (metal + crystal) <= transport_capacity(transporter_count)


def has_enough_transporters(planet, transporter_count: int) -> bool:
    return planet.transporter_count >= transporter_count


def has_enough_resources_for_transport(planet, metal: int, crystal: int) -> bool:
    return planet.metal >= metal and planet.crystal >= crystal


@transaction.atomic
def send_transport_fleet(source_planet, target_planet, transporter_count, metal, crystal, user):
    now = timezone.now()

    source_planet = Planet.objects.select_for_update().get(pk=source_planet.pk)
    target_planet = Planet.objects.select_for_update().get(pk=target_planet.pk)

    synchronize_resources(source_planet, at=now, save=False)

    if source_planet.id == target_planet.id:
        raise SamePlanetTransportError("Nie można wysłać floty na tę samą planetę.")

    if transporter_count <= 0:
        raise FleetError("Liczba transportowców musi być większa od zera.")

    if metal < 0 or crystal < 0:
        raise FleetError("Nie można wysłać ujemnej ilości surowców.")

    if not has_enough_transporters(source_planet, transporter_count):
        raise NotEnoughTransportersError("Nie masz wystarczającej liczby transportowców.")

    if not has_enough_resources_for_transport(source_planet, metal, crystal):
        raise NotEnoughResourcesError("Nie masz wystarczających zasobów.")

    if not can_carry_resources(transporter_count, metal, crystal):
        raise CargoCapacityExceededError("Ładunek nie mieści się w pojemności transportowców.")

    source_planet.transporter_count -= transporter_count
    source_planet.metal -= metal
    source_planet.crystal -= crystal
    source_planet.save(update_fields=["transporter_count", "metal", "crystal", "last_resource_update"])

    flight_time_seconds = calculate_flight_time_seconds(source_planet, target_planet)
    flight_duration = timedelta(seconds=flight_time_seconds)

    arrival_time = now + flight_duration
    return_time = arrival_time + flight_duration

    fleet = Fleet.objects.create(
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

    return fleet


@transaction.atomic
def process_fleets_for_user(user, *, at=None):
    now = at or timezone.now()

    outbound_fleets = (
        Fleet.objects
        .select_for_update()
        .select_related("target_planet", "source_planet")
        .filter(
            Q(owner=user) | Q(target_planet__owner=user),
            status=Fleet.Status.OUTBOUND,
            arrival_time__lte=now,
        )
    )

    for fleet in outbound_fleets:
        target_planet = Planet.objects.select_for_update().get(pk=fleet.target_planet_id)
        synchronize_resources(target_planet, at=now, save=False)

        target_planet.metal += fleet.metal
        target_planet.crystal += fleet.crystal
        target_planet.save(update_fields=["metal", "crystal", "last_resource_update"])

        fleet.metal = 0
        fleet.crystal = 0
        fleet.status = Fleet.Status.RETURNING
        fleet.save(update_fields=["metal", "crystal", "status"])

    returning_fleets = (
        Fleet.objects
        .select_for_update()
        .select_related("source_planet")
        .filter(
            owner=user,
            status=Fleet.Status.RETURNING,
            return_time__lte=now,
        )
    )

    for fleet in returning_fleets:
        source_planet = Planet.objects.select_for_update().get(pk=fleet.source_planet_id)
        synchronize_resources(source_planet, at=now, save=False)

        source_planet.transporter_count += fleet.transporter_count
        source_planet.save(update_fields=["transporter_count", "last_resource_update"])

        fleet.status = Fleet.Status.COMPLETED
        fleet.save(update_fields=["status"])
