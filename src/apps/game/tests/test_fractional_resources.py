from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.resources import (
    RESOURCE_PRECISION_MICRO,
    synchronize_resources,
)

from .helpers import PlanetTestMixin


class FractionalResourceProductionTests(PlanetTestMixin, TestCase):
    def test_frequent_synchronization_keeps_fractional_production(self):
        start_time = timezone.now()

        planet = self.create_planet(
            metal=0,
            crystal=0,
            helion=0,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=10,
            last_resource_update=start_time,
        )

        first_sync = start_time + timezone.timedelta(seconds=15)
        second_sync = start_time + timezone.timedelta(seconds=30)

        synchronize_resources(planet, at=first_sync, save=True)

        planet.refresh_from_db()

        self.assertEqual(planet.metal, 0)
        self.assertEqual(
            planet.metal_production_remainder_micro,
            RESOURCE_PRECISION_MICRO // 2,
        )
        self.assertEqual(planet.last_resource_update, first_sync)

        synchronize_resources(planet, at=second_sync, save=True)

        planet.refresh_from_db()

        self.assertEqual(planet.metal, 1)
        self.assertEqual(planet.metal_production_remainder_micro,0)
        self.assertEqual(planet.last_resource_update, second_sync)

    def test_save_false_updates_fractional_remainder_only_in_memory(self):
        start_time = timezone.now()

        planet = self.create_planet(
            metal=0,
            crystal=0,
            helion=0,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=10,
            last_resource_update=start_time,
        )

        sync_time = start_time + timezone.timedelta(seconds=15)

        synchronize_resources(planet, at=sync_time, save=False)

        self.assertEqual(planet.metal, 0)
        self.assertEqual(
            planet.metal_production_remainder_micro,
            RESOURCE_PRECISION_MICRO // 2,
        )
        self.assertEqual(planet.last_resource_update, sync_time)

        fresh_planet = type(planet).objects.get(pk=planet.pk)

        self.assertEqual(fresh_planet.metal, 0)
        self.assertEqual(fresh_planet.metal_production_remainder_micro,0)
        self.assertEqual(fresh_planet.last_resource_update, start_time)

    def test_full_storage_discards_fractional_remainder(self):
        start_time = timezone.now()

        planet = self.create_planet(
            metal=5000,
            crystal=0,
            helion=0,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=0,
            last_resource_update=start_time,
        )

        sync_time = start_time + timezone.timedelta(seconds=15)

        synchronize_resources(planet, at=sync_time, save=True)

        planet.refresh_from_db()

        self.assertEqual(planet.metal, 5000)
        self.assertEqual(planet.metal_production_remainder_micro,0)

    def test_overflow_discards_fractional_remainder(self):
        start_time = timezone.now()

        planet = self.create_planet(
            metal=4999,
            crystal=0,
            helion=0,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=0,
            last_resource_update=start_time,
        )

        sync_time = start_time + timezone.timedelta(seconds=45)

        synchronize_resources(planet, at=sync_time, save=True)

        planet.refresh_from_db()

        # 120/h przez 45 sekund = 1.5 metalu.
        # Do magazynu mieści się tylko 1.
        # Pozostałe 0.5 przepada.
        self.assertEqual(planet.metal, 5000)
        self.assertEqual(planet.metal_production_remainder_micro, 0)
