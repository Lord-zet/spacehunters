from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.buildings import (
    finish_building_if_ready,
    start_building_upgrade,
    get_upgrade_cost,
    get_upgrade_time
)
from apps.game.domain.exceptions import (
    BuildingAlreadyInProgressError,
    NotEnoughResourcesError,
    UnknownBuildingError,
)
from .helpers import PlanetTestMixin


class StartBuildingUpgradeTests(PlanetTestMixin, TestCase):
    def test_start_building_upgrade_starts_construction_and_spends_resources(self):
        user = self.create_user("builder1")
        start_time = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=start_time,
            name="Earth",
            metal=10000,
            crystal=10000,
            metal_mine_level=1,
            crystal_mine_level=0,
        )

        building_name = "metal_mine"
        cost = get_upgrade_cost(planet, building_name)

        start_building_upgrade(
            planet,
            building_name,
            at=start_time,
        )

        planet = self.reload_planet(planet)

        self.assertEqual(planet.buildings.building_type, building_name)
        self.assertIsNotNone(planet.buildings.building_ends_at)
        self.assertGreater(planet.buildings.building_ends_at, start_time)
        self.assertEqual(planet.metal, 10000 - cost["metal"])

    def test_start_building_upgrade_raises_when_construction_is_already_in_progress(self):
        user = self.create_user("builder2")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            name="Mars",
            metal=10000,
            crystal=10000,
            building_type="metal_mine",
            building_ends_at=now + timezone.timedelta(minutes=10),
        )

        old_metal = planet.metal
        old_crystal = planet.crystal
        old_building_type = planet.buildings.building_type
        old_building_ends_at = planet.buildings.building_ends_at

        with self.assertRaises(BuildingAlreadyInProgressError) as ctx:
            start_building_upgrade(
                planet,
                "crystal_mine",
                at=now,
            )

        planet = self.reload_planet(planet)

        self.assertEqual(str(ctx.exception), "Na tej planecie trwa już budowa.")
        self.assertEqual(planet.metal, old_metal)
        self.assertEqual(planet.crystal, old_crystal)
        self.assertEqual(planet.buildings.building_type, old_building_type)
        self.assertEqual(planet.buildings.building_ends_at, old_building_ends_at)

    def test_start_building_upgrade_raises_when_not_enough_resources(self):
        user = self.create_user("builder3")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            name="Venus",
            metal=0,
            crystal=0,
            metal_mine_level=1,
            crystal_mine_level=0,
        )

        with self.assertRaises(NotEnoughResourcesError) as ctx:
            start_building_upgrade(
                planet,
                "metal_mine",
                at=now,
            )

        planet = self.reload_planet(planet)

        self.assertEqual(str(ctx.exception), "Za mało surowców.")
        self.assertEqual(planet.buildings.building_type, "")
        self.assertIsNone(planet.buildings.building_ends_at)
        self.assertEqual(planet.metal, 0)
        self.assertEqual(planet.crystal, 0)

    def test_start_building_upgrade_raises_for_unknown_building(self):
        user = self.create_user("builder4")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            name="Jupiter",
            metal=10000,
            crystal=10000,
        )

        with self.assertRaises(UnknownBuildingError) as ctx:
            start_building_upgrade(
                planet,
                "unknown_building",
                at=now,
            )

        planet = self.reload_planet(planet)

        self.assertEqual(str(ctx.exception), "Nieznany budynek.")
        self.assertEqual(planet.buildings.building_type, "")
        self.assertIsNone(planet.buildings.building_ends_at)


class FinishBuildingIfReadyTests(PlanetTestMixin, TestCase):
    def test_finish_building_if_ready_increases_level_and_clears_building_state(self):
        user = self.create_user("finisher1")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            metal_mine_level=3,
            building_type="metal_mine",
            building_ends_at=now - timezone.timedelta(seconds=1),
        )

        finished = finish_building_if_ready(planet, at=now)
        planet = self.reload_planet(planet)

        self.assertTrue(finished)
        self.assertEqual(planet.buildings.metal_mine_level, 4)
        self.assertEqual(planet.buildings.building_type, "")
        self.assertIsNone(planet.buildings.building_ends_at)

    def test_finish_building_if_ready_returns_false_when_no_building_end_time(self):
        user = self.create_user("finisher2")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            metal_mine_level=3,
            building_type="",
            building_ends_at=None,
        )

        finished = finish_building_if_ready(planet, at=now)
        planet = self.reload_planet(planet)

        self.assertFalse(finished)
        self.assertEqual(planet.buildings.metal_mine_level, 3)
        self.assertEqual(planet.buildings.building_type, "")
        self.assertIsNone(planet.buildings.building_ends_at)

    def test_finish_building_if_ready_returns_false_when_building_is_still_in_progress(self):
        user = self.create_user("finisher3")
        now = timezone.now()

        future_end = now + timezone.timedelta(minutes=5)

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            metal_mine_level=3,
            building_type="metal_mine",
            building_ends_at=future_end,
        )

        finished = finish_building_if_ready(planet, at=now)
        planet = self.reload_planet(planet)

        self.assertFalse(finished)
        self.assertEqual(planet.buildings.metal_mine_level, 3)
        self.assertEqual(planet.buildings.building_type, "metal_mine")
        self.assertEqual(planet.buildings.building_ends_at, future_end)

    def test_finish_building_if_ready_clears_invalid_building_type(self):
        user = self.create_user("finisher4")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            metal_mine_level=3,
            building_type="unknown_building",
            building_ends_at=now - timezone.timedelta(seconds=1),
        )

        finished = finish_building_if_ready(planet, at=now)
        planet = self.reload_planet(planet)

        self.assertFalse(finished)
        self.assertEqual(planet.buildings.metal_mine_level, 3)
        self.assertEqual(planet.buildings.building_type, "")
        self.assertIsNone(planet.buildings.building_ends_at)

    def test_upgrade_cost_for_level_zero_building_is_not_zero(self):
        planet = self.create_planet(
            metal=10000,
            crystal=10000,
            helion_synthesizer_level=0,
        )

        cost = get_upgrade_cost(planet, "helion_synthesizer")

        self.assertGreater(cost["metal"], 0)
        self.assertGreater(cost["crystal"], 0)

    def test_upgrade_time_for_level_zero_building_is_greater_than_base_zero_case(self):
        planet = self.create_planet(
            helion_synthesizer_level=0,
        )

        upgrade_time = get_upgrade_time(planet, "helion_synthesizer")

        self.assertGreater(upgrade_time, 0)
