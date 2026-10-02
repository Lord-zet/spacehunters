from apps.game.domain.world import Coordinates, DEFAULT_UNIVERSE_RULES
from apps.game.models import SpaceLocation, SpaceObject


def get_or_create_space_location(coordinates: Coordinates) -> SpaceLocation:
    DEFAULT_UNIVERSE_RULES.validate_coordinates(coordinates)
    location, _ = SpaceLocation.objects.get_or_create(
        **SpaceLocation.coordinate_fields(coordinates)
    )
    return location


def create_space_object(*, coordinates: Coordinates, object_type: str) -> SpaceObject:
    location = get_or_create_space_location(coordinates)
    return SpaceObject.objects.create(
        location=location,
        object_type=object_type,
    )


def get_space_object_at_coordinates(*, coordinates: Coordinates, object_type: str) -> SpaceObject | None:
    DEFAULT_UNIVERSE_RULES.validate_coordinates(coordinates)
    return (
        SpaceObject.objects
        .select_related("location")
        .filter(
            **{
                f"location__{field}": value
                for field, value in SpaceLocation.coordinate_fields(coordinates).items()
            },
            object_type=object_type,
        )
        .first()
    )
