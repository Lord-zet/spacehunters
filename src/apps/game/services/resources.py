from django.utils import timezone

from apps.game.domain.resources import (
    RESOURCE_STATE_FIELDS,
    apply_fractional_resource_production,
    get_elapsed_microseconds,
    get_production_per_hour,
)


def synchronize_resources(planet, at=None, *, save=False, buildings=None):
    now = at or timezone.now()
    elapsed_microseconds = get_elapsed_microseconds(planet.last_resource_update, now)

    if elapsed_microseconds <= 0:
        return planet

    if buildings is None:
        buildings = planet.get_buildings()

    production = get_production_per_hour(buildings)

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
