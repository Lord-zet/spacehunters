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
    UnsupportedFleetMissionError,
    UnknownShipError,
    PlanetOwnershipError,
)
from apps.game.domain_services.travel import calculate_distance, calculate_flight_time_seconds
from apps.game.ships import SHIPS
from apps.game.domain_services.resources import (
    synchronize_resources,
    RESOURCE_STATE_FIELDS,
    Resource,
    ResourceAmounts,
    total_resources,
    has_resources,
    combine_resources,
    subtract_resources,
    resource_amounts_to_model_fields,
    transfer_resources,
    normalize_resource_amounts
)
from .sync import advance_planet_state
from apps.game.fleet_speed_profiles import (
    DEFAULT_FLEET_SPEED_PROFILE,
    get_fleet_fuel_multiplier,
    get_fleet_speed_multiplier,
)



TRANSPORTER_CODE = "transporter"
HELION_DISTANCE_DIVISOR = 1000
MIN_HELION_COST = 1
SUPPORTED_FLEET_MISSIONS = {
    Fleet.MissionType.TRANSPORT,
    Fleet.MissionType.STATION,
}


def get_planet_ship(planet, ship_code: str) -> PlanetShip:
    ship, _ = PlanetShip.objects.get_or_create(
        planet=planet,
        ship_code=ship_code,
        defaults={"quantity": 0},
    )
    return ship


def calculate_fleet_base_fuel_burn(ship_quantities: dict[str, int]) -> int:
    total = 0
    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue
        ship_config = SHIPS[ship_code]
        total += ship_config["fuel_burn"] * quantity
    return total


def apply_fuel_multiplier(base_cost: int, fuel_multiplier: float) -> int:
    if base_cost <= 0:
        return 0

    return int(math.ceil(base_cost * fuel_multiplier))


def calculate_helion_cost_for_flight(source_planet, target_planet, ship_quantities: dict[str, int], fuel_multiplier=1.0) -> int:
    base_burn = calculate_fleet_base_fuel_burn(ship_quantities)
    if base_burn <= 0:
        return 0

    distance = calculate_distance(source_planet, target_planet)
    raw_cost = (base_burn * distance) / HELION_DISTANCE_DIVISOR
    final_cost = apply_fuel_multiplier(int(raw_cost), fuel_multiplier)
    return max(MIN_HELION_COST, math.ceil(final_cost))


def calculate_cargo_capacity(ship_quantities: dict[str, int]) -> int:
    total = 0

    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue

        ship_config = SHIPS[ship_code]
        total += ship_config.get("cargo_capacity", 0) * quantity

    return total


def ensure_planet_has_enough_ships(planet, ship_quantities: dict[str, int]) -> None:
    validate_ship_quantities(ship_quantities)

    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue

        planet_ship = get_planet_ship(planet, ship_code)

        if planet_ship.quantity < quantity:
            if ship_code == TRANSPORTER_CODE:
                raise NotEnoughTransportersError("Nie masz wystarczającej liczby transportowców.")

            raise FleetError("Nie masz wystarczającej liczby statków.")


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


def add_fleet_ships_to_planet(fleet, planet) -> None:
    for fleet_ship in fleet.ships.all():
        add_planet_ships(
            planet,
            fleet_ship.ship_code,
            fleet_ship.quantity,
        )


def get_safe_fleet_event_time(event_time, *planets):
    safe_time = event_time

    for planet in planets:
        if (
            planet.last_resource_update
            and planet.last_resource_update > safe_time
        ):
            safe_time = planet.last_resource_update

    return safe_time


def handle_transport_arrival(fleet, *, at) -> None:
    target_planet = (
        Planet.objects
        .select_for_update()
        .get(pk=fleet.target_planet_id)
    )

    safe_event_time = get_safe_fleet_event_time(at, target_planet)

    advance_result = advance_planet_state(target_planet, at=safe_event_time)

    target_planet = advance_result.planet

    fleet_resource_fields, _ = transfer_resources(
        source=fleet,
        target=target_planet,
    )

    fleet.status = Fleet.Status.RETURNING

    target_planet.save(update_fields=RESOURCE_STATE_FIELDS)

    fleet.save(update_fields=[*fleet_resource_fields, "status"])


def handle_station_arrival(fleet, *, at) -> None:
    target_planet = (
        Planet.objects
        .select_for_update()
        .get(pk=fleet.target_planet_id)
    )

    safe_event_time = get_safe_fleet_event_time(at, target_planet)

    advance_result = advance_planet_state(target_planet, at=safe_event_time)

    target_planet = advance_result.planet

    fleet_resource_fields, _ = transfer_resources(
        source=fleet,
        target=target_planet,
    )

    add_fleet_ships_to_planet(fleet, target_planet)

    fleet.status = Fleet.Status.COMPLETED
    fleet.return_time = None

    target_planet.save(update_fields=RESOURCE_STATE_FIELDS)

    fleet.save(update_fields=[*fleet_resource_fields, "status", "return_time"])


