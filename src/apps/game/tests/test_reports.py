from django.test import TestCase
from django.http import Http404
from django.urls import reverse

from apps.game.domain_services.reports import (
    ESPIONAGE_PLANET_SECTION,
    REPORT_PAYLOAD_SCHEMA_VERSION,
    build_espionage_payload,
    build_planet_intel_section,
    create_espionage_report,
)
from apps.game.models import Report
from apps.game.selectors.reports import (
    get_unread_reports_count,
    get_user_report_or_404,
    get_user_reports,
)
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


class ReportSelectorTests(PlanetTestMixin, TestCase):
    def test_get_user_reports_returns_only_owned_reports_in_category(self):
        owner = self.create_user("selector_report_owner")
        other_user = self.create_user("selector_report_other")
        source_planet = self.create_planet(
            owner=owner,
            name="Source",
            galaxy=1,
            system=10,
            position=1,
        )
        target_planet = self.create_planet(
            owner=other_user,
            name="Target",
            galaxy=1,
            system=11,
            position=1,
            is_homeland=True,
        )
        other_source = self.create_planet(
            owner=other_user,
            name="Other Source",
            galaxy=1,
            system=12,
            position=1,
            is_homeland=False,
        )

        own_report = create_espionage_report(
            owner=owner,
            source_planet=source_planet,
            target_planet=target_planet,
        )
        create_espionage_report(
            owner=other_user,
            source_planet=other_source,
            target_planet=source_planet,
        )

        reports = list(get_user_reports(owner, category=Report.Category.ESPIONAGE))

        self.assertEqual(reports, [own_report])
        self.assertEqual(get_unread_reports_count(owner), 1)

    def test_get_user_report_or_404_rejects_other_users_report(self):
        owner = self.create_user("selector_report_owner_404")
        other_user = self.create_user("selector_report_other_404")
        source_planet = self.create_planet(
            owner=owner,
            name="Source",
            galaxy=1,
            system=20,
            position=1,
        )
        target_planet = self.create_planet(
            owner=other_user,
            name="Target",
            galaxy=1,
            system=21,
            position=1,
            is_homeland=True,
        )
        report = create_espionage_report(
            owner=owner,
            source_planet=source_planet,
            target_planet=target_planet,
        )

        with self.assertRaises(Http404):
            get_user_report_or_404(other_user, report.pk)


class ReportViewTests(PlanetTestMixin, TestCase):
    def test_reports_view_lists_only_current_users_reports(self):
        owner = self.create_user("view_report_owner")
        other_user = self.create_user("view_report_other")
        third_user = self.create_user("view_report_third")
        source_planet = self.create_planet(
            owner=owner,
            name="Source",
            galaxy=1,
            system=30,
            position=1,
        )
        own_target = self.create_planet(
            owner=other_user,
            name="Visible Target",
            galaxy=1,
            system=31,
            position=1,
            is_homeland=True,
        )
        other_source = self.create_planet(
            owner=other_user,
            name="Other Source",
            galaxy=1,
            system=32,
            position=1,
            is_homeland=False,
        )
        hidden_target = self.create_planet(
            owner=third_user,
            name="Hidden Target",
            galaxy=1,
            system=33,
            position=1,
            is_homeland=True,
        )

        create_espionage_report(
            owner=owner,
            source_planet=source_planet,
            target_planet=own_target,
        )
        create_espionage_report(
            owner=other_user,
            source_planet=other_source,
            target_planet=hidden_target,
        )
        self.client.force_login(owner)

        response = self.client.get(reverse("game:reports", kwargs={"pk": source_planet.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible Target")
        self.assertNotContains(response, "Hidden Target")

    def test_report_detail_marks_report_as_read(self):
        owner = self.create_user("view_report_detail_owner")
        target_owner = self.create_user("view_report_detail_target_owner")
        source_planet = self.create_planet(
            owner=owner,
            name="Source",
            galaxy=1,
            system=40,
            position=1,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=1,
            system=41,
            position=1,
            is_homeland=True,
        )
        report = create_espionage_report(
            owner=owner,
            source_planet=source_planet,
            target_planet=target_planet,
        )
        self.client.force_login(owner)

        response = self.client.get(
            reverse(
                "game:report_detail",
                kwargs={"pk": source_planet.pk, "report_id": report.pk},
            )
        )

        report.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(report.is_read)
