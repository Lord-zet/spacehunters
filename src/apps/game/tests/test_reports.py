from django.test import TestCase

from apps.game.domain_services.reports import (
    ESPIONAGE_PLANET_SECTION,
    REPORT_PAYLOAD_SCHEMA_VERSION,
    build_espionage_payload,
    build_planet_intel_section,
    create_espionage_report,
)
from apps.game.models import Report
from .helpers import PlanetTestMixin


class ReportServiceTests(PlanetTestMixin, TestCase):
    def test_build_planet_intel_section_contains_basic_planet_traits(self):
        user = self.create_user("report_planet_traits")
        planet = self.create_planet(
            owner=user,
            name="Target",
            planet_type="ice",
            radius_km=7_500,
            temperature_min=-90,
            temperature_max=-30,
        )

        section = build_planet_intel_section(planet)

        self.assertEqual(section, {
            "planet_type": "ice",
            "radius_km": 7_500,
            "temperature_min": -90,
            "temperature_max": -30,
        })

    def test_build_espionage_payload_wraps_sections_with_schema_version(self):
        user = self.create_user("report_payload")
        target_planet = self.create_planet(
            owner=user,
            name="Target",
            planet_type="desert",
            radius_km=5_400,
            temperature_min=15,
            temperature_max=75,
        )

        payload = build_espionage_payload(target_planet=target_planet)

        self.assertEqual(payload["schema_version"], REPORT_PAYLOAD_SCHEMA_VERSION)
        self.assertEqual(
            payload["sections"][ESPIONAGE_PLANET_SECTION],
            {
                "planet_type": "desert",
                "radius_km": 5_400,
                "temperature_min": 15,
                "temperature_max": 75,
            },
        )

    def test_build_espionage_payload_rejects_unknown_section(self):
        user = self.create_user("report_unknown_section")
        target_planet = self.create_planet(owner=user, name="Target")

        with self.assertRaises(ValueError):
            build_espionage_payload(
                target_planet=target_planet,
                sections=["unknown"],
            )

    def test_create_espionage_report_saves_report_with_payload_and_context(self):
        owner = self.create_user("report_owner")
        target_owner = self.create_user("report_target_owner")
        source_planet = self.create_planet(
            owner=owner,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=1,
            system=2,
            position=1,
            is_homeland=True,
            planet_type="ocean",
            radius_km=6_800,
            temperature_min=-5,
            temperature_max=35,
        )

        report = create_espionage_report(
            owner=owner,
            source_planet=source_planet,
            target_planet=target_planet,
        )

        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(report.owner, owner)
        self.assertEqual(report.category, Report.Category.ESPIONAGE)
        self.assertEqual(report.report_type, Report.ReportType.PLANET_SCAN)
        self.assertEqual(report.source_planet, source_planet)
        self.assertEqual(report.target_planet, target_planet)
        self.assertIsNone(report.fleet)
        self.assertFalse(report.is_read)
        self.assertEqual(
            report.payload["sections"][ESPIONAGE_PLANET_SECTION],
            {
                "planet_type": "ocean",
                "radius_km": 6_800,
                "temperature_min": -5,
                "temperature_max": 35,
            },
        )
