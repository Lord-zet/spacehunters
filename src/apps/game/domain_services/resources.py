from django.utils import timezone

from ..buildings import BUILDINGS


RESOURCE_FIELDS = ("metal", "crystal", "helion")

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


def get_storage_capacity_for_level(level: int) -> int:
    if level < len(PRETTY_STORAGE_CAPACITIES):
        return PRETTY_STORAGE_CAPACITIES[level]

    extra_levels = level - len(PRETTY_STORAGE_CAPACITIES) + 1
    raw_value = PRETTY_STORAGE_CAPACITIES[-1] * (1.35 ** extra_levels)
    return round_up_to_nice_number(raw_value)


def get_storage_capacity(planet, resource: str) -> int:
    buildings = planet.get_buildings()

    storage_levels = {
        "metal": buildings.metal_storage_level,
        "crystal": buildings.crystal_storage_level,
        "helion": buildings.helion_storage_level,
    }
    level = storage_levels.get(resource, 0)

    base_capacity = 5000
    return int(base_capacity * (1.5 ** level))


def get_production_per_hour(planet) -> dict:
    buildings = planet.get_buildings()
    total = {}

    for _, config in BUILDINGS.items():
        level = getattr(buildings, config["level_field"])

        production_fn = config.get("production_fn")
        if not production_fn:
            continue

        production = production_fn(level)

        for resource, amount in production.items():
            total[resource] = total.get(resource, 0) + amount

    return total


def synchronize_resources(planet, at=None, *, save=False):
    now = at or timezone.now()
    elapsed_seconds = (now - planet.last_resource_update).total_seconds()

    if elapsed_seconds <= 0:
        return planet

    production = get_production_per_hour(planet)

    for resource, per_hour in production.items():
        gain = int(per_hour * elapsed_seconds / 3600)
        if gain <= 0:
            continue

        current_amount = getattr(planet, resource, 0)
        capacity = get_storage_capacity(planet, resource)
        free_space = max(capacity - current_amount, 0)

        actual_gain = min(gain, free_space)
        setattr(planet, resource, current_amount + actual_gain)

    planet.last_resource_update = now

    if save:
        planet.save(update_fields=[*RESOURCE_FIELDS, "last_resource_update"])

    return planet
