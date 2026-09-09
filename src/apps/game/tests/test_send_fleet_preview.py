from django.test import TestCase
from django.urls import reverse

from .helpers import PlanetTestMixin


class SendFleetPreviewViewTests(PlanetTestMixin, TestCase):
    def test_send_fleet_preview_requires_login(self):
        user = self.create_user("preview_login_user")
        planet = self.create_planet(owner=user)

        response = self.client.post(
            reverse("game:send_fleet_preview", kwargs={"pk": planet.pk}),
            data={},
        )

        self.assertEqual(response.status_code, 302)

    def test_send_fleet_preview_returns_json_payload_for_owner(self):
        user = self.create_user("preview_owner_user")
        source = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
        )
        target = self.create_planet(
            owner=user,
            name="Target",
            galaxy=1,
            system=2,
            position=1,
            is_homeland=False,
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("game:send_fleet_preview", kwargs={"pk": source.pk}),
            data={
                "mission_type": "transport",
                "target_planet": str(target.pk),
                "target_coordinates": target.coordinates,
                "speed_profile": "standard",
                "ship_transporter": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-type"], "application/json")
        self.assertEqual(response.json(), {
            "ok": True,
            "preview": {
                "source_planet_id": source.pk,
                "mission_type": "transport",
                "target_planet_id": target.pk,
                "target_coordinates": target.coordinates,
                "speed_profile": "standard",
                "ship_quantities": {
                    "transporter": 1,
                },
            },
        })

    def test_send_fleet_preview_ignores_empty_ship_fields(self):
        user = self.create_user("preview_empty_ship_user")
        source = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
        )
        target = self.create_planet(
            owner=user,
            name="Target",
            galaxy=1,
            system=2,
            position=1,
            is_homeland=False,
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("game:send_fleet_preview", kwargs={"pk": source.pk}),
            data={
                "mission_type": "transport",
                "target_planet": str(target.pk),
                "target_coordinates": target.coordinates,
                "speed_profile": "standard",
                "ship_transporter": "1",
                "ship_large_transporter": "",
                "ship_espionage_probe": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["preview"]["ship_quantities"], {
            "transporter": 1,
        })
