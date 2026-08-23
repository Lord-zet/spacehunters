from django.test import TestCase
from django.utils import timezone

from apps.game.buildings import calculate_resource_production
from apps.game.domain_services.energy import (
    apply_energy_efficiency_to_production,
    get_energy_balance,
    get_energy_consumption,
    get_energy_production,
)
from apps.game.domain_services.resources import (
    get_production_per_hour,
    get_raw_production_per_hour,
    synchronize_resources,
)

from .helpers import PlanetTestMixin


class PlanetEnergyTests(PlanetTestMixin, TestCase):
    def test_solar_array_produces_energy(self):
        planet = self.create_planet(
            solar_array_level=1,
            metal_mine_level=0,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )

        self.assertGreater(get_energy_production(planet.get_buildings()),0)

    def test_mines_consume_energy(self):
        planet = self.create_planet(
            solar_array_level=0,
            metal_mine_level=1,
            crystal_mine_level=1,
            helion_synthesizer_level=1,
        )

        self.assertGreater(get_energy_consumption(planet.get_buildings()),0)

    def test_energy_balance_reports_shortage(self):
        planet = self.create_planet(
            solar_array_level=0,
            metal_mine_level=3,
            crystal_mine_level=3,
            helion_synthesizer_level=1,
        )

        balance = get_energy_balance(planet.get_buildings())

        self.assertEqual(balance.produced, 0)
        self.assertGreater(balance.consumed, 0)
        self.assertTrue(balance.is_shortage)
        self.assertEqual(balance.efficiency_percent, 0)

    def test_energy_balance_reports_full_efficiency_when_enough_energy(self):
        planet = self.create_planet(
            solar_array_level=5,
            metal_mine_level=1,
            crystal_mine_level=1,
            helion_synthesizer_level=0,
        )

        balance = get_energy_balance(planet.get_buildings())

        self.assertGreaterEqual(balance.produced, balance.consumed)
        self.assertFalse(balance.is_shortage)
        self.assertEqual(balance.efficiency_percent, 100)

    def test_resource_production_is_scaled_by_energy_shortage(self):
        planet = self.create_planet(
            solar_array_level=0,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )

        production = get_production_per_hour(planet.get_buildings())

        self.assertEqual(production["metal"], 0)

    def test_raw_production_ignores_energy_but_effective_production_uses_it(self):
        planet = self.create_planet(
            solar_array_level=0,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )

        buildings = planet.get_buildings()
        raw_production = get_raw_production_per_hour(buildings)
        effective_production = get_production_per_hour(buildings)

        self.assertEqual(
            raw_production["metal"],
            calculate_resource_production(1, 120, 1.18),
        )
        self.assertEqual(effective_production["metal"],0)

    def test_synchronize_resources_uses_energy_scaled_production(self):
        start_time = timezone.now()

        planet = self.create_planet(
            metal=0,
            crystal=0,
            helion=0,
            solar_array_level=0,
            metal_mine_level=1,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=10,
            last_resource_update=start_time,
        )

        synchronize_resources(planet, at=start_time + timezone.timedelta(hours=1), save=True)
        planet.refresh_from_db()

        self.assertEqual(planet.metal, 0)

    def test_apply_energy_efficiency_scales_all_resources(self):
        class FakeBalance:
            produced = 50
            consumed = 100

        production = apply_energy_efficiency_to_production({"metal": 120, "crystal": 80}, FakeBalance())

        self.assertEqual(production, {"metal": 60, "crystal": 40})
