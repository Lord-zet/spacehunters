from django.test import TestCase
from django.utils import timezone

from apps.game.models import Planet
from apps.game.domain_services.resources import (
    synchronize_resources,
    get_production_per_hour,
    get_storage_capacity,
    get_storage_capacity_for_level,
)
from apps.game.buildings import calculate_resource_production

from .helpers import PlanetTestMixin


class SynchronizeResourcesTests(PlanetTestMixin, TestCase):
    def test_synchronize_resources_adds_resources_for_elapsed_time(self):
        user = self.create_user("tester1")
        start_time = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=start_time,
            metal=500,
            crystal=200,
            metal_mine_level=2,
            crystal_mine_level=1,
        )

        production = get_production_per_hour(planet)
        target_time = start_time + timezone.timedelta(hours=2)

        synchronize_resources(planet, at=target_time, save=True)
        planet = self.reload_planet(planet)

        expected_metal_gain = int(production["metal"] * 2)
        expected_crystal_gain = int(production["crystal"] * 2)

        self.assertEqual(planet.metal, 500 + expected_metal_gain)
        self.assertEqual(planet.crystal, 200 + expected_crystal_gain)
        self.assertEqual(planet.last_resource_update, target_time)

    def test_synchronize_resources_does_not_exceed_storage_capacity(self):
        user = self.create_user("tester2")
        start_time = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=start_time,
            name="Mars",
            galaxy=1,
            system=2,
            position=3,
            metal=7400,
            crystal=7300,
            metal_mine_level=10,
            crystal_mine_level=10,
            metal_storage_level=1,
            crystal_storage_level=1,
        )

        metal_capacity = get_storage_capacity(planet, "metal")
        crystal_capacity = get_storage_capacity(planet, "crystal")
        target_time = start_time + timezone.timedelta(hours=24)

        synchronize_resources(planet, at=target_time, save=True)
        planet = self.reload_planet(planet)

        self.assertEqual(planet.metal, metal_capacity)
        self.assertEqual(planet.crystal, crystal_capacity)
        self.assertEqual(planet.last_resource_update, target_time)

    def test_synchronize_resources_does_nothing_when_no_time_has_elapsed(self):
        user = self.create_user("tester3")
        start_time = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=start_time,
            name="Venus",
            galaxy=1,
            system=4,
            position=5,
            metal=1200,
            crystal=800,
            metal_mine_level=3,
            crystal_mine_level=2,
            metal_storage_level=5,
            crystal_storage_level=5,
        )

        synchronize_resources(planet, at=start_time, save=True)
        planet = self.reload_planet(planet)

        self.assertEqual(planet.metal, 1200)
        self.assertEqual(planet.crystal, 800)
        self.assertEqual(planet.last_resource_update, start_time)

    def test_synchronize_resources_does_nothing_when_time_is_earlier_than_last_update(self):
        user = self.create_user("tester4")
        start_time = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=start_time,
            name="Jupiter",
            galaxy=1,
            system=6,
            position=7,
            metal=1500,
            crystal=900,
            metal_mine_level=4,
            crystal_mine_level=3,
            metal_storage_level=5,
            crystal_storage_level=5,
        )

        earlier_time = start_time - timezone.timedelta(minutes=10)

        synchronize_resources(planet, at=earlier_time, save=True)
        planet = self.reload_planet(planet)

        self.assertEqual(planet.metal, 1500)
        self.assertEqual(planet.crystal, 900)
        self.assertEqual(planet.last_resource_update, start_time)

    def test_synchronize_resources_with_save_false_updates_only_in_memory(self):
        user = self.create_user("tester5")
        start_time = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=start_time,
            name="Saturn",
            galaxy=1,
            system=8,
            position=9,
            metal=500,
            crystal=200,
            metal_mine_level=2,
            crystal_mine_level=1,
            metal_storage_level=10,
            crystal_storage_level=10,
        )

        production = get_production_per_hour(planet)
        target_time = start_time + timezone.timedelta(hours=2)

        synchronize_resources(planet, at=target_time, save=False)

        expected_metal_gain = int(production["metal"] * 2)
        expected_crystal_gain = int(production["crystal"] * 2)

        self.assertEqual(planet.metal, 500 + expected_metal_gain)
        self.assertEqual(planet.crystal, 200 + expected_crystal_gain)
        self.assertEqual(planet.last_resource_update, target_time)

        fresh_planet = Planet.objects.get(pk=planet.pk)
        self.assertEqual(fresh_planet.metal, 500)
        self.assertEqual(fresh_planet.crystal, 200)
        self.assertEqual(fresh_planet.last_resource_update, start_time)


class StorageCapacityTests(PlanetTestMixin, TestCase):
    def test_storage_capacity_for_early_levels_uses_pretty_table(self):
        self.assertEqual(get_storage_capacity_for_level(0), 5000)
        self.assertEqual(get_storage_capacity_for_level(1), 10000)
        self.assertEqual(get_storage_capacity_for_level(2), 15000)
        self.assertEqual(get_storage_capacity_for_level(3), 30000)
        self.assertEqual(get_storage_capacity_for_level(8), 240000)

    def test_storage_capacity_for_higher_levels_uses_nice_rounded_values(self):
        capacity = get_storage_capacity_for_level(15)

        self.assertGreater(capacity, 0)
        self.assertIsInstance(capacity, int)

    def test_storage_capacity_is_monotonically_increasing(self):
        capacities = [get_storage_capacity_for_level(level) for level in range(20)]

        self.assertEqual(capacities, sorted(capacities))

    def test_get_storage_capacity_uses_building_level_for_resource_type(self):
        planet = self.create_planet(
            metal_storage_level=3,
            crystal_storage_level=2,
            helion_storage_level=1,
        )

        self.assertEqual(get_storage_capacity(planet, "metal"), get_storage_capacity_for_level(3))
        self.assertEqual(get_storage_capacity(planet, "crystal"), get_storage_capacity_for_level(2))
        self.assertEqual(get_storage_capacity(planet, "helion"), get_storage_capacity_for_level(1))


class ResourceProductionProgressionTests(PlanetTestMixin, TestCase):
    def test_calculate_resource_production_returns_zero_for_level_zero(self):
        self.assertEqual(calculate_resource_production(0, 120, 1.18), 0)

    def test_calculate_resource_production_grows_monotonically(self):
        values = [
            calculate_resource_production(level, 120, 1.18)
            for level in range(1, 21)
        ]

        self.assertEqual(values, sorted(values))

    def test_metal_mine_production_is_much_softer_at_high_levels(self):
        planet = self.create_planet(
            metal_mine_level=20,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )

        production = get_production_per_hour(planet)

        self.assertLess(production["metal"], 5000)

    def test_mine_production_still_scales_reasonably_in_early_game(self):
        planet_lvl_1 = self.create_planet(
            owner=self.create_user("prod_lvl_1"),
            is_homeland=True,
            system=40,
            position=1,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )
        planet_lvl_5 = self.create_planet(
            owner=self.create_user("prod_lvl_5"),
            is_homeland=True,
            system=40,
            position=2,
            metal_mine_level=5,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )

        prod_1 = get_production_per_hour(planet_lvl_1)["metal"]
        prod_5 = get_production_per_hour(planet_lvl_5)["metal"]

        self.assertGreater(prod_5, prod_1)
        self.assertLess(prod_5, 1000)
