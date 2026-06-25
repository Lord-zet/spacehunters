from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import (
    NoBuildingInProgressError,
)
from apps.game.domain_services.buildings import (
    BUILDING_CANCEL_REFUND_PERCENT,
    calculate_building_cancel_refund,
    cancel_building_upgrade,
    get_upgrade_cost,
    start_building_upgrade,
)

from .helpers import PlanetTestMixin


class BuildingCancellationTests(PlanetTestMixin, TestCase):
    def test_cancel_building_refunds_half_cost_and_clears_progress(self):
        user = self.create_user("cancel_building_1")
        now = timezone.now()

        initial_metal = 10_000
        initial_crystal = 10_000

        planet = self.create_planet(
            owner=user,
            metal=initial_metal,
            crystal=initial_crystal,
            metal_mine_level=1,
            last_resource_update=now,
        )

        cost = get_upgrade_cost(planet, "metal_mine")
        start_building_upgrade(planet, "metal_mine", at=now)
        result = cancel_building_upgrade(planet, at=now)
        planet = self.reload_planet(planet)
        expected_refund = calculate_building_cancel_refund(cost)

        self.assertEqual(result.building_type, "metal_mine")
        self.assertEqual(result.paid_cost, cost)
        self.assertEqual(result.refund, expected_refund)
        self.assertEqual(
            planet.metal, initial_metal - cost.get("metal", 0) + expected_refund.get("metal", 0)
        )
        self.assertEqual(
            planet.crystal, initial_crystal - cost.get("crystal", 0) + expected_refund.get("crystal", 0)
        )
        self.assertEqual(planet.buildings.building_type, "")
        self.assertIsNone(planet.buildings.building_ends_at)
        self.assertEqual(planet.buildings.building_cost_paid,{})

    def test_cancel_building_does_not_increase_building_level(self):
        now = timezone.now()

        planet = self.create_planet(
            metal=10_000,
            crystal=10_000,
            metal_mine_level=3,
            last_resource_update=now,
        )

        start_building_upgrade(planet, "metal_mine", at=now)
        cancel_building_upgrade(planet, at=now)
        planet = self.reload_planet(planet)

        self.assertEqual(planet.buildings.metal_mine_level,3)

    def test_cancel_building_releases_reserved_planet_field(self):
        now = timezone.now()

        planet = self.create_planet(
            metal=10_000,
            crystal=10_000,
            last_resource_update=now,
        )

        start_building_upgrade(planet, "metal_mine", at=now)
        planet = self.reload_planet(planet)
        used_during_build = planet.buildings.get_used_fields(at=now)
        cancel_building_upgrade(planet, at=now)
        planet = self.reload_planet(planet)

        self.assertEqual(planet.buildings.get_used_fields(at=now), used_during_build - 1)

    def test_cancel_building_raises_when_no_building_is_in_progress(self):
        now = timezone.now()

        planet = self.create_planet(
            metal=10_000,
            crystal=10_000,
            last_resource_update=now,
        )

        old_metal = planet.metal
        old_crystal = planet.crystal

        with self.assertRaises(NoBuildingInProgressError):
            cancel_building_upgrade(planet, at=now)

        planet = self.reload_planet(planet)

        self.assertEqual(planet.metal, old_metal)
        self.assertEqual(planet.crystal, old_crystal)

    def test_cancel_building_rejects_building_after_end_time(self):
        start_time = timezone.now()

        planet = self.create_planet(
            metal=10_000,
            crystal=10_000,
            last_resource_update=start_time,
        )

        start_building_upgrade(planet, "metal_mine", at=start_time)
        planet = self.reload_planet(planet)
        end_time = planet.buildings.building_ends_at

        with self.assertRaises(NoBuildingInProgressError):
            cancel_building_upgrade(planet, at=end_time)

    def test_start_building_stores_paid_cost_snapshot(self):
        now = timezone.now()

        planet = self.create_planet(
            metal=10_000,
            crystal=10_000,
            last_resource_update=now,
        )

        expected_cost = get_upgrade_cost(planet, "metal_mine")
        start_building_upgrade(planet, "metal_mine", at=now)
        planet = self.reload_planet(planet)

        self.assertEqual(planet.buildings.building_cost_paid, expected_cost)
