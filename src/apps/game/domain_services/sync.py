from django.db import transaction

from .resources import synchronize_resources
from .buildings import finish_building_if_ready
from .shipyard import finish_ship_construction_if_ready


@transaction.atomic
def synchronize_planet_state(planet, *, save=True, at=None):
    synchronize_resources(planet, at=at, save=False)
    building_finished = finish_building_if_ready(planet, at=at)
    ship_construction_finished = finish_ship_construction_if_ready(planet, at=at)

    planet._building_finished = building_finished
    planet._ship_construction_finished = ship_construction_finished

    if save and not (building_finished or ship_construction_finished):
        planet.save()

    return planet, building_finished


@transaction.atomic
def synchronize_user_state(user):
    from .fleet import process_fleets_for_user
    process_fleets_for_user(user)
