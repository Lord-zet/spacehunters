from apps.game.domain.world import Coordinates, DEFAULT_UNIVERSE_RULES
from apps.game.models import SpaceLocation, SpaceObject


def normalize_space_object_type(object_type: str | None) -> str:
    normalized_type = object_type or SpaceObject.ObjectType.PLANET
    valid_types = {choice for choice, _label in SpaceObject.ObjectType.choices}

    if normalized_type not in valid_types:
        raise ValueError("Nieznany typ obiektu kosmicznego.")

    return normalized_type


def get_or_create_space_location(coordinates: Coordinates) -> SpaceLocation:
    DEFAULT_UNIVERSE_RULES.validate_coordinates(coordinates)
    location, _ = SpaceLocation.objects.get_or_create(
        **SpaceLocation.coordinate_fields(coordinates)
    )
    return location


def create_space_object(*, coordinates: Coordinates, object_type: str) -> SpaceObject:
    object_type = normalize_space_object_type(object_type)
    location = get_or_create_space_location(coordinates)
    return SpaceObject.objects.create(
        location=location,
        object_type=object_type,
    )


def get_space_object_at_coordinates(*, coordinates: Coordinates, object_type: str) -> SpaceObject | None:
    object_type = normalize_space_object_type(object_type)
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
