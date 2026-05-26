from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.game.domain.exceptions import (
    BuildingAlreadyInProgressError,
    NotEnoughResourcesError,
    UnknownBuildingError,
    NoFreePlanetFieldsError,
)
from apps.game.models import Planet, PlanetBuildings
from ..buildings import BUILDINGS
from .resources import synchronize_resources, RESOURCE_FIELDS


def get_building_config(building_name):
    return BUILDINGS.get(building_name)


def get_building_level(planet, config):
    buildings = planet.get_buildings()
    return getattr(buildings, config["level_field"])


def calculate_upgrade_cost(current_level, base_cost):
    next_level = current_level + 1
    return {
        resource: int(base * next_level * 2.5)
        for resource, base in base_cost.items()
    }


def get_upgrade_cost(planet, building_name):
    config = get_building_config(building_name)
    if not config:
        return None

    current_level = get_building_level(planet, config)
    return calculate_upgrade_cost(current_level, config["base_cost"])


def has_enough_resources(planet, cost):
    for resource, amount in cost.items():
        if getattr(planet, resource) < amount:
            return False
    return True


def spend_resources(planet, cost):
    for resource, amount in cost.items():
        setattr(planet, resource, getattr(planet, resource) - amount)


def calculate_upgrade_time(current_level, base_build_time, multiplier=1.3):
    next_level = current_level + 1
    return int(base_build_time * (multiplier ** next_level))


def get_upgrade_time(planet, building_name):
    config = get_building_config(building_name)
    if not config:
        return None

    current_level = get_building_level(planet, config)
    multiplier = config.get("build_time_multiplier", 1.3)
    return calculate_upgrade_time(current_level, config["build_time"], multiplier)


@transaction.atomic
def start_building_upgrade(planet, building_name, *, at=None):
    now = at or timezone.now()

    planet = Planet.objects.select_for_update().get(pk=planet.pk)
    buildings, _ = PlanetBuildings.objects.select_for_update().get_or_create(planet=planet)

    synchronize_resources(planet, at=now, save=False)

    if buildings.is_building_in_progress(at=now):
        raise BuildingAlreadyInProgressError("Na tej planecie trwa już budowa.")

    config = get_building_config(building_name)
    if not config:
        raise UnknownBuildingError("Nieznany budynek.")

    if not buildings.has_free_field(at=now):
        raise NoFreePlanetFieldsError("Brak wolnych pól na planecie.")

    cost = get_upgrade_cost(planet, building_name)
    if cost is None:
        raise UnknownBuildingError("Nieznany budynek.")

    if not has_enough_resources(planet, cost):
        raise NotEnoughResourcesError("Za mało surowców.")

    spend_resources(planet, cost)

    buildings.building_type = building_name
    upgrade_time = get_upgrade_time(planet, building_name)
    buildings.building_ends_at = now + timedelta(seconds=upgrade_time)

    buildings.save(update_fields=["building_type", "building_ends_at"])
    planet.save(update_fields=[*RESOURCE_FIELDS, "last_resource_update"])

    return planet


@transaction.atomic
def finish_building_if_ready(planet, *, at=None):
    now = at or timezone.now()

    planet = Planet.objects.select_for_update().get(pk=planet.pk)
    buildings, _ = PlanetBuildings.objects.select_for_update().get_or_create(planet=planet)

    if not buildings.building_ends_at:
        return False

    if buildings.building_ends_at > now:
        return False

    config = get_building_config(buildings.building_type)
    if not config:
        buildings.building_type = ""
        buildings.building_ends_at = None
        buildings.save(update_fields=["building_type", "building_ends_at"])
        return False

    level_field = config["level_field"]
    current_level = getattr(buildings, level_field)
    setattr(buildings, level_field, current_level + 1)

    buildings.building_type = ""
    buildings.building_ends_at = None
    buildings.save(update_fields=[level_field, "building_type", "building_ends_at"])

    return True