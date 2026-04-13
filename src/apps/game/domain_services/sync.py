from django.db import transaction

from .resources import synchronize_resources
from ..services import process_fleets_for_user


@transaction.atomic
def synchronize_planet_state(planet, *, save=True):
    synchronize_resources(planet, save=False)

    finished = planet.finish_building_if_ready()

    if save and not finished:
        planet.save()

    return planet, finished


@transaction.atomic
def synchronize_user_state(user):
    process_fleets_for_user(user)
