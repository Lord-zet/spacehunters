from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.game.domain.exceptions import (
    BuildingAlreadyInProgressError,
    NotEnoughResourcesError,
    UnknownBuildingError,
    NoFreePlanetFieldsError,
    NoBuildingInProgressError,
)
from apps.game.models import Planet, PlanetBuildings
from apps.game.domain.buildings import (
    BuildingCancellationResult,
    calculate_building_cancel_refund,
    get_build_cost_for_level,
    get_build_time_for_level,
    get_building_config,
)
from apps.game.domain.resources import RESOURCE_FIELDS, RESOURCE_STATE_FIELDS
from .resources import synchronize_resources


def has_enough_resources(planet, cost):
    for resource, amount in cost.items():
        if getattr(planet, resource) < amount:
            return False
    return True


def spend_resources(planet, cost):
    for resource, amount in cost.items():
        setattr(planet, resource, getattr(planet, resource) - amount)


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

    current_level = buildings.get_level(config["level_field"])
    target_level = current_level + 1

    cost = get_build_cost_for_level(config, target_level)
    if cost is None:
        raise UnknownBuildingError("Nieznany budynek.")

    if not has_enough_resources(planet, cost):
        raise NotEnoughResourcesError("Za mało surowców.")

    spend_resources(planet, cost)

    buildings.building_type = building_name
    buildings.building_cost_paid = dict(cost)

    upgrade_time = get_build_time_for_level(config, target_level)
    buildings.building_ends_at = now + timedelta(seconds=upgrade_time)

    buildings.save(update_fields=["building_type", "building_ends_at", "building_cost_paid"])
    planet.save(update_fields=RESOURCE_STATE_FIELDS)

    return planet


def finish_locked_building_if_ready(buildings, *, at=None):
    """
    Kończy budowę na przekazanym, wcześniej zablokowanym rekordzie
    PlanetBuildings.

    Funkcja nie pobiera ponownie Planet ani PlanetBuildings.
    """
    now = at or timezone.now()

    if not buildings.building_ends_at:
        return False

    if buildings.building_ends_at > now:
        return False

    config = get_building_config(buildings.building_type)

    if not config:
        buildings.clear_building_progress()
        buildings.save(
            update_fields=[
                "building_type",
                "building_ends_at",
                "building_cost_paid",
            ]
        )
        return False

    level_field = config["level_field"]
    current_level = buildings.get_level(level_field)
    setattr(buildings, level_field, current_level + 1)

    buildings.building_type = ""
    buildings.building_ends_at = None
    buildings.save(
        update_fields=[
            level_field,
            "building_type",
            "building_ends_at",
            "building_cost_paid",
        ]
    )

    return True


@transaction.atomic
def finish_building_if_ready(planet, *, at=None):
    locked_planet = Planet.objects.select_for_update().get(pk=planet.pk)

    buildings, _ = (
        PlanetBuildings.objects
        .select_for_update()
        .get_or_create(planet=locked_planet)
    )

    return finish_locked_building_if_ready(
        buildings,
        at=at,
    )


def refund_resources(planet, refund):
    for resource, amount in refund.items():
        if resource not in RESOURCE_FIELDS:
            continue

        setattr(planet, resource, getattr(planet, resource) + amount)


@transaction.atomic
def cancel_building_upgrade(planet, *, at=None) -> BuildingCancellationResult:
    now = at or timezone.now()

    locked_planet = Planet.objects.select_for_update().get(pk=planet.pk)
    buildings = PlanetBuildings.objects.select_for_update().get(planet=locked_planet)

    synchronize_resources(locked_planet, at=now, save=False, buildings=buildings)

    if not buildings.is_building_in_progress(at=now):
        raise NoBuildingInProgressError("Brak aktywnej budowy do anulowania.")

    if not buildings.building_cost_paid:
        raise NoBuildingInProgressError("Brak zapisanego kosztu aktywnej budowy.")

    building_type = buildings.building_type

    paid_cost = {
        resource: int(amount)
        for resource, amount in buildings.building_cost_paid.items()
    }

    refund = calculate_building_cancel_refund(paid_cost)
    refund_resources(locked_planet, refund)

    buildings.clear_building_progress()

    buildings.save(
        update_fields=[
            "building_type",
            "building_ends_at",
            "building_cost_paid",
        ]
    )
    locked_planet.save(update_fields=RESOURCE_STATE_FIELDS)

    return BuildingCancellationResult(
        building_type=building_type,
        paid_cost=paid_cost,
        refund=refund,
    )
