from django.utils import timezone

from ..buildings import BUILDINGS
from .energy import (
    apply_energy_efficiency_to_production,
    get_energy_balance,
)


RESOURCE_FIELDS = ("metal", "crystal", "helion")

RESOURCE_PRODUCTION_REMAINDER_FIELDS = (
    "metal_production_remainder_micro",
    "crystal_production_remainder_micro",
    "helion_production_remainder_micro",
)

RESOURCE_STATE_FIELDS = (
    *RESOURCE_FIELDS,
    *RESOURCE_PRODUCTION_REMAINDER_FIELDS,
    "last_resource_update",
)

RESOURCE_PRODUCTION_REMAINDER_FIELD_BY_RESOURCE = {
    "metal": "metal_production_remainder_micro",
    "crystal": "crystal_production_remainder_micro",
    "helion": "helion_production_remainder_micro",
}

RESOURCE_PRECISION_MICRO = 1_000_000
MICROSECONDS_PER_HOUR = 3_600 * 1_000_000


# Manual progression for early storage levels to keep UI values clean and game balance readable.
PRETTY_STORAGE_CAPACITIES = [
    5000,    # lvl 0
    10000,   # lvl 1
    15000,   # lvl 2
    30000,   # lvl 3
    50000,   # lvl 4
    80000,   # lvl 5
    120000,  # lvl 6
    180000,  # lvl 7
    240000,  # lvl 8
    320000,  # lvl 9
    450000,  # lvl 10
]

NICE_MANTISSAS = [1.0, 1.2, 1.5, 2.0, 2.4, 3.0, 4.0, 5.0, 6.0, 7.5, 8.0, 10.0]


def round_up_to_nice_number(value: float) -> int:
    if value <= 0:
        return 0

    magnitude = 10 ** (len(str(int(value))) - 1)
    normalized = value / magnitude

    for mantissa in NICE_MANTISSAS:
        if normalized <= mantissa:
            return int(mantissa * magnitude)

    return int(10 * magnitude)


def get_elapsed_microseconds(start, end) -> int:
    delta = end - start
    return (
        ((delta.days * 24 * 3600) + delta.seconds)
        * 1_000_000
        + delta.microseconds
    )


def apply_fractional_resource_production(
    planet,
    *,
    resource: str,
    per_hour: int,
    elapsed_microseconds: int,
    buildings=None,
) -> None:
    if per_hour <= 0 or elapsed_microseconds <= 0:
        return

    remainder_field = RESOURCE_PRODUCTION_REMAINDER_FIELD_BY_RESOURCE[resource]

    produced_micro = (
        per_hour
        * elapsed_microseconds
        * RESOURCE_PRECISION_MICRO
        // MICROSECONDS_PER_HOUR
    )

    total_micro = getattr(planet, remainder_field, 0) + produced_micro
    whole_units, new_remainder = divmod(total_micro, RESOURCE_PRECISION_MICRO)

    current_amount = getattr(planet, resource, 0)
    capacity = get_storage_capacity(
        planet,
        resource,
        buildings=buildings,
    )
    free_space = max(capacity - current_amount, 0)

    if free_space <= 0:
        # Magazyn jest pełny. Nie kumulujemy ukrytej produkcji.
        setattr(planet, remainder_field, 0)
        return

    actual_gain = min(whole_units, free_space)

    if actual_gain > 0:
        setattr(planet, resource, current_amount + actual_gain)

    if actual_gain < whole_units:
        # Produkcja przekroczyła pojemność magazynu.
        # Nadwyżka, również ułamkowa, przepada.
        new_remainder = 0
    elif current_amount + actual_gain >= capacity:
        # Magazyn został zapełniony dokładnie w tym przedziale.
        # Nie zostawiamy ukrytej ułamkowej produkcji ponad pojemność.
        new_remainder = 0

    setattr(planet, remainder_field, new_remainder)


def get_storage_capacity_for_level(level: int) -> int:
    if level < len(PRETTY_STORAGE_CAPACITIES):
        return PRETTY_STORAGE_CAPACITIES[level]

    extra_levels = level - len(PRETTY_STORAGE_CAPACITIES) + 1
    raw_value = PRETTY_STORAGE_CAPACITIES[-1] * (1.35 ** extra_levels)
    return round_up_to_nice_number(raw_value)


def get_storage_capacity(planet, resource: str, *, buildings=None) -> int:
    if buildings is None:
        buildings = planet.get_buildings()

    storage_levels = {
        "metal": buildings.metal_storage_level,
        "crystal": buildings.crystal_storage_level,
        "helion": buildings.helion_storage_level,
    }
    level = storage_levels.get(resource, 0)
    return get_storage_capacity_for_level(level)


def get_raw_production_per_hour(planet, *, buildings=None) -> dict:
    if buildings is None:
        buildings = planet.get_buildings()

    total = {}

    for config in BUILDINGS.values():
        level = getattr(buildings, config["level_field"])

        production_fn = config.get("production_fn")
        if not production_fn:
            continue

        production = production_fn(level)

        for resource, amount in production.items():
            total[resource] = total.get(resource, 0) + amount

    return total


def get_production_per_hour(planet, *, buildings=None) -> dict:
    if buildings is None:
        buildings = planet.get_buildings()

    raw_production = get_raw_production_per_hour(planet, buildings=buildings)
    energy_balance = get_energy_balance(planet, buildings=buildings)

    return apply_energy_efficiency_to_production(raw_production, energy_balance)


def synchronize_resources(planet, at=None, *, save=False, buildings=None):
    now = at or timezone.now()
    elapsed_microseconds = get_elapsed_microseconds(planet.last_resource_update, now)

    if elapsed_microseconds <= 0:
        return planet

    if buildings is None:
        buildings = planet.get_buildings()

    production = get_production_per_hour(planet, buildings=buildings)

    for resource, per_hour in production.items():
        apply_fractional_resource_production(
            planet,
            resource=resource,
            per_hour=per_hour,
            elapsed_microseconds=elapsed_microseconds,
            buildings=buildings,
        )

    planet.last_resource_update = now

    if save:
        planet.save(update_fields=RESOURCE_STATE_FIELDS)

    return planet
