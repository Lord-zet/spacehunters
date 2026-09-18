from django.test import SimpleTestCase

from apps.game.domain.world import Coordinates
from apps.game.domain_services.travel import calculate_distance, calculate_flight_time_seconds


class TravelCalculationTests(SimpleTestCase):
    def test_calculate_distance_returns_weighted_distance_between_planets(self):
        source = Coordinates(
            galaxy=1,
            system=1,
            position=1,
        )
        target = Coordinates(
            galaxy=1,
            system=4,
            position=6,
        )

        distance = calculate_distance(source, target)

        self.assertEqual(distance, 310)  # 3*95 + 5*5

    def test_calculate_flight_time_seconds_increases_with_distance(self):
        source = Coordinates(
            galaxy=1,
            system=1,
            position=1,
        )
        near = Coordinates(
            galaxy=1,
            system=1,
            position=2,
        )
        far = Coordinates(
            galaxy=2,
            system=6,
            position=5,
        )

        near_time = calculate_flight_time_seconds(source, near)
        far_time = calculate_flight_time_seconds(source, far)

        self.assertGreater(far_time, near_time)
