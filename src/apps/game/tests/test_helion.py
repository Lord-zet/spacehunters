from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.resources import (
    get_production_per_hour,
    get_storage_capacity,
    synchronize_resources,
)
from .helpers import PlanetTestMixin


class HelionResourceTests(PlanetTestMixin, TestCase):
    def test_helion_synthesizer_adds_helion_to_hourly_production(self):
        planet = self.create_planet(
            helion_synthesizer_level=3,
        )

        production = get_production_per_hour(planet)

        self.assertIn("helion", production)
        self.assertEqual(
            production["helion"],
            int(40 * 3 * (1.1 ** 3)),
        )

    def test_helion_storage_capacity_depends_on_helion_storage_level(self):
        planet = self.create_planet(
            helion_storage_level=2,
        )

        capacity = get_storage_capacity(planet, "helion")

        self.assertEqual(capacity, int(5000 * (1.5 ** 2)))

    def test_synchronize_resources_adds_helion_up_to_storage_capacity(self):
        start_time = timezone.now()
        planet = self.create_planet(
            helion=100,
            helion_synthesizer_level=5,
            helion_storage_level=1,
            last_resource_update=start_time,
        )

        target_time = start_time + timezone.timedelta(hours=10)

        synchronize_resources(planet, at=target_time, save=True)
        planet = self.reload_planet(planet)

        self.assertLessEqual(
            planet.helion,
            get_storage_capacity(planet, "helion"),
        )
        self.assertEqual(planet.last_resource_update, target_time)
