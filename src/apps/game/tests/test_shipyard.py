from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import ShipyardRequiredError
from apps.game.domain_services.shipyard import (
    finish_ship_construction_if_ready,
    get_ship_construction_time_seconds,
    start_ship_construction,
)
from .helpers import PlanetTestMixin


class ShipyardTests(PlanetTestMixin, TestCase):
    def test_start_ship_construction_requires_shipyard(self):
        now = timezone.now()
        planet = self.create_planet(
            metal=10000,
            crystal=10000,
            helion=1000,
            shipyard_level=0,
            last_resource_update=now,
        )

        with self.assertRaises(ShipyardRequiredError):
            start_ship_construction(planet, "transporter", 1, at=now)

    def test_start_ship_construction_spends_resources_and_sets_queue(self):
        now = timezone.now()
        planet = self.create_planet(
            metal=10000,
            crystal=10000,
            helion=1000,
            shipyard_level=1,
            last_resource_update=now,
        )

        start_ship_construction(planet, "transporter", 2, at=now)
        planet = self.reload_planet(planet)
        construction = planet.get_ship_construction()

        self.assertEqual(construction.ship_code, "transporter")
        self.assertEqual(construction.quantity, 2)
        self.assertEqual(planet.metal, 6000)
        self.assertEqual(planet.crystal, 8000)

    def test_finish_ship_construction_adds_ships_to_planet_inventory(self):
        now = timezone.now()
        planet = self.create_planet(
            metal=10000,
            crystal=10000,
            helion=1000,
            shipyard_level=1,
            transporter_count=3,
            last_resource_update=now,
        )

        start_ship_construction(planet, "transporter", 2, at=now)
        finish_time = now + timezone.timedelta(
            seconds=get_ship_construction_time_seconds("transporter", 2) + 1
        )

        finished = finish_ship_construction_if_ready(planet, at=finish_time)
        planet = self.reload_planet(planet)

        self.assertTrue(finished)
        self.assertEqual(self.get_planet_ship_quantity(planet, "transporter"), 5)
        self.assertFalse(planet.get_ship_construction().is_in_progress(at=finish_time))

    def test_ship_construction_time_does_not_depend_on_shipyard_level(self):
        planet_a = self.create_planet(shipyard_level=1)
        planet_b = self.create_planet(
            owner=self.create_user("other_shipyard_user"),
            is_homeland=True,
            system=2,
            position=2,
            shipyard_level=5,
        )

        time_a = get_ship_construction_time_seconds("transporter", 3)
        time_b = get_ship_construction_time_seconds("transporter", 3)

        self.assertEqual(time_a, time_b)
