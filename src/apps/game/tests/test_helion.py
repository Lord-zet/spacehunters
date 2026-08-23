from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.resources import (
    get_production_per_hour,
    get_storage_capacity,
    synchronize_resources,
    get_storage_capacity_for_level,
)
from apps.game.buildings import calculate_resource_production

from .helpers import PlanetTestMixin


class HelionResourceTests(PlanetTestMixin, TestCase):
    def test_helion_synthesizer_adds_helion_to_hourly_production(self):
        planet = self.create_planet(
            helion_synthesizer_level=3,
        )

        production = get_production_per_hour(planet.get_buildings())

        self.assertIn("helion", production)
        self.assertEqual(
            production["helion"],
            calculate_resource_production(3, 40, 1.16),
        )

    def test_helion_storage_capacity_depends_on_helion_storage_level(self):
        planet = self.create_planet(
            helion_storage_level=2,
        )

        capacity = get_storage_capacity(planet.get_buildings(), "helion")

        self.assertEqual(capacity, get_storage_capacity_for_level(2))

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
            get_storage_capacity(planet.get_buildings(), "helion"),
        )
        self.assertEqual(planet.last_resource_update, target_time)
