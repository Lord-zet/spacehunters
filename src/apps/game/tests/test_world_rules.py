from django.test import SimpleTestCase

from apps.game.domain.exceptions import InvalidCoordinatesError
from apps.game.domain.world import Coordinates, DEFAULT_UNIVERSE_RULES, UniverseRules


class CoordinatesTests(SimpleTestCase):
    def test_parse_returns_coordinates(self):
        coordinates = Coordinates.parse("2:145:9")

        self.assertEqual(coordinates.galaxy, 2)
        self.assertEqual(coordinates.system, 145)
        self.assertEqual(coordinates.position, 9)

    def test_parse_rejects_invalid_format(self):
        with self.assertRaises(InvalidCoordinatesError):
            Coordinates.parse("1:2")

    def test_parse_rejects_non_numeric_values(self):
        with self.assertRaises(InvalidCoordinatesError):
            Coordinates.parse("1:x:3")

    def test_coordinates_string_uses_galaxy_system_position(self):
        coordinates = Coordinates(galaxy=2, system=145, position=9)

        self.assertEqual(str(coordinates), "2:145:9")

    def test_coordinates_can_be_exported_as_tuple(self):
        coordinates = Coordinates(galaxy=2, system=145, position=9)

        self.assertEqual(coordinates.as_tuple(), (2, 145, 9))


class UniverseRulesTests(SimpleTestCase):
    def test_default_rules_match_single_universe_limits(self):
        self.assertEqual(DEFAULT_UNIVERSE_RULES.galaxy_count, 9)
        self.assertEqual(DEFAULT_UNIVERSE_RULES.systems_per_galaxy, 499)
        self.assertEqual(DEFAULT_UNIVERSE_RULES.positions_per_system, 15)
        self.assertEqual(DEFAULT_UNIVERSE_RULES.max_planets_per_player, 9)

    def test_contains_accepts_coordinates_inside_universe(self):
        rules = UniverseRules(galaxy_count=2, systems_per_galaxy=10, positions_per_system=5)

        self.assertTrue(rules.contains(Coordinates(galaxy=2, system=10, position=5)))

    def test_contains_rejects_zero_values(self):
        rules = UniverseRules(galaxy_count=2, systems_per_galaxy=10, positions_per_system=5)

        self.assertFalse(rules.contains(Coordinates(galaxy=0, system=1, position=1)))
        self.assertFalse(rules.contains(Coordinates(galaxy=1, system=0, position=1)))
        self.assertFalse(rules.contains(Coordinates(galaxy=1, system=1, position=0)))

    def test_contains_rejects_coordinates_outside_universe(self):
        rules = UniverseRules(galaxy_count=2, systems_per_galaxy=10, positions_per_system=5)

        self.assertFalse(rules.contains(Coordinates(galaxy=3, system=1, position=1)))
        self.assertFalse(rules.contains(Coordinates(galaxy=1, system=11, position=1)))
        self.assertFalse(rules.contains(Coordinates(galaxy=1, system=1, position=6)))

    def test_validate_coordinates_raises_for_coordinates_outside_universe(self):
        rules = UniverseRules(galaxy_count=2, systems_per_galaxy=10, positions_per_system=5)

        with self.assertRaises(InvalidCoordinatesError):
            rules.validate_coordinates(Coordinates(galaxy=3, system=1, position=1))
