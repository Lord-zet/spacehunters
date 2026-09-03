from django.test import TestCase
from django.urls import reverse

from .helpers import PlanetTestMixin


class PlanetRenameViewTests(PlanetTestMixin, TestCase):
    def test_owner_can_rename_planet(self):
        user = self.create_user("rename_owner")
        planet = self.create_planet(
            owner=user,
            name="Old Terra",
            galaxy=1,
            system=10,
            position=1,
        )
        self.client.login(username="rename_owner", password="secret")

        response = self.client.post(
            reverse("game:rename_planet", kwargs={"pk": planet.pk}),
            {"name": "New Terra"},
        )

        planet = self.reload_planet(planet)
        self.assertRedirects(response, reverse("game:planet_detail", kwargs={"pk": planet.pk}))
        self.assertEqual(planet.name, "New Terra")

    def test_user_cannot_rename_other_users_planet(self):
        owner = self.create_user("rename_other_owner")
        intruder = self.create_user("rename_intruder")
        planet = self.create_planet(
            owner=owner,
            name="Private World",
            galaxy=1,
            system=10,
            position=2,
        )
        self.client.force_login(intruder)

        response = self.client.post(
            reverse("game:rename_planet", kwargs={"pk": planet.pk}),
            {"name": "Stolen World"},
        )

        planet = self.reload_planet(planet)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(planet.name, "Private World")
