from django.test import TestCase

from apps.game.domain.exceptions import InvalidCoordinatesError, PlanetLimitReachedError
from apps.game.domain.world import Coordinates, DEFAULT_UNIVERSE_RULES
from apps.game.domain_services.planets import (
    create_planet,
    get_planet_at_coordinates,
    get_planet_limit_status,
)
from .helpers import PlanetTestMixin


class PlanetCreationTests(PlanetTestMixin, TestCase):
    def test_create_planet_creates_required_state_records(self):
        user = self.create_user("planet_create_1")

        planet = create_planet(
            owner=user,
            name="Earth",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            is_homeland=True,
            ships={
                "transporter": 2,
            },
        )

        self.assertIsNotNone(planet.get_buildings())
        self.assertIsNotNone(planet.get_ship_construction())
        self.assertEqual(planet.get_ship_quantity("transporter"),2)

    def test_missing_planet_ship_record_means_zero_quantity(self):
        user = self.create_user("planet_create_2")

        planet = create_planet(
            owner=user,
            name="Earth",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            is_homeland=True,
        )

        self.assertEqual(planet.get_ship_quantity("transporter"), 0)
        self.assertEqual(planet.transporter_count,0)

    def test_create_planet_rejects_coordinates_outside_universe(self):
        user = self.create_user("planet_create_outside_universe")

        with self.assertRaises(InvalidCoordinatesError):
            create_planet(
                owner=user,
                name="Outside",
                coordinates=Coordinates(
                    galaxy=DEFAULT_UNIVERSE_RULES.galaxy_count + 1,
                    system=1,
                    position=1,
                ),
                is_homeland=True,
            )

    def test_create_planet_rejects_planets_above_player_limit(self):
        user = self.create_user("planet_create_limit")

        for index in range(DEFAULT_UNIVERSE_RULES.max_planets_per_player):
            create_planet(
                owner=user,
                name=f"Planet {index + 1}",
                coordinates=Coordinates(galaxy=1, system=index + 1, position=1),
                is_homeland=(index == 0),
            )

        with self.assertRaises(PlanetLimitReachedError):
            create_planet(
                owner=user,
                name="Too Many",
                coordinates=Coordinates(
                    galaxy=1,
                    system=DEFAULT_UNIVERSE_RULES.max_planets_per_player + 1,
                    position=1,
                ),
                is_homeland=False,
            )

    def test_get_planet_limit_status_returns_current_capacity(self):
        user = self.create_user("planet_create_limit_status")

        create_planet(
            owner=user,
            name="Earth",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            is_homeland=True,
        )

        status = get_planet_limit_status(user)

        self.assertEqual(status.current, 1)
        self.assertEqual(status.maximum, DEFAULT_UNIVERSE_RULES.max_planets_per_player)
        self.assertEqual(status.remaining, DEFAULT_UNIVERSE_RULES.max_planets_per_player - 1)
        self.assertFalse(status.is_reached)

    def test_get_planet_at_coordinates_returns_planet_matching_coordinates(self):
        planet = self.create_planet(
            galaxy=2,
            system=20,
            position=7,
        )

        found_planet = get_planet_at_coordinates(Coordinates(galaxy=2, system=20, position=7))

        self.assertEqual(found_planet, planet)

    def test_get_planet_at_coordinates_returns_none_for_empty_position(self):
        self.assertIsNone(
            get_planet_at_coordinates(Coordinates(galaxy=2, system=20, position=7))
        )
