from django.db import transaction

from .resources import synchronize_resources
from .buildings import finish_building_if_ready


@transaction.atomic
def synchronize_planet_state(planet, *, save=True, at=None):
    synchronize_resources(planet, at=at, save=False)
    finished = finish_building_if_ready(planet, at=at)

    if save and not finished:
        planet.save()

    return planet, finished


@transaction.atomic
def synchronize_user_state(user):
    from .fleet import process_fleets_for_user
    process_fleets_for_user(user)
