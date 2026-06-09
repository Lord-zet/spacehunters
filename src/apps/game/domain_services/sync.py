from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.game.models import (
    Planet,
    PlanetBuildings,
    PlanetShipConstruction,
)

from .buildings import finish_locked_building_if_ready
from .resources import RESOURCE_FIELDS, synchronize_resources
from .shipyard import finish_locked_ship_construction_if_ready


@dataclass(frozen=True, slots=True)
class PlanetStateAdvanceResult:
    planet: Planet
    building_finished: bool
    ship_construction_finished: bool


@transaction.atomic
def advance_planet_state(planet, *, at=None) -> PlanetStateAdvanceResult:
    """
    Doprowadza stan pojedynczej planety do wskazanego momentu.

    W obecnej wersji:
    - nalicza zasoby do `at`,
    - kończy gotową budowę,
    - kończy gotową produkcję statków,
    - zapisuje stan planety w jednej transakcji.

    """
    now = at or timezone.now()

    locked_planet = (
        Planet.objects
        .select_for_update()
        .get(pk=planet.pk)
    )

    buildings, _ = (
        PlanetBuildings.objects
        .select_for_update()
        .get_or_create(planet=locked_planet)
    )

    ship_construction, _ = (
        PlanetShipConstruction.objects
        .select_for_update()
        .get_or_create(planet=locked_planet)
    )

    synchronize_resources(
        locked_planet,
        at=now,
        save=False,
    )

    building_finished = finish_locked_building_if_ready(
        buildings,
        at=now,
    )

    ship_construction_finished = (
        finish_locked_ship_construction_if_ready(
            locked_planet,
            ship_construction,
            at=now,
        )
    )

    locked_planet.save(
        update_fields=[
            *RESOURCE_FIELDS,
            "last_resource_update",
        ]
    )

    return PlanetStateAdvanceResult(
        planet=locked_planet,
        building_finished=building_finished,
        ship_construction_finished=ship_construction_finished,
    )


@transaction.atomic
def synchronize_user_state(user, *, at=None):
    from .fleet import process_fleets_for_user

    process_fleets_for_user(user, at=at)
