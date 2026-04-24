from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.game.domain.exceptions import (
    BuildingAlreadyInProgressError,
    NotEnoughResourcesError,
    UnknownBuildingError,
)
from ..buildings import BUILDINGS
from .resources import synchronize_resources


def get_building_config(building_name):
    return BUILDINGS.get(building_name)


def get_building_level(planet, config):
    return getattr(planet, config["level_field"])


def calculate_upgrade_cost(current_level, base_cost):
    return {
        resource: int(base * current_level * 2.5)
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
    return int(base_build_time * (multiplier ** current_level))

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

    synchronize_resources(planet, at=now, save=False)

    if planet.is_building_in_progress():
        raise BuildingAlreadyInProgressError("Na tej planecie trwa już budowa.")

    config = get_building_config(building_name)
    if not config:
        raise UnknownBuildingError("Nieznany budynek.")

    cost = get_upgrade_cost(planet, building_name)
    if cost is None:
        raise UnknownBuildingError("Nieznany budynek.")

    if not has_enough_resources(planet, cost):
        raise NotEnoughResourcesError("Za mało surowców.")

    spend_resources(planet, cost)

    planet.building_type = building_name
    upgrade_time = get_upgrade_time(planet, building_name)
    planet.building_ends_at = now + timedelta(seconds=upgrade_time)
    planet.save()

    return planet


@transaction.atomic
def finish_building_if_ready(planet, *, at=None):
    now = at or timezone.now()

    if not planet.building_ends_at:
        return False

    if planet.building_ends_at > now:
        return False

    config = get_building_config(planet.building_type)
    if not config:
        planet.building_type = ""
        planet.building_ends_at = None
        planet.save(update_fields=["building_type", "building_ends_at"])
        return False

    level_field = config["level_field"]
    current_level = getattr(planet, level_field)
    setattr(planet, level_field, current_level + 1)

    planet.building_type = ""
    planet.building_ends_at = None
    planet.save(update_fields=[level_field, "building_type", "building_ends_at"])

    return True
