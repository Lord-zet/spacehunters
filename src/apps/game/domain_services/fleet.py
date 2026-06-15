import math
from datetime import timedelta
from dataclasses import dataclass

from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from apps.game.models import Fleet, Planet, PlanetShip, FleetShip
from apps.game.domain.exceptions import (
    FleetError,
    CargoCapacityExceededError,
    NotEnoughResourcesError,
    NotEnoughTransportersError,
    SamePlanetTransportError,
    NotEnoughFuelError,
    InvalidStationingTargetError,
)
from apps.game.domain_services.travel import calculate_distance, calculate_flight_time_seconds
from apps.game.ships import SHIPS
from .resources import synchronize_resources, RESOURCE_STATE_FIELDS
from .sync import advance_planet_state


TRANSPORTER_CODE = "transporter"
HELION_DISTANCE_DIVISOR = 1000
MIN_HELION_COST = 1


def get_planet_ship(planet, ship_code: str) -> PlanetShip:
    ship, _ = PlanetShip.objects.get_or_create(
        planet=planet,
        ship_code=ship_code,
        defaults={"quantity": 0},
    )
    return ship


def get_fleet_ship_quantity(fleet, ship_code: str) -> int:
    prefetched = getattr(fleet, "_prefetched_objects_cache", {})
    if "ships" in prefetched:
        for ship in fleet.ships.all():
            if ship.ship_code == ship_code:
                return ship.quantity
        return 0

    ship = fleet.ships.filter(ship_code=ship_code).first()
    return ship.quantity if ship else 0


def calculate_fleet_base_fuel_burn(ship_quantities: dict[str, int]) -> int:
    total = 0
    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue
        ship_config = SHIPS[ship_code]
        total += ship_config["fuel_burn"] * quantity
    return total


def calculate_helion_cost_for_flight(source_planet, target_planet, ship_quantities: dict[str, int]) -> int:
    base_burn = calculate_fleet_base_fuel_burn(ship_quantities)
    if base_burn <= 0:
        return 0

    distance = calculate_distance(source_planet, target_planet)
    raw_cost = (base_burn * distance) / HELION_DISTANCE_DIVISOR
    return max(MIN_HELION_COST, math.ceil(raw_cost))


def transport_capacity(transporter_count: int) -> int:
    return SHIPS[TRANSPORTER_CODE]["cargo_capacity"] * transporter_count


def can_carry_resources(transporter_count: int, metal: int, crystal: int) -> bool:
    return (metal + crystal) <= transport_capacity(transporter_count)


def has_enough_transporters(planet, transporter_count: int) -> bool:
    transporter = get_planet_ship(planet, TRANSPORTER_CODE)
    return transporter.quantity >= transporter_count


def has_enough_resources_for_transport(planet, metal: int, crystal: int) -> bool:
    return planet.metal >= metal and planet.crystal >= crystal


def has_enough_helion_for_flight(planet, helion_cost: int) -> bool:
    return planet.helion >= helion_cost


def ensure_planet_has_enough_ships(planet, ship_quantities: dict[str, int]) -> None:
    transporter_count = ship_quantities.get(TRANSPORTER_CODE, 0)

    if transporter_count <= 0:
        raise FleetError("Liczba transportowców musi być większa od zera.")

    transporter = get_planet_ship(planet, TRANSPORTER_CODE)
    if transporter.quantity < transporter_count:
        raise NotEnoughTransportersError("Nie masz wystarczającej liczby transportowców.")


def deduct_planet_ships(planet, ship_quantities: dict[str, int]) -> None:
    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue
        planet_ship = get_planet_ship(planet, ship_code)
        planet_ship.quantity -= quantity
        planet_ship.save(update_fields=["quantity"])


def create_fleet_ships(fleet, ship_quantities: dict[str, int]) -> None:
    fleet_ships = [
        FleetShip(
            fleet=fleet,
            ship_code=ship_code,
            quantity=quantity,
        )
        for ship_code, quantity in ship_quantities.items()
        if quantity > 0
    ]
    FleetShip.objects.bulk_create(fleet_ships)