def handle_fleet_return(fleet, *, at) -> None:
    source_planet = (
        Planet.objects
        .select_for_update()
        .get(pk=fleet.source_planet_id)
    )

    safe_event_time = get_safe_fleet_event_time(at, source_planet)

    advance_result = advance_planet_state(source_planet, at=safe_event_time)
    source_planet = advance_result.planet

    add_fleet_ships_to_planet(fleet, source_planet)

    fleet.status = Fleet.Status.COMPLETED

    source_planet.save(update_fields=RESOURCE_STATE_FIELDS)
    fleet.save(update_fields=["status"])


FLEET_ARRIVAL_HANDLERS = {
    Fleet.MissionType.TRANSPORT: handle_transport_arrival,
    Fleet.MissionType.STATION: handle_station_arrival,
}


def handle_outbound_fleet_arrival(fleet, *, at) -> None:
    handler = FLEET_ARRIVAL_HANDLERS.get(fleet.mission_type)

    if handler is None:
        raise UnsupportedFleetMissionError("Nieobsługiwany typ misji floty.")

    handler(fleet, at=at)


def ensure_source_planet_belongs_to_user(source_planet, user) -> None:
    if source_planet.owner_id != user.id:
        raise PlanetOwnershipError("Planeta źródłowa nie należy do tego gracza.")


def ensure_supported_mission_type(mission_type: str) -> None:
    if mission_type not in SUPPORTED_FLEET_MISSIONS:
        raise UnsupportedFleetMissionError("Nieobsługiwany typ misji floty.")


def validate_ship_quantities(ship_quantities: dict[str, int]) -> None:
    if not ship_quantities:
        raise FleetError("Flota musi zawierać co najmniej jeden statek.")

    has_any_ship = False

    for ship_code, quantity in ship_quantities.items():
        if ship_code not in SHIPS:
            raise UnknownShipError("Nieznany statek.")

        if quantity < 0:
            raise FleetError("Liczba statków nie może być ujemna.")

        if quantity > 0:
            has_any_ship = True

    if not has_any_ship:
        raise FleetError("Flota musi zawierać co najmniej jeden statek.")


@transaction.atomic
def _send_fleet_mission(
    source_planet,
    target_planet,
    ship_quantities: dict[str, int],
    cargo: ResourceAmounts,
    user,
    mission_type: str,
    speed_profile=DEFAULT_FLEET_SPEED_PROFILE,
    at=None,
):
    now = at or timezone.now()

    cargo = normalize_resource_amounts(cargo)
    ensure_supported_mission_type(mission_type)
    validate_ship_quantities(ship_quantities)

    source_planet = Planet.objects.select_for_update().get(pk=source_planet.pk)
    target_planet = Planet.objects.get(pk=target_planet.pk)

    ensure_source_planet_belongs_to_user(source_planet, user)



    if source_planet.id == target_planet.id:
        raise SamePlanetTransportError("Nie można wysłać floty na tę samą planetę.")

    if mission_type == Fleet.MissionType.STATION and source_planet.owner_id != target_planet.owner_id:
        raise InvalidStationingTargetError("Misja stacjonowania jest możliwa tylko na własną planetę.")

    synchronize_resources(source_planet, at=now, save=False)

    ensure_planet_has_enough_ships(source_planet, ship_quantities)

    if not has_resources(source_planet, cargo):
        raise NotEnoughResourcesError("Nie masz wystarczających zasobów.")

    cargo_amount = total_resources(cargo)
    cargo_capacity = calculate_cargo_capacity(ship_quantities)
    if cargo_amount > cargo_capacity:
        raise CargoCapacityExceededError("Ładunek nie mieści się w pojemności floty.")

    fuel_multiplier = get_fleet_fuel_multiplier(speed_profile)
    helion_cost = calculate_helion_cost_for_flight(
        source_planet,
        target_planet,
        ship_quantities,
        fuel_multiplier,
    )

    fuel = {Resource.HELION: helion_cost}
    required_resources = combine_resources(cargo, fuel)
    if not has_resources(source_planet, required_resources):
        raise NotEnoughFuelError("Nie masz wystarczającej ilości helionu na lot.")

    deduct_planet_ships(source_planet, ship_quantities)

    subtract_resources(source_planet, required_resources)

    source_planet.save(update_fields=RESOURCE_STATE_FIELDS)

    speed_multiplier = get_fleet_speed_multiplier(speed_profile)
    flight_time_seconds = calculate_flight_time_seconds(source_planet, target_planet, speed_multiplier)
    flight_duration = timedelta(seconds=flight_time_seconds)

    arrival_time = now + flight_duration
    if mission_type == Fleet.MissionType.TRANSPORT:
        return_time = arrival_time + flight_duration
    else:
        return_time = None

    fleet_resource_fields = resource_amounts_to_model_fields(cargo, include_missing=True, default=0)

    fleet = Fleet.objects.create(
        owner=user,
        source_planet=source_planet,
        target_planet=target_planet,
        helion_cost=helion_cost,
        mission_type=mission_type,
        status=Fleet.Status.OUTBOUND,
        speed_profile=speed_profile,
        departure_time=now,
        arrival_time=arrival_time,
        return_time=return_time,
        **fleet_resource_fields,
    )

    create_fleet_ships(fleet, ship_quantities)

    return fleet


