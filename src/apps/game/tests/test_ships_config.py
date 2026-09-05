from django.test import SimpleTestCase

from apps.game.ships import ESPIONAGE_PROBE_CODE, SHIPS


class ShipsConfigTests(SimpleTestCase):
    def test_espionage_probe_is_configured_for_espionage_mission(self):
        probe_config = SHIPS[ESPIONAGE_PROBE_CODE]

        self.assertEqual(probe_config["label"], "Sonda szpiegowska")
        self.assertEqual(probe_config["cargo_capacity"], 0)
        self.assertIn("espionage", probe_config["allowed_missions"])

    def test_transporters_are_not_configured_for_espionage_mission(self):
        self.assertNotIn("espionage", SHIPS["transporter"]["allowed_missions"])
        self.assertNotIn("espionage", SHIPS["large_transporter"]["allowed_missions"])
