from django.test import TestCase
from django.urls import reverse

from apps.game.domain.world import DEFAULT_UNIVERSE_RULES

from .helpers import PlanetTestMixin


class PlanetLimitViewTests(PlanetTestMixin, TestCase):
    def test_planet_detail_includes_planet_limit_status(self):
        user = self.create_user("planet_limit_detail_user")
        planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
        )

        self.client.force_login(user)

        response = self.client.get(reverse("game:planet_detail", kwargs={"pk": planet.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["planet_limit"].current, 1)
        self.assertEqual(
            response.context["planet_limit"].maximum,
            DEFAULT_UNIVERSE_RULES.max_planets_per_player,
        )
        self.assertContains(response, "Planety")
        self.assertContains(response, f"1/{DEFAULT_UNIVERSE_RULES.max_planets_per_player}")

    def test_send_fleet_includes_planet_limit_status(self):
        user = self.create_user("planet_limit_send_fleet_user")
        planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
        )

        self.client.force_login(user)

        response = self.client.get(reverse("game:send_fleet", kwargs={"pk": planet.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["planet_limit"].current, 1)
        self.assertEqual(
            response.context["planet_limit"].maximum,
            DEFAULT_UNIVERSE_RULES.max_planets_per_player,
        )
        self.assertContains(response, "Planety")
        self.assertContains(response, f"1/{DEFAULT_UNIVERSE_RULES.max_planets_per_player}")
