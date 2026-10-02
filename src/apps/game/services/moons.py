from django.db import transaction

from apps.game.domain.world import Coordinates
from apps.game.models import Moon, SpaceObject
from apps.game.services.space_objects import create_space_object


def get_moon_at_coordinates(coordinates: Coordinates) -> Moon | None:
    return (
        Moon.objects
        .select_related("space_object__location")
        .filter(
            **Moon.coordinate_fields(coordinates),
            space_object__object_type=SpaceObject.ObjectType.MOON,
        )
        .first()
    )


@transaction.atomic
def create_moon(*, owner=None, coordinates: Coordinates, diameter: int) -> Moon:
    space_object = create_space_object(
        coordinates=coordinates,
        object_type=SpaceObject.ObjectType.MOON,
    )
    return Moon.objects.create(
        space_object=space_object,
        owner=owner,
        diameter=diameter,
    )
