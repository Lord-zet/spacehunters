from django.test import TestCase
from django.urls import reverse

from apps.game.domain_services.fleet import (
    calculate_effective_fleet_speed_multiplier,
    calculate_helion_cost_for_flight,
)
from apps.game.domain_services.travel import calculate_flight_time_seconds
from apps.game.fleet_speed_profiles import (
    get_fleet_fuel_multiplier,
)
from apps.game.ships import ESPIONAGE_PROBE_CODE

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
        ship_quantities = {"transporter": 1}
        speed_profile = "standard"
        expected_flight_time_seconds = calculate_flight_time_seconds(
            source,
            target,
            calculate_effective_fleet_speed_multiplier(
                ship_quantities,
                speed_profile,
            ),
        )
        expected_helion_cost = calculate_helion_cost_for_flight(
            source,
            target,
            ship_quantities,
            get_fleet_fuel_multiplier(speed_profile),
        )
        self.assertEqual(response.json(), {
            "ok": True,
            "preview": {
                "source_planet_id": source.pk,
                "mission_type": "transport",
                "target_planet_id": target.pk,
                "target_coordinates": target.coordinates,
                "speed_profile": speed_profile,
                "ship_quantities": ship_quantities,
                "flight_time_seconds": expected_flight_time_seconds,
                "helion_cost": expected_helion_cost,
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

    def test_send_fleet_preview_returns_validation_errors(self):
        user = self.create_user("preview_validation_user")
        source = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("game:send_fleet_preview", kwargs={"pk": source.pk}),
            data={
                "mission_type": "transport",
                "target_coordinates": "not-coordinates",
                "speed_profile": "standard",
                "ship_transporter": "1",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertIn(
            "Koordynaty",
            response.json()["non_field_errors"][0],
        )

    def test_send_fleet_preview_uses_speed_profile_multipliers(self):
        user = self.create_user("preview_speed_profile_user")
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
            system=5,
            position=1,
            is_homeland=False,
        )

        self.client.force_login(user)

        def post_preview(speed_profile):
            response = self.client.post(
                reverse("game:send_fleet_preview", kwargs={"pk": source.pk}),
                data={
                    "mission_type": "transport",
                    "target_planet": str(target.pk),
                    "target_coordinates": target.coordinates,
                    "speed_profile": speed_profile,
                    "ship_transporter": "1",
                },
            )

            self.assertEqual(response.status_code, 200)
            return response.json()["preview"]

        standard_preview = post_preview("standard")
        fast_preview = post_preview("fast")

        self.assertLess(
            fast_preview["flight_time_seconds"],
            standard_preview["flight_time_seconds"],
        )
        self.assertGreater(
            fast_preview["helion_cost"],
            standard_preview["helion_cost"],
        )

    def test_send_fleet_preview_uses_selected_ship_base_speed(self):
        user = self.create_user("preview_ship_speed_user")
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
            system=5,
            position=1,
            is_homeland=False,
        )

        self.client.force_login(user)

        transporter_response = self.client.post(
            reverse("game:send_fleet_preview", kwargs={"pk": source.pk}),
            data={
                "mission_type": "transport",
                "target_planet": str(target.pk),
                "target_coordinates": target.coordinates,
                "speed_profile": "standard",
                "ship_transporter": "1",
            },
        )
        probe_response = self.client.post(
            reverse("game:send_fleet_preview", kwargs={"pk": source.pk}),
            data={
                "mission_type": "espionage",
                "target_planet": str(target.pk),
                "target_coordinates": target.coordinates,
                "speed_profile": "standard",
                f"ship_{ESPIONAGE_PROBE_CODE}": "1",
            },
        )

        self.assertEqual(transporter_response.status_code, 200)
        self.assertEqual(probe_response.status_code, 200)
        self.assertLess(
            probe_response.json()["preview"]["flight_time_seconds"],
            transporter_response.json()["preview"]["flight_time_seconds"],
        )
