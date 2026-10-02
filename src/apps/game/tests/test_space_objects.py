from django.db import IntegrityError
from django.test import TestCase

from apps.game.domain.world import Coordinates
from apps.game.models import SpaceLocation, SpaceObject


class SpaceLocationTests(TestCase):
    def test_coordinates_property_returns_galaxy_system_position(self):
        location = SpaceLocation.objects.create(
            galaxy=1,
            system=42,
            position=7,
        )

        self.assertEqual(
            location.coordinates,
            Coordinates(galaxy=1, system=42, position=7),
        )

    def test_coordinate_fields_maps_coordinates_to_model_fields(self):
        self.assertEqual(
            SpaceLocation.coordinate_fields(Coordinates(galaxy=1, system=42, position=7)),
            {
                "galaxy": 1,
                "system": 42,
                "position": 7,
            },
        )

    def test_location_coordinates_must_be_unique(self):
        SpaceLocation.objects.create(galaxy=1, system=42, position=7)

        with self.assertRaises(IntegrityError):
            SpaceLocation.objects.create(galaxy=1, system=42, position=7)


class SpaceObjectTests(TestCase):
    def test_different_object_types_can_share_location(self):
        location = SpaceLocation.objects.create(galaxy=1, system=42, position=7)

        planet = SpaceObject.objects.create(
            location=location,
            object_type=SpaceObject.ObjectType.PLANET,
        )
        moon = SpaceObject.objects.create(
            location=location,
            object_type=SpaceObject.ObjectType.MOON,
        )
        debris_field = SpaceObject.objects.create(
            location=location,
            object_type=SpaceObject.ObjectType.DEBRIS_FIELD,
        )

        self.assertEqual(planet.coordinates, Coordinates(galaxy=1, system=42, position=7))
        self.assertEqual(moon.coordinates, Coordinates(galaxy=1, system=42, position=7))
        self.assertEqual(debris_field.coordinates, Coordinates(galaxy=1, system=42, position=7))

    def test_same_object_type_cannot_be_duplicated_at_location(self):
        location = SpaceLocation.objects.create(galaxy=1, system=42, position=7)
        SpaceObject.objects.create(
            location=location,
            object_type=SpaceObject.ObjectType.MOON,
        )

        with self.assertRaises(IntegrityError):
            SpaceObject.objects.create(
                location=location,
                object_type=SpaceObject.ObjectType.MOON,
            )
