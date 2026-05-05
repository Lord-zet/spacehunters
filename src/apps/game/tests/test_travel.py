from django.test import TestCase

from apps.game.domain_services.travel import calculate_distance, calculate_flight_time_seconds
from .helpers import PlanetTestMixin


class TravelCalculationTests(PlanetTestMixin, TestCase):
    def test_calculate_distance_returns_manhattan_distance_between_planets(self):
        user = self.create_user("travel1")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            x=1,
            y=1,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=4,
            y=6,
            is_homeland=False,
        )

        distance = calculate_distance(source_planet, target_planet)

        self.assertEqual(distance, 8)  # |4 - 1| + |6 - 1| = 3 + 5 = 8

    def test_calculate_flight_time_seconds_increases_with_distance(self):
        user = self.create_user("travel2")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            x=1,
            y=1,
        )
        near_planet = self.create_planet(
            owner=user,
            name="Near",
            x=2,
            y=1,
            is_homeland=False,
        )
        far_planet = self.create_planet(
            owner=user,
            name="Far",
            x=6,
            y=5,
            is_homeland=False,
        )

        near_time = calculate_flight_time_seconds(source_planet, near_planet)
        far_time = calculate_flight_time_seconds(source_planet, far_planet)

        self.assertGreater(far_time, near_time)