def add_planet_ships(planet, ship_code: str, quantity: int) -> None:
    if quantity <= 0:
        return

    planet_ship = (
        PlanetShip.objects
        .select_for_update()
        .filter(
            planet=planet,
            ship_code=ship_code,
        )
        .first()
    )

    if planet_ship is None:
        planet_ship = PlanetShip.objects.create(
            planet=planet,
            ship_code=ship_code,
            quantity=0,
        )

    planet_ship.quantity += quantity
    planet_ship.save(update_fields=["quantity"])


def deliver_fleet_resources_to_planet(fleet, planet) -> None:
    planet.metal += fleet.metal
    planet.crystal += fleet.crystal

    planet.save(update_fields=["metal", "crystal"])


def add_fleet_ships_to_planet(fleet, planet) -> None:
    for fleet_ship in fleet.ships.all():
        add_planet_ships(
            planet,
            fleet_ship.ship_code,
            fleet_ship.quantity,
        )


def handle_transport_arrival(fleet, *, at) -> None:
    advance_result = advance_planet_state(
        fleet.target_planet,
        at=at,
    )
    target_planet = advance_result.planet

    deliver_fleet_resources_to_planet(
        fleet,
        target_planet,
    )

    fleet.metal = 0
    fleet.crystal = 0
    fleet.status = Fleet.Status.RETURNING

    fleet.save(update_fields=["metal", "crystal", "status"])


def handle_station_arrival(fleet, *, at) -> None:
    advance_result = advance_planet_state(
        fleet.target_planet,
        at=at,
    )
    target_planet = advance_result.planet

    deliver_fleet_resources_to_planet(
        fleet,
        target_planet,
    )

    add_fleet_ships_to_planet(
        fleet,
        target_planet,
    )

    fleet.metal = 0
    fleet.crystal = 0
    fleet.status = Fleet.Status.COMPLETED
    fleet.return_time = None

    fleet.save(update_fields=["metal", "crystal", "status", "return_time"])


def handle_fleet_return(fleet, *, at) -> None:
    advance_result = advance_planet_state(
        fleet.source_planet,
        at=at,
    )
    source_planet = advance_result.planet

    add_fleet_ships_to_planet(
        fleet,
        source_planet,
    )

    fleet.status = Fleet.Status.COMPLETED
    fleet.save(update_fields=["status"])


def handle_outbound_fleet_arrival(fleet, *, at) -> None:
    if fleet.mission_type == Fleet.MissionType.TRANSPORT:
        handle_transport_arrival(fleet, at=at)
        return

    if fleet.mission_type == Fleet.MissionType.STATION:
        handle_station_arrival(fleet, at=at)
        return

    raise FleetError("Nieobsługiwany typ misji floty.")


