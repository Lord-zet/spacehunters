from django.test import TestCase

from apps.game.domain_services.planets import create_planet
from .helpers import PlanetTestMixin


class PlanetCreationTests(PlanetTestMixin, TestCase):
    def test_create_planet_creates_required_state_records(self):
        user = self.create_user("planet_create_1")

        planet = create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            is_homeland=True,
            ships={
                "transporter": 2,
            },
        )

        self.assertIsNotNone(planet.get_buildings())
        self.assertIsNotNone(planet.get_ship_construction())
        self.assertEqual(planet.get_ship_quantity("transporter"),2)

    def test_missing_planet_ship_record_means_zero_quantity(self):
        user = self.create_user("planet_create_2")

        planet = create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            is_homeland=True,
        )

        self.assertEqual(planet.get_ship_quantity("transporter"), 0)
        self.assertEqual(planet.transporter_count,0)
