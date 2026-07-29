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


def calculate_fleet_base_fuel_burn(ship_quantities: dict[str, int]) -> int:
    total = 0
    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue
        ship_config = SHIPS[ship_code]
        total += ship_config["fuel_burn"] * quantity
    return total


def calculate_helion_cost_for_flight(source_planet, target_planet, ship_quantities: dict[str, int],
                                     fuel_multiplier=1.0) -> int:
    base_burn = calculate_fleet_base_fuel_burn(ship_quantities)
    if base_burn <= 0:
        return 0

    distance = calculate_distance(source_planet, target_planet)
    raw_cost = base_burn * distance * fuel_multiplier / HELION_DISTANCE_DIVISOR

    return max(MIN_HELION_COST, math.ceil(raw_cost))


def calculate_cargo_capacity(ship_quantities: dict[str, int]) -> int:
    total = 0

    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue

        ship_config = SHIPS[ship_code]
        total += ship_config.get("cargo_capacity", 0) * quantity

    return total


def check_and_get_planet_ships(planet, ship_quantities: dict[str, int]) -> list[PlanetShip]:
    """
    Pobiera istniejące statki jednym zapytaniem i weryfikuje ich ilość.
    Zapobiega N+1 zapytaniom występującym przy pętlach walidujących poszczególne typy.
    """
    validate_ship_quantities(ship_quantities)
    active_quantities = {code: q for code, q in ship_quantities.items() if q > 0}

    # Jedno zapytanie do bazy z blokadą zamiast N zapytań (dla każdego typu)
    existing_ships = list(
        PlanetShip.objects
        .select_for_update()
        .filter(planet=planet, ship_code__in=active_quantities.keys())
    )
    ship_map = {ship.ship_code: ship for ship in existing_ships}

    for ship_code, required_quantity in active_quantities.items():
        planet_ship = ship_map.get(ship_code)

        if not planet_ship or planet_ship.quantity < required_quantity:
            if ship_code == TRANSPORTER_CODE:
                raise NotEnoughTransportersError("Nie masz wystarczającej liczby transportowców.")
            raise FleetError("Nie masz wystarczającej liczby statków.")

    return existing_ships


def deduct_planet_ships_bulk(ships_to_update: list[PlanetShip], ship_quantities: dict[str, int]) -> None:
    """
    Odejmuje wartości statków w pamięci i wykonuje 1 zapytanie UPDATE (bulk_update).
    """
    if not ships_to_update:
        return

    for ship in ships_to_update:
        deduction = ship_quantities.get(ship.ship_code, 0)
        if deduction > 0:
            ship.quantity -= deduction

    PlanetShip.objects.bulk_update(ships_to_update, ["quantity"])


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
    if fleet_ships:
        FleetShip.objects.bulk_create(fleet_ships)


def add_fleet_ships_to_planet(fleet, planet) -> None:
    """
    Dodaje statki z floty do planety.

    Przy prefetched fleet.ships wykonuje jedno zapytanie odczytujące PlanetShip oraz maksymalnie
    jeden bulk_update i jeden bulk_create.
    """
    fleet_ships = [fs for fs in fleet.ships.all() if fs.quantity > 0]
    if not fleet_ships:
        return

    ship_codes = [fs.ship_code for fs in fleet_ships]

    existing_ships = list(
        PlanetShip.objects
        .select_for_update()
        .filter(planet=planet, ship_code__in=ship_codes)
    )
    ship_map = {ship.ship_code: ship for ship in existing_ships}

    ships_to_update = []
    ships_to_create = []

    for fs in fleet_ships:
        if fs.ship_code in ship_map:
            planet_ship = ship_map[fs.ship_code]
            planet_ship.quantity += fs.quantity
            ships_to_update.append(planet_ship)
        else:
            ships_to_create.append(PlanetShip(
                planet=planet,
                ship_code=fs.ship_code,
                quantity=fs.quantity
            ))

    if ships_to_update:
        PlanetShip.objects.bulk_update(ships_to_update, ["quantity"])
    if ships_to_create:
        PlanetShip.objects.bulk_create(ships_to_create)


