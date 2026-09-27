import math

from apps.game.domain.exceptions import FleetError, UnknownShipError
from apps.game.domain.fleet_speed_profiles import (
    DEFAULT_FLEET_SPEED_PROFILE,
    get_fleet_speed_multiplier,
)
from apps.game.domain.ships import SHIPS
from apps.game.domain.travel import calculate_distance


DEFAULT_TRANSPORTER_CODE = "transporter"
HELION_DISTANCE_DIVISOR = 1000
MIN_HELION_COST = 1


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
