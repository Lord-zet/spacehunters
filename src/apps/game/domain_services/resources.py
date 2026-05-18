from django.utils import timezone

from ..buildings import BUILDINGS


def get_storage_capacity(planet, resource: str) -> int:
    buildings = planet.get_buildings()

    storage_levels = {
        "metal": buildings.metal_storage_level,
        "crystal": buildings.crystal_storage_level,
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
        planet.save(update_fields=["metal", "crystal", "last_resource_update"])

    return planet
