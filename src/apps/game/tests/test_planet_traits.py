import random

from django.test import TestCase

from apps.game.domain_services.planet_generation import generate_planet_traits
from apps.game.planet_types import PLANET_TYPES, get_planet_type_config
from apps.game.presenters.planets import (
    format_radius,
    format_temperature_range,
    get_planet_trait_rows,
)

from .helpers import PlanetTestMixin


class PlanetTraitGenerationTests(TestCase):
    def test_generate_planet_traits_uses_requested_planet_type(self):
        traits = generate_planet_traits(
            planet_type="ice",
            rng=random.Random(123),
        )

        self.assertEqual(traits.planet_type, "ice")

    def test_generated_radius_is_within_planet_type_range(self):
        traits = generate_planet_traits(
            planet_type="desert",
            rng=random.Random(123),
        )

        config = PLANET_TYPES["desert"]
        radius_min, radius_max = config["radius_km_range"]

        self.assertGreaterEqual(traits.radius_km, radius_min)
        self.assertLessEqual(traits.radius_km, radius_max)

    def test_generated_temperature_is_within_planet_type_ranges(self):
        traits = generate_planet_traits(
            planet_type="volcanic",
            rng=random.Random(123),
        )

        config = PLANET_TYPES["volcanic"]
        temp_min_low, temp_min_high = config["temperature_min_range"]
        temp_max_low, temp_max_high = config["temperature_max_range"]

        self.assertGreaterEqual(traits.temperature_min, temp_min_low)
        self.assertLessEqual(traits.temperature_min, temp_min_high)
        self.assertGreaterEqual(traits.temperature_max, temp_max_low)
        self.assertLessEqual(traits.temperature_max, temp_max_high)
        self.assertLessEqual(traits.temperature_min, traits.temperature_max)


class PlanetTraitPersistenceTests(PlanetTestMixin, TestCase):
    def test_create_planet_stores_explicit_traits(self):
        planet = self.create_planet(
            planet_type="desert",
            radius_km=6_200,
            temperature_min=-10,
            temperature_max=90,
        )

        planet.refresh_from_db()

        self.assertEqual(planet.planet_type, "desert")
        self.assertEqual(planet.radius_km, 6_200)
        self.assertEqual(planet.temperature_min, -10)
        self.assertEqual(planet.temperature_max, 90)

    def test_create_planet_uses_stable_default_traits_in_tests(self):
        planet = self.create_planet()

        self.assertEqual(planet.planet_type, "terrestrial")
        self.assertEqual(planet.radius_km, 6_000)
        self.assertEqual(planet.temperature_min, -20)
        self.assertEqual(planet.temperature_max, 40)


class PlanetTraitPresenterTests(PlanetTestMixin, TestCase):
    def test_format_radius(self):
        self.assertEqual(format_radius(6371), "6 371 km")

    def test_format_temperature_range(self):
        self.assertEqual(format_temperature_range(-20, 40), "-20°C do 40°C")

    def test_planet_trait_rows_include_type_radius_and_temperature(self):
        planet = self.create_planet(
            planet_type="ice",
            radius_km=5_100,
            temperature_min=-140,
            temperature_max=-30,
        )

        rows = get_planet_trait_rows(planet)

        self.assertEqual(
            rows,
            [
                {"label": "Typ planety", "value": "Planeta lodowa"},
                {"label": "Promień", "value": "5 100 km"},
                {"label": "Temperatura", "value": "-140°C do -30°C"},
            ],
        )
