import math
from dataclasses import dataclass

from apps.game.domain.exceptions import (
    FleetError,
    InvalidCoordinatesError,
    InvalidStationingTargetError,
    UnknownShipError,
    UnsupportedFleetMissionError,
)
from apps.game.domain.fleet_speed_profiles import (
    DEFAULT_FLEET_SPEED_PROFILE,
    get_fleet_speed_multiplier,
)
from apps.game.domain.ships import ESPIONAGE_PROBE_CODE, SHIPS
from apps.game.domain.travel import calculate_distance
from apps.game.domain.world import Coordinates, DEFAULT_UNIVERSE_RULES


DEFAULT_TRANSPORTER_CODE = "transporter"
HELION_DISTANCE_DIVISOR = 1000
MIN_HELION_COST = 1

MISSION_TARGET_EXISTING_PLANET = "existing_planet"
MISSION_TARGET_OWN_PLANET = "own_planet"
MISSION_TARGET_EMPTY_COORDINATES = "empty_coordinates"


@dataclass(frozen=True, slots=True)
class FleetTarget:
    coordinates: Coordinates
    planet: object | None = None


@dataclass(frozen=True, slots=True)
class FleetEvent:
    event_time: object
    fleet: object
    event_type: str


FLEET_EVENT_ARRIVAL = "arrival"
FLEET_EVENT_RETURN = "return"

FLEET_EVENT_PRIORITY = {
    FLEET_EVENT_ARRIVAL: 10,
    FLEET_EVENT_RETURN: 20,
}


def calculate_fleet_base_fuel_burn(ship_quantities: dict[str, int]) -> int:
    total = 0
    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue
        ship_config = SHIPS[ship_code]
        total += ship_config["fuel_burn"] * quantity
    return total


def calculate_fleet_base_speed(ship_quantities: dict[str, int]) -> float:
    active_ship_speeds = [
        float(SHIPS[ship_code]["base_speed"])
        for ship_code, quantity in ship_quantities.items()
        if quantity > 0
    ]

    if not active_ship_speeds:
        return 1.0
    return min(active_ship_speeds)


def calculate_effective_fleet_speed_multiplier(
    ship_quantities: dict[str, int],
    speed_profile=DEFAULT_FLEET_SPEED_PROFILE,
) -> float:
    return (
        calculate_fleet_base_speed(ship_quantities)
        * get_fleet_speed_multiplier(speed_profile)
    )


def calculate_helion_cost_for_flight(source, target, ship_quantities: dict[str, int],
                                     fuel_multiplier=1.0) -> int:
    base_burn = calculate_fleet_base_fuel_burn(ship_quantities)
    if base_burn <= 0:
        return 0

    distance = calculate_distance(source.coordinates, target.coordinates)
    raw_cost = base_burn * distance * fuel_multiplier / HELION_DISTANCE_DIVISOR

    return max(MIN_HELION_COST, math.ceil(raw_cost))


def get_fleet_flight_duration(fleet):
    return fleet.arrival_time - fleet.departure_time


def get_safe_fleet_event_time(event_time, *planets):
    safe_time = event_time

    for planet in planets:
        if (
            planet.last_resource_update
            and planet.last_resource_update > safe_time
        ):
            safe_time = planet.last_resource_update

    return safe_time


def sort_fleet_events(events):
    return sorted(events, key=lambda event: (
        event.event_time,
        FLEET_EVENT_PRIORITY[event.event_type],
        event.fleet.pk)
    )


def get_due_fleet_events_for_fleets(fleets, *, at, outbound_status, returning_status) -> list[FleetEvent]:
    events = []

    for fleet in fleets:
        if fleet.status == outbound_status:
            if fleet.arrival_time and fleet.arrival_time <= at:
                events.append(
                    FleetEvent(
                        event_time=fleet.arrival_time,
                        fleet=fleet,
                        event_type=FLEET_EVENT_ARRIVAL,
                    )
                )

            if fleet.return_time and fleet.return_time <= at:
                events.append(
                    FleetEvent(
                        event_time=fleet.return_time,
                        fleet=fleet,
                        event_type=FLEET_EVENT_RETURN,
                    )
                )

        elif fleet.status == returning_status and fleet.return_time and fleet.return_time <= at:
            events.append(
                FleetEvent(
                    event_time=fleet.return_time,
                    fleet=fleet,
                    event_type=FLEET_EVENT_RETURN,
                )
            )

    return sort_fleet_events(events)


def calculate_cargo_capacity(ship_quantities: dict[str, int]) -> int:
    """
    Oblicza łączną ładowność dla dowolnej mieszanki statków we flocie. Dowolny statek w konfiguracji
    SHIPS posiadający parametr 'cargo_capacity' będzie brał udział w ładowności floty.
    """
    total = 0

    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue

        ship_config = SHIPS.get(ship_code, {})
        total += ship_config.get("cargo_capacity", 0) * quantity

    return total


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


def normalize_ship_quantities(ship_quantities: dict[str, int] | int) -> dict[str, int]:
    if isinstance(ship_quantities, int):
        return {DEFAULT_TRANSPORTER_CODE: ship_quantities}
    return ship_quantities


def validate_target_coordinates(coordinates: Coordinates) -> Coordinates:
    if not isinstance(coordinates, Coordinates):
        raise FleetError("Koordynaty celu muszą być obiektem Coordinates.")

    try:
        DEFAULT_UNIVERSE_RULES.validate_coordinates(coordinates)
    except InvalidCoordinatesError as exc:
        raise FleetError(str(exc)) from exc

    return coordinates


def validate_mission_target_requirement(requirement: str, target_planet, user) -> None:
    if requirement == MISSION_TARGET_EXISTING_PLANET:
        if target_planet is None:
            raise FleetError("Ten typ misji wymaga istniejącej planety docelowej.")

    elif requirement == MISSION_TARGET_OWN_PLANET:
        if target_planet is None:
            raise InvalidStationingTargetError(
                "Misja stacjonowania jest możliwa tylko na własną planetę."
            )
        if target_planet.owner_id != user.id:
            raise InvalidStationingTargetError(
                "Misja stacjonowania jest możliwa tylko na własną planetę."
            )

    elif requirement == MISSION_TARGET_EMPTY_COORDINATES:
        if target_planet is not None:
            raise FleetError("Ten typ misji wymaga pustych koordynatów celu.")

    else:
        raise UnsupportedFleetMissionError("Nieobsługiwane wymaganie celu misji floty.")


def validate_mission_fleet_composition(ship_quantities: dict[str, int], mission_type: str):
    for ship_code, quantity in ship_quantities.items():
        if quantity <= 0:
            continue

        allowed_missions = SHIPS[ship_code].get("allowed_missions", ())
        if mission_type not in allowed_missions:
            ship_label = SHIPS[ship_code].get("label", ship_code)
            raise FleetError(f"Statek {ship_label} nie może wykonać tej misji.")


def validate_espionage_fleet_composition(ship_quantities: dict[str, int], mission_type: str):
    validate_mission_fleet_composition(ship_quantities, mission_type)

    active_ship_codes = [
        ship_code
        for ship_code, quantity in ship_quantities.items()
        if quantity > 0
    ]
    if active_ship_codes != [ESPIONAGE_PROBE_CODE]:
        raise FleetError("Misja szpiegowska wymaga floty zlożonej wyłącznie z sond szpiegowskich.")
