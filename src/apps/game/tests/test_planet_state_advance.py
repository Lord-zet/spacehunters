from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.sync import advance_planet_state

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
