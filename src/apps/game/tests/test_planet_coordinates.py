from django.db import IntegrityError
from django.test import TestCase

from .helpers import PlanetTestMixin


class PlanetCoordinatesTests(PlanetTestMixin, TestCase):
    def test_planet_coordinates_property_returns_galaxy_system_position(self):
        planet = self.create_planet(
            galaxy=2,
            system=145,
            position=9,
        )

        self.assertEqual(planet.coordinates, "2:145:9")

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
