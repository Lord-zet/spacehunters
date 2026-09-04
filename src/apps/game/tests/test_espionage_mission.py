from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import FleetError
from apps.game.domain_services.fleet import send_espionage_fleet, process_fleets_for_user
from apps.game.domain_services.resources import Resource
from apps.game.forms import SendFleetForm
from apps.game.models import Fleet, Report
from .helpers import PlanetTestMixin


class EspionageMissionTests(PlanetTestMixin, TestCase):
    def test_send_espionage_fleet_creates_returning_mission_without_cargo(self):
        user = self.create_user("espionage_sender")
        target_owner = self.create_user("espionage_target_owner")
        now = timezone.now()
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            helion=10_000,
            transporter_count=5,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=1,
            system=2,
            position=1,
            is_homeland=True,
            last_resource_update=now,
        )

        fleet = send_espionage_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            ship_quantities=2,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            user=user,
            at=now,
        )

        source_planet.refresh_from_db()

        self.assertEqual(fleet.mission_type, Fleet.MissionType.ESPIONAGE)
        self.assertEqual(fleet.status, Fleet.Status.OUTBOUND)
        self.assertIsNotNone(fleet.return_time)
        self.assertEqual(fleet.metal, 0)
        self.assertEqual(fleet.crystal, 0)
        self.assertEqual(fleet.helion, 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 3)

    def test_process_espionage_arrival_creates_report_and_sets_fleet_returning(self):
        user = self.create_user("espionage_report_sender")
        target_owner = self.create_user("espionage_report_target_owner")
        now = timezone.now()
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=3,
            position=1,
            helion=10_000,
            transporter_count=3,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=1,
            system=4,
            position=1,
            is_homeland=True,
            planet_type="ice",
            radius_km=7_100,
            temperature_min=-80,
            temperature_max=-35,
            last_resource_update=now,
        )
        fleet = send_espionage_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            ship_quantities=1,
            cargo={},
            user=user,
            at=now,
        )

        process_fleets_for_user(user, at=fleet.arrival_time)

        fleet.refresh_from_db()
        report = Report.objects.get(owner=user)

        self.assertEqual(fleet.status, Fleet.Status.RETURNING)
        self.assertEqual(report.category, Report.Category.ESPIONAGE)
        self.assertEqual(report.report_type, Report.ReportType.PLANET_SCAN)
        self.assertEqual(report.fleet, fleet)
        self.assertEqual(report.source_planet, source_planet)
        self.assertEqual(report.target_planet, target_planet)
        self.assertEqual(
            report.payload["sections"]["planet"],
            {
                "planet_type": "ice",
                "radius_km": 7_100,
                "temperature_min": -80,
                "temperature_max": -35,
            },
        )

    def test_process_espionage_return_restores_ships_to_source_planet(self):
        user = self.create_user("espionage_return_sender")
        target_owner = self.create_user("espionage_return_target_owner")
        now = timezone.now()
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=5,
            position=1,
            helion=10_000,
            transporter_count=2,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=1,
            system=6,
            position=1,
            is_homeland=True,
            last_resource_update=now,
        )
        fleet = send_espionage_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            ship_quantities=2,
            cargo={},
            user=user,
            at=now,
        )

        process_fleets_for_user(user, at=fleet.return_time)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 2)
        self.assertEqual(Report.objects.filter(owner=user).count(), 1)

    def test_send_espionage_fleet_rejects_cargo(self):
        user = self.create_user("espionage_cargo_sender")
        target_owner = self.create_user("espionage_cargo_target_owner")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=7,
            position=1,
            helion=10_000,
            transporter_count=1,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=1,
            system=8,
            position=1,
            is_homeland=True,
        )

        with self.assertRaises(FleetError):
            send_espionage_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities=1,
                cargo={Resource.METAL: 1},
                user=user,
            )


class SendFleetEspionageFormTests(PlanetTestMixin, TestCase):
    def test_form_allows_espionage_target_owned_by_other_user(self):
        user = self.create_user("espionage_form_sender")
        target_owner = self.create_user("espionage_form_target_owner")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=2,
            system=1,
            position=1,
            transporter_count=1,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=2,
            system=2,
            position=1,
            is_homeland=True,
        )

        form = SendFleetForm(
            data={
                "mission_type": Fleet.MissionType.ESPIONAGE,
                "target_planet": target_planet.pk,
                "speed_profile": "standard",
                "ship_transporter": 1,
                "metal": 0,
                "crystal": 0,
                "helion": 0,
            },
            user=user,
            source_planet=source_planet,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_transport_target_owned_by_other_user(self):
        user = self.create_user("transport_form_sender")
        target_owner = self.create_user("transport_form_target_owner")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=2,
            system=3,
            position=1,
            transporter_count=1,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=2,
            system=4,
            position=1,
            is_homeland=True,
        )

        form = SendFleetForm(
            data={
                "mission_type": Fleet.MissionType.TRANSPORT,
                "target_planet": target_planet.pk,
                "speed_profile": "standard",
                "ship_transporter": 1,
                "metal": 0,
                "crystal": 0,
                "helion": 0,
            },
            user=user,
            source_planet=source_planet,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_form_rejects_espionage_cargo(self):
        user = self.create_user("espionage_form_cargo_sender")
        target_owner = self.create_user("espionage_form_cargo_target_owner")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=2,
            system=5,
            position=1,
            transporter_count=1,
        )
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=2,
            system=6,
            position=1,
            is_homeland=True,
        )

        form = SendFleetForm(
            data={
                "mission_type": Fleet.MissionType.ESPIONAGE,
                "target_planet": target_planet.pk,
                "speed_profile": "standard",
                "ship_transporter": 1,
                "metal": 1,
                "crystal": 0,
                "helion": 0,
            },
            user=user,
            source_planet=source_planet,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
