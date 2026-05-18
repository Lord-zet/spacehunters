from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.buildings import (
    finish_building_if_ready,
    start_building_upgrade,
)
from apps.game.domain_services.resources import (
    get_production_per_hour,
    get_storage_capacity,
)
from apps.game.models import Planet, PlanetBuildings


class PlanetBuildingsIntegrationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="player1",
            password="testpass123",
        )
        self.planet = Planet.objects.create(
            owner=self.user,
            name="Earth",
            x=1,
            y=1,
            metal=10000,
            crystal=10000,
            transporter_count=5,
            is_homeland=True,
        )
        PlanetBuildings.objects.create(
            planet=self.planet,
            metal_mine_level=1,
            crystal_mine_level=0,
            metal_storage_level=1,
            crystal_storage_level=1,
        )

    def test_production_uses_levels_from_planet_buildings(self):
        production = get_production_per_hour(self.planet)

        self.assertEqual(production["metal"], int(120 * 1 * (1.1 ** 1)))
        self.assertEqual(production.get("crystal"), 0)

    def test_storage_capacity_uses_storage_level_from_planet_buildings(self):
        capacity = get_storage_capacity(self.planet, "metal")
        self.assertEqual(capacity, int(5000 * (1.5 ** 1)))

    def test_start_building_upgrade_saves_progress_on_planet_buildings(self):
        now = timezone.now()

        start_building_upgrade(self.planet, "crystal_mine", at=now)

        buildings = PlanetBuildings.objects.get(planet=self.planet)
        self.assertEqual(buildings.building_type, "crystal_mine")
        self.assertIsNotNone(buildings.building_ends_at)

    def test_finish_building_if_ready_increments_level_on_planet_buildings(self):
        buildings = PlanetBuildings.objects.get(planet=self.planet)
        buildings.building_type = "crystal_mine"
        buildings.building_ends_at = timezone.now() - timedelta(seconds=1)
        buildings.save(update_fields=["building_type", "building_ends_at"])

        finished = finish_building_if_ready(self.planet, at=timezone.now())

        buildings.refresh_from_db()
        self.assertTrue(finished)
        self.assertEqual(buildings.crystal_mine_level, 1)
        self.assertEqual(buildings.building_type, "")
        self.assertIsNone(buildings.building_ends_at)
