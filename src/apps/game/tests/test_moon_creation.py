from django.db import IntegrityError
from django.test import TestCase

from apps.game.domain.exceptions import InvalidCoordinatesError
from apps.game.domain.world import Coordinates, DEFAULT_UNIVERSE_RULES
from apps.game.models import SpaceObject
from apps.game.services.moons import create_moon, get_moon_at_coordinates

from .helpers import PlanetTestMixin


class MoonCreationTests(PlanetTestMixin, TestCase):
    def test_create_moon_creates_moon_space_object(self):
        user = self.create_user("moon_create_space_object")

        moon = create_moon(
            owner=user,
            coordinates=Coordinates(galaxy=1, system=42, position=7),
            diameter=8_944,
        )

        self.assertEqual(moon.owner, user)
        self.assertEqual(moon.diameter, 8_944)
        self.assertEqual(moon.space_object.object_type, SpaceObject.ObjectType.MOON)
        self.assertEqual(
            moon.coordinates,
            Coordinates(galaxy=1, system=42, position=7),
        )

    def test_create_moon_can_share_location_with_planet(self):
        user = self.create_user("moon_create_shared_location")
        coordinates = Coordinates(galaxy=1, system=42, position=7)
        planet = self.create_planet(owner=user, coordinates=coordinates)

        moon = create_moon(
            owner=user,
            coordinates=coordinates,
            diameter=8_944,
        )

        self.assertEqual(moon.coordinates, planet.coordinates)
        self.assertEqual(
            moon.space_object.location_id,
            planet.space_object.location_id,
        )

    def test_get_moon_at_coordinates_returns_matching_moon(self):
        user = self.create_user("moon_get_at_coordinates")
        moon = create_moon(
            owner=user,
            coordinates=Coordinates(galaxy=2, system=20, position=7),
            diameter=8_944,
        )

        found_moon = get_moon_at_coordinates(Coordinates(galaxy=2, system=20, position=7))

        self.assertEqual(found_moon, moon)

    def test_get_moon_at_coordinates_returns_none_for_empty_position(self):
        self.assertIsNone(
            get_moon_at_coordinates(Coordinates(galaxy=2, system=20, position=7))
        )

    def test_create_moon_rejects_coordinates_outside_universe(self):
        user = self.create_user("moon_create_outside_universe")

        with self.assertRaises(InvalidCoordinatesError):
            create_moon(
                owner=user,
                coordinates=Coordinates(
                    galaxy=DEFAULT_UNIVERSE_RULES.galaxy_count + 1,
                    system=1,
                    position=1,
                ),
                diameter=8_944,
            )

    def test_create_moon_rejects_duplicate_moon_at_location(self):
        user = self.create_user("moon_create_duplicate")
        coordinates = Coordinates(galaxy=1, system=42, position=7)
        create_moon(
            owner=user,
            coordinates=coordinates,
            diameter=8_944,
        )

        with self.assertRaises(IntegrityError):
            create_moon(
                owner=user,
                coordinates=coordinates,
                diameter=6_100,
            )
