from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.sync import advance_planet_state
from apps.game.buildings import calculate_resource_production
from apps.game.domain.exceptions import PlanetStateTimeRegressionError
from apps.game.domain_services.resources import (
    get_storage_capacity_for_level,
)

from .helpers import PlanetTestMixin


class AdvancePlanetStateTests(PlanetTestMixin, TestCase):
    def test_advance_saves_resources_when_building_finishes(self):
        start_time = timezone.now()
        target_time = start_time + timezone.timedelta(hours=1)

        planet = self.create_planet(
            metal=500,
            crystal=200,
            metal_mine_level=2,
            crystal_mine_level=1,
            last_resource_update=start_time,
            building_type="metal_mine",
            building_ends_at=target_time - timezone.timedelta(seconds=1),
        )

        result = advance_planet_state(
            planet,
            at=target_time,
        )

        refreshed_planet = self.reload_planet(planet)

        self.assertTrue(result.building_finished)
        self.assertGreater(refreshed_planet.metal, 500)
        self.assertGreater(refreshed_planet.crystal, 200)
        self.assertEqual(
            refreshed_planet.last_resource_update,
            target_time,
        )
        self.assertEqual(
            refreshed_planet.buildings.metal_mine_level,
            3,
        )

    def test_advance_saves_resources_when_ship_construction_finishes(self):
        start_time = timezone.now()
        target_time = start_time + timezone.timedelta(hours=1)

        planet = self.create_planet(
            metal=10000,
            crystal=10000,
            metal_mine_level=2,
            crystal_mine_level=1,
            shipyard_level=1,
            transporter_count=2,
            last_resource_update=start_time,
        )

        construction = planet.get_ship_construction()
        construction.ship_code = "transporter"
        construction.quantity = 3
        construction.started_at = start_time
        construction.ends_at = target_time - timezone.timedelta(seconds=1)
        construction.save()

        result = advance_planet_state(
            planet,
            at=target_time,
        )

        refreshed_planet = self.reload_planet(planet)

        self.assertTrue(result.ship_construction_finished)
        self.assertGreater(refreshed_planet.metal, 10000)
        self.assertGreater(refreshed_planet.crystal, 10000)
        self.assertEqual(
            refreshed_planet.last_resource_update,
            target_time,
        )
        self.assertEqual(
            self.get_planet_ship_quantity(
                refreshed_planet,
                "transporter",
            ),
            5,
        )

    def test_advance_returns_false_for_unfinished_jobs(self):
        start_time = timezone.now()
        target_time = start_time + timezone.timedelta(minutes=10)

        planet = self.create_planet(
            last_resource_update=start_time,
            building_type="metal_mine",
            building_ends_at=target_time + timezone.timedelta(minutes=5),
        )

        result = advance_planet_state(
            planet,
            at=target_time,
        )

        self.assertFalse(result.building_finished)
        self.assertFalse(result.ship_construction_finished)
        self.assertEqual(result.planet.pk, planet.pk)


class ChronologicalPlanetStateAdvanceTests(PlanetTestMixin, TestCase):
    def test_production_is_split_when_mine_finishes_during_advance(self):
        start_time = timezone.now()
        building_end = start_time + timezone.timedelta(minutes=30)
        target_time = start_time + timezone.timedelta(hours=1)

        planet = self.create_planet(
            metal=500,
            crystal=0,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=10,
            last_resource_update=start_time,
            building_type="metal_mine",
            building_ends_at=building_end,
        )

        level_1_production = calculate_resource_production(1, 120,1.18)
        level_2_production = calculate_resource_production(2, 120, 1.18)

        expected_gain = (
            int(level_1_production * 30 / 60)
            + int(level_2_production * 30 / 60)
        )

        result = advance_planet_state(
            planet,
            at=target_time,
        )

        refreshed_planet = self.reload_planet(planet)

        self.assertTrue(result.building_finished)
        self.assertEqual(
            refreshed_planet.metal,
            500 + expected_gain,
        )
        self.assertEqual(
            refreshed_planet.buildings.metal_mine_level,
            2,
        )
        self.assertEqual(
            refreshed_planet.last_resource_update,
            target_time,
        )

    def test_storage_upgrade_changes_capacity_after_completion_time(self):
        start_time = timezone.now()
        building_end = start_time + timezone.timedelta(minutes=30)
        target_time = start_time + timezone.timedelta(hours=1)

        planet = self.create_planet(
            metal=4990,
            crystal=0,
            metal_mine_level=5,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=0,
            last_resource_update=start_time,
            building_type="metal_storage",
            building_ends_at=building_end,
        )

        production_per_hour = calculate_resource_production(5, 120, 1.18)
        half_hour_gain = int(production_per_hour / 2)

        old_capacity = get_storage_capacity_for_level(0)
        new_capacity = get_storage_capacity_for_level(1)

        first_period_gain = min(
            half_hour_gain,
            old_capacity - 4990,
        )

        amount_after_first_period = 4990 + first_period_gain

        second_period_gain = min(
            half_hour_gain,
            new_capacity - amount_after_first_period,
        )

        expected_metal = (
            amount_after_first_period
            + second_period_gain
        )

        advance_planet_state(
            planet,
            at=target_time,
        )

        refreshed_planet = self.reload_planet(planet)

        self.assertEqual(
            refreshed_planet.buildings.metal_storage_level,
            1,
        )
        self.assertEqual(
            refreshed_planet.metal,
            expected_metal,
        )

    def test_events_with_same_timestamp_are_processed_together(self):
        start_time = timezone.now()
        event_time = start_time + timezone.timedelta(minutes=30)
        target_time = start_time + timezone.timedelta(hours=1)

        planet = self.create_planet(
            metal=5000,
            crystal=5000,
            metal_mine_level=1,
            crystal_mine_level=0,
            shipyard_level=1,
            transporter_count=2,
            last_resource_update=start_time,
            building_type="metal_mine",
            building_ends_at=event_time,
        )

        construction = planet.get_ship_construction()
        construction.ship_code = "transporter"
        construction.quantity = 3
        construction.started_at = start_time
        construction.ends_at = event_time
        construction.save()

        result = advance_planet_state(
            planet,
            at=target_time,
        )

        refreshed_planet = self.reload_planet(planet)

        self.assertTrue(result.building_finished)
        self.assertTrue(result.ship_construction_finished)

        self.assertEqual(
            refreshed_planet.buildings.metal_mine_level,
            2,
        )
        self.assertEqual(
            self.get_planet_ship_quantity(
                refreshed_planet,
                "transporter",
            ),
            5,
        )
        self.assertEqual(
            refreshed_planet.last_resource_update,
            target_time,
        )

    def test_advance_rejects_time_before_last_resource_update(self):
        last_update = timezone.now()
        earlier_time = last_update - timezone.timedelta(minutes=1)

        planet = self.create_planet(
            last_resource_update=last_update,
        )

        with self.assertRaises(PlanetStateTimeRegressionError):
            advance_planet_state(
                planet,
                at=earlier_time,
            )

        refreshed_planet = self.reload_planet(planet)

        self.assertEqual(
            refreshed_planet.last_resource_update,
            last_update,
        )
