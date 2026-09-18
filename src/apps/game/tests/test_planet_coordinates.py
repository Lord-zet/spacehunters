from django.db import IntegrityError
from django.test import TestCase

from apps.game.domain.world import Coordinates
from apps.game.models import Planet

from .helpers import PlanetTestMixin


class PlanetCoordinatesTests(PlanetTestMixin, TestCase):
    def test_planet_coordinates_property_returns_galaxy_system_position(self):
        planet = self.create_planet(
            galaxy=2,
            system=145,
            position=9,
        )

        self.assertEqual(planet.coordinates, Coordinates(galaxy=2, system=145, position=9))

    def test_planet_coordinate_fields_maps_coordinates_to_model_fields(self):
        self.assertEqual(
            Planet.coordinate_fields(Coordinates(galaxy=2, system=145, position=9)),
            {
                "galaxy": 2,
                "system": 145,
                "position": 9,
            },
        )

    def test_set_coordinates_updates_model_coordinate_fields(self):
        planet = self.create_planet()

        planet.set_coordinates(Coordinates(galaxy=3, system=22, position=8))

        self.assertEqual(planet.coordinates, Coordinates(galaxy=3, system=22, position=8))

    def test_planet_coordinates_must_be_unique(self):
        self.create_planet(
            galaxy=1,
            system=20,
            position=7,
        )

        with self.assertRaises(IntegrityError):
            self.create_planet(
                is_homeland=False,
                galaxy=1,
                system=20,
                position=7,
            )