def get_safe_fleet_event_time(event_time, *planets):
    safe_time = event_time

    for planet in planets:
        if (
            planet.last_resource_update
            and planet.last_resource_update > safe_time
        ):
            safe_time = planet.last_resource_update

    return safe_time


def _prepare_planet_for_fleet_event(planet_id, at):
    planet = Planet.objects.select_for_update().get(pk=planet_id)
    safe_event_time = get_safe_fleet_event_time(at, planet)
    advance_result = advance_planet_state(planet, at=safe_event_time)
    return advance_result.planet


def handle_transport_arrival(fleet, *, at) -> None:
    target_planet = _prepare_planet_for_fleet_event(fleet.target_planet_id, at)

    fleet_resource_fields, _ = transfer_resources(
        source=fleet,
        target=target_planet,
    )

    fleet.status = Fleet.Status.RETURNING

    target_planet.save(update_fields=RESOURCE_STATE_FIELDS)

    fleet.save(update_fields=[*fleet_resource_fields, "status"])


def handle_station_arrival(fleet, *, at) -> None:
    target_planet = _prepare_planet_for_fleet_event(fleet.target_planet_id, at)

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

    source_planet = Planet.objects.select_for_update().get(pk=source_planet.pk)
    target_planet = Planet.objects.get(pk=target_planet.pk)

    ensure_source_planet_belongs_to_user(source_planet, user)

    if source_planet.id == target_planet.id:
        raise SamePlanetTransportError("Nie można wysłać floty na tę samą planetę.")

    if mission_type == Fleet.MissionType.STATION and source_planet.owner_id != target_planet.owner_id:
        raise InvalidStationingTargetError("Misja stacjonowania jest możliwa tylko na własną planetę.")

    synchronize_resources(source_planet, at=now, save=False)

    # 1. Walidacja i pobranie rekordów PlanetShip
    existing_ships = check_and_get_planet_ships(source_planet, ship_quantities)

    # 2. Walidacja surowców
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

    # 3. Zapis zmian
    deduct_planet_ships_bulk(existing_ships, ship_quantities)

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
    fleet: Fleet
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
        .prefetch_related("ships")
        .filter(Q(owner=owner) | Q(target_planet__owner=owner))
        .exclude(status=Fleet.Status.COMPLETED)
        .order_by("pk")
    )

    for fleet in fleets:
        if fleet.status == Fleet.Status.OUTBOUND:
            if fleet.arrival_time and fleet.arrival_time <= at:
                events.append(
                    FleetEvent(
                        event_time=fleet.arrival_time,
                        fleet=fleet,  # Przekazujemy pełny model
                        event_type=FLEET_EVENT_ARRIVAL,
                    )
                )

            # Ważne: jeśli użytkownik czekał aż flota zdążyła już wrócić,
            # dodajemy też return event w tej samej rundzie.
            if fleet.return_time and fleet.return_time <= at:
                events.append(
                    FleetEvent(
                        event_time=fleet.return_time,
                        fleet=fleet,
                        event_type=FLEET_EVENT_RETURN,
                    )
                )

        elif fleet.status == Fleet.Status.RETURNING and fleet.return_time and fleet.return_time <= at:
            events.append(
                FleetEvent(
                    event_time=fleet.return_time,
                    fleet=fleet,
                    event_type=FLEET_EVENT_RETURN,
                )
            )

    return sorted(events, key=lambda event: (
        event.event_time,
        FLEET_EVENT_PRIORITY[event.event_type],
        event.fleet.pk)
        )


@transaction.atomic
def process_fleets_for_user(user, *, at=None):
    target_time = at or timezone.now()
    processed_events = []

    events = get_due_fleet_events(user, at=target_time)

    for event in events:
        fleet = event.fleet  # Wyciągamy model z pamięci zamiast ponownie strzelać zapytaniem do bazy

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
