from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import NoFreePlanetFieldsError
from apps.game.domain_services.buildings import (
    finish_building_if_ready,
    start_building_upgrade,
)
from .helpers import PlanetTestMixin


class PlanetFieldsTests(PlanetTestMixin, TestCase):
    def test_used_fields_are_sum_of_all_building_levels(self):
        planet = self.create_planet(
            planet_fields_total=20,
            metal_mine_level=3,
            crystal_mine_level=2,
            metal_storage_level=1,
            crystal_storage_level=4,
        )

        self.assertEqual(planet.buildings.get_used_fields(), 10)
        self.assertEqual(planet.buildings.get_free_fields(), 10)

    def test_building_in_progress_reserves_one_additional_field(self):
        now = timezone.now()

        planet = self.create_planet(
            planet_fields_total=10,
            metal_mine_level=3,
            crystal_mine_level=2,
            metal_storage_level=1,
            crystal_storage_level=1,
            building_type="metal_mine",
            building_ends_at=now + timezone.timedelta(minutes=5),
        )

        self.assertEqual(
            planet.buildings.get_used_fields(at=now),
            8,  # 3 + 2 + 1 + 1 + 1 reserved
        )
        self.assertEqual(planet.buildings.get_free_fields(at=now), 2)

    def test_start_building_upgrade_raises_when_no_free_fields_are_available(self):
        now = timezone.now()

        planet = self.create_planet(
            last_resource_update=now,
            planet_fields_total=4,
            metal=10000,
            crystal=10000,
            metal_mine_level=2,
            crystal_mine_level=1,
            metal_storage_level=1,
            crystal_storage_level=0,
        )

        with self.assertRaises(NoFreePlanetFieldsError) as ctx:
            start_building_upgrade(planet, "metal_mine", at=now)

        planet = self.reload_planet(planet)

        self.assertEqual(str(ctx.exception), "Brak wolnych pól na planecie.")
        self.assertEqual(planet.buildings.building_type, "")
        self.assertIsNone(planet.buildings.building_ends_at)

    def test_starting_upgrade_on_last_free_field_reserves_it_immediately(self):
        now = timezone.now()

        planet = self.create_planet(
            last_resource_update=now,
            planet_fields_total=4,
            metal=10000,
            crystal=10000,
            metal_mine_level=1,
            crystal_mine_level=1,
            metal_storage_level=1,
            crystal_storage_level=0,
        )

        start_building_upgrade(planet, "metal_mine", at=now)
        planet = self.reload_planet(planet)

        self.assertEqual(planet.buildings.get_used_fields(at=now), 4)
        self.assertEqual(planet.buildings.get_free_fields(at=now), 0)
        self.assertEqual(planet.buildings.building_type, "metal_mine")

    def test_finishing_build_keeps_field_count_consistent_after_reserved_slot_turns_into_level(self):
        now = timezone.now()

        planet = self.create_planet(
            last_resource_update=now,
            planet_fields_total=4,
            metal=10000,
            crystal=10000,
            metal_mine_level=1,
            crystal_mine_level=1,
            metal_storage_level=1,
            crystal_storage_level=0,
        )

        start_building_upgrade(planet, "metal_mine", at=now)
        planet = self.reload_planet(planet)

        used_during_construction = planet.buildings.get_used_fields(at=now)
        finish_time = planet.buildings.building_ends_at + timezone.timedelta(seconds=1)

        finished = finish_building_if_ready(planet, at=finish_time)
        planet = self.reload_planet(planet)

        self.assertTrue(finished)
        self.assertEqual(used_during_construction, 4)
        self.assertEqual(planet.buildings.metal_mine_level, 2)
        self.assertEqual(planet.buildings.get_used_fields(at=finish_time), 4)
        self.assertEqual(planet.buildings.get_free_fields(at=finish_time), 0)