@transaction.atomic
def _send_fleet_mission(
    source_planet,
    target_planet,
    ship_quantities: dict[str, int],
    metal: int,
    crystal: int,
    user,
    mission_type: str,
):
    now = timezone.now()

    source_planet = Planet.objects.select_for_update().get(pk=source_planet.pk)
    target_planet = Planet.objects.select_for_update().get(pk=target_planet.pk)

    synchronize_resources(source_planet, at=now, save=False)

    if source_planet.id == target_planet.id:
        raise SamePlanetTransportError("Nie można wysłać floty na tę samą planetę.")

    if metal < 0 or crystal < 0:
        raise FleetError("Nie można wysłać ujemnej ilości surowców.")

    if mission_type == Fleet.MissionType.STATION and source_planet.owner_id != target_planet.owner_id:
        raise InvalidStationingTargetError("Misja stacjonowania jest możliwa tylko na własną planetę.")

    ensure_planet_has_enough_ships(source_planet, ship_quantities)

    transporter_count = ship_quantities.get(TRANSPORTER_CODE, 0)

    if not has_enough_resources_for_transport(source_planet, metal, crystal):
        raise NotEnoughResourcesError("Nie masz wystarczających zasobów.")

    if not can_carry_resources(transporter_count, metal, crystal):
        raise CargoCapacityExceededError("Ładunek nie mieści się w pojemności transportowców.")

    helion_cost = calculate_helion_cost_for_flight(
        source_planet,
        target_planet,
        ship_quantities,
    )

    if not has_enough_helion_for_flight(source_planet, helion_cost):
        raise NotEnoughFuelError("Nie masz wystarczającej ilości helionu na lot.")

    deduct_planet_ships(source_planet, ship_quantities)
    source_planet.metal -= metal
    source_planet.crystal -= crystal
    source_planet.helion -= helion_cost
    source_planet.save(update_fields=RESOURCE_STATE_FIELDS)

    flight_time_seconds = calculate_flight_time_seconds(source_planet, target_planet)
    flight_duration = timedelta(seconds=flight_time_seconds)

    arrival_time = now + flight_duration
    return_time = arrival_time + flight_duration if mission_type == Fleet.MissionType.TRANSPORT else None

    fleet = Fleet.objects.create(
        owner=user,
        source_planet=source_planet,
        target_planet=target_planet,
        metal=metal,
        crystal=crystal,
        helion_cost=helion_cost,
        mission_type=mission_type,
        status=Fleet.Status.OUTBOUND,
        departure_time=now,
        arrival_time=arrival_time,
        return_time=return_time,
    )

    create_fleet_ships(fleet, ship_quantities)

    return fleet


def send_transport_fleet(source_planet, target_planet, transporter_count, metal, crystal, user):
    return _send_fleet_mission(
        source_planet=source_planet,
        target_planet=target_planet,
        ship_quantities={TRANSPORTER_CODE: transporter_count},
        metal=metal,
        crystal=crystal,
        user=user,
        mission_type=Fleet.MissionType.TRANSPORT,
    )


def send_stationing_fleet(source_planet, target_planet, transporter_count, metal, crystal, user):
    return _send_fleet_mission(
        source_planet=source_planet,
        target_planet=target_planet,
        ship_quantities={TRANSPORTER_CODE: transporter_count},
        metal=metal,
        crystal=crystal,
        user=user,
        mission_type=Fleet.MissionType.STATION,
    )


@dataclass(frozen=True, slots=True)
class FleetEvent:
    fleet: Fleet
    event_type: str
    event_time: timezone.datetime


@transaction.atomic
def process_fleets_for_user(user, *, at=None):
    now = at or timezone.now()

    outbound_fleets = list(
        Fleet.objects
        .select_for_update()
        .select_related("target_planet", "source_planet")
        .prefetch_related("ships")
        .filter(
            Q(owner=user) | Q(target_planet__owner=user),
            status=Fleet.Status.OUTBOUND,
            arrival_time__lte=now,
        )
    )

    returning_fleets = list(
        Fleet.objects
        .select_for_update()
        .select_related("source_planet", "target_planet")
        .prefetch_related("ships")
        .filter(
            owner=user,
            status=Fleet.Status.RETURNING,
            return_time__lte=now,
        )
    )

    events = [
        FleetEvent(
            fleet=fleet,
            event_type="arrival",
            event_time=fleet.arrival_time,
        )
        for fleet in outbound_fleets
    ]

    events.extend(
        FleetEvent(
            fleet=fleet,
            event_type="return",
            event_time=fleet.return_time,
        )
        for fleet in returning_fleets
        if fleet.return_time is not None
    )

    events.sort(
        key=lambda event: (
            event.event_time,
            event.fleet.pk,
            event.event_type,
        )
    )

    for event in events:
        if event.event_type == "arrival":
            handle_outbound_fleet_arrival(event.fleet, at=event.event_time)
            continue

        if event.event_type == "return":
            handle_fleet_return(event.fleet, at=event.event_time)
            continue

        raise FleetError("Nieobsługiwany typ zdarzenia floty.")
