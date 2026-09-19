from django.test import SimpleTestCase

from apps.game.domain.world import UniverseRules
from apps.game.presenters.world import get_universe_coordinate_hint


class UniversePresenterTests(SimpleTestCase):
    def test_coordinate_hint_describes_universe_bounds(self):
        rules = UniverseRules(
            galaxy_count=2,
            systems_per_galaxy=10,
            positions_per_system=5,
        )

        self.assertEqual(
            get_universe_coordinate_hint(rules),
            "Zakres: galaktyka 1-2, system 1-10, pozycja 1-5.",
        )
