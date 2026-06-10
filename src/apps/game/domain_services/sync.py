from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.game.domain.exceptions import PlanetStateTimeRegressionError
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


def _get_next_due_event_time(
    *,
    buildings: PlanetBuildings,
    ship_construction: PlanetShipConstruction,
    target_time: datetime,
) -> datetime | None:
    candidates = []

    if (
        buildings.building_ends_at is not None
        and buildings.building_ends_at <= target_time
    ):
        candidates.append(buildings.building_ends_at)

    if (
        ship_construction.ends_at is not None
        and ship_construction.ends_at <= target_time
    ):
        candidates.append(ship_construction.ends_at)

    return min(candidates) if candidates else None


@transaction.atomic
def advance_planet_state(
    planet,
    *,
    at=None,
) -> PlanetStateAdvanceResult:
    target_time = at or timezone.now()

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

    if target_time < locked_planet.last_resource_update:
        raise PlanetStateTimeRegressionError(
            "Nie można cofnąć stanu planety do wcześniejszego czasu."
        )

    building_finished = False
    ship_construction_finished = False

    while True:
        scheduled_event_time = _get_next_due_event_time(
            buildings=buildings,
            ship_construction=ship_construction,
            target_time=target_time,
        )

        if scheduled_event_time is None:
            break

        # Zabezpieczenie dla danych utworzonych przed wprowadzeniem
        # chronologicznego processora. Jeżeli zdarzenie ma czas wcześniejszy
        # niż last_resource_update, nie możemy odtworzyć historii.
        # Kończymy je w aktualnym punkcie symulacji.
        event_time = max(
            scheduled_event_time,
            locked_planet.last_resource_update,
        )

        synchronize_resources(
            locked_planet,
            at=event_time,
            save=False,
            buildings=buildings,
        )

        if (
            buildings.building_ends_at is not None
            and buildings.building_ends_at <= event_time
        ):
            finished = finish_locked_building_if_ready(
                buildings,
                at=event_time,
            )
            building_finished = building_finished or finished

        if (
            ship_construction.ends_at is not None
            and ship_construction.ends_at <= event_time
        ):
            finished = finish_locked_ship_construction_if_ready(
                locked_planet,
                ship_construction,
                at=event_time,
            )
            ship_construction_finished = (
                ship_construction_finished or finished
            )

    synchronize_resources(
        locked_planet,
        at=target_time,
        save=False,
        buildings=buildings,
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