def send_transport_fleet(source_planet, target_planet, transporter_count, cargo: ResourceAmounts, user,
                         speed_profile=DEFAULT_FLEET_SPEED_PROFILE, at=None):
    return _send_fleet_mission(
        source_planet=source_planet,
        target_planet=target_planet,
        ship_quantities={TRANSPORTER_CODE: transporter_count},
        cargo=cargo,
        speed_profile=speed_profile,
        user=user,
        mission_type=Fleet.MissionType.TRANSPORT,
        at=at,
    )


def send_stationing_fleet(source_planet, target_planet, transporter_count, cargo: ResourceAmounts, user,
                          speed_profile=DEFAULT_FLEET_SPEED_PROFILE, at=None):
    return _send_fleet_mission(
        source_planet=source_planet,
        target_planet=target_planet,
        ship_quantities={TRANSPORTER_CODE: transporter_count},
        cargo=cargo,
        speed_profile=speed_profile,
        user=user,
        mission_type=Fleet.MissionType.STATION,
        at=at,
    )


@dataclass(frozen=True, slots=True)
class FleetEvent:
    event_time: object
    fleet_id: int
    event_type: str


FLEET_EVENT_ARRIVAL = "arrival"
FLEET_EVENT_RETURN = "return"


FLEET_EVENT_PRIORITY = {
    FLEET_EVENT_ARRIVAL: 10,
    FLEET_EVENT_RETURN: 20,
}


def get_due_fleet_events(owner, *, at):
    events = []

    fleets = list(
        Fleet.objects
        .select_for_update()
        .select_related("target_planet", "source_planet")
        .prefetch_related("ships")
        .filter(Q(owner=owner) | Q(target_planet__owner=owner))
        .exclude(status=Fleet.Status.COMPLETED)
    )

    for fleet in fleets:
        if fleet.status == Fleet.Status.OUTBOUND:
            if fleet.arrival_time and fleet.arrival_time <= at:
                events.append(
                    FleetEvent(
                        event_time=fleet.arrival_time,
                        fleet_id=fleet.pk,
                        event_type=FLEET_EVENT_ARRIVAL,
                    )
                )

            # Ważne: jeśli użytkownik czekał aż flota zdążyła już wrócić,
            # dodajemy też return event w tej samej rundzie.
            if fleet.return_time and fleet.return_time <= at:
                events.append(
                    FleetEvent(
                        event_time=fleet.return_time,
                        fleet_id=fleet.pk,
                        event_type=FLEET_EVENT_RETURN,
                    )
                )

        elif fleet.status == Fleet.Status.RETURNING and fleet.return_time and fleet.return_time <= at:
            events.append(
                FleetEvent(
                    event_time=fleet.return_time,
                    fleet_id=fleet.pk,
                    event_type=FLEET_EVENT_RETURN,
                )
            )

    return sorted(events, key=lambda event: (
        event.event_time,
        FLEET_EVENT_PRIORITY[event.event_type],
        event.fleet_id)
        )


@transaction.atomic
def process_fleets_for_user(user, *, at=None):
    target_time = at or timezone.now()
    processed_events = []

    events = get_due_fleet_events(user, at=target_time)

    for event in events:
        fleet = (
            Fleet.objects
            .select_for_update()
            .select_related(
                "source_planet",
                "target_planet",
            )
            .prefetch_related("ships")
            .get(pk=event.fleet_id)
        )

        if event.event_type == FLEET_EVENT_ARRIVAL:
            if fleet.status != Fleet.Status.OUTBOUND:
                continue

            handle_outbound_fleet_arrival(fleet, at=event.event_time)

            processed_events.append(event)

        elif event.event_type == FLEET_EVENT_RETURN:
            if fleet.status != Fleet.Status.RETURNING:
                continue

            handle_fleet_return(fleet, at=event.event_time)

            processed_events.append(event)

    return processed_events
