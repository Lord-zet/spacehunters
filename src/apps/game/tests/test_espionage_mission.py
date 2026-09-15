from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import FleetError
from apps.game.domain_services.fleet import send_espionage_fleet, process_fleets_for_user
from apps.game.domain_services.resources import Resource
from apps.game.forms import SendFleetForm, parse_planet_coordinates
from apps.game.models import Fleet, PlanetShip, Report
from apps.game.ships import ESPIONAGE_PROBE_CODE
from .helpers import PlanetTestMixin


class EspionageMissionTests(PlanetTestMixin, TestCase):
    def add_espionage_probes(self, planet, quantity):
        return PlanetShip.objects.create(
            planet=planet,
            ship_code=ESPIONAGE_PROBE_CODE,
            quantity=quantity,
        )

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
            last_resource_update=now,
        )
        self.add_espionage_probes(source_planet, 5)
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
            ship_quantities={ESPIONAGE_PROBE_CODE: 2},
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
        self.assertEqual(self.get_planet_ship_quantity(source_planet, ESPIONAGE_PROBE_CODE), 3)

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
            last_resource_update=now,
        )
        self.add_espionage_probes(source_planet, 3)
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
            ship_quantities={ESPIONAGE_PROBE_CODE: 1},
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
            last_resource_update=now,
        )
        self.add_espionage_probes(source_planet, 2)
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
            ship_quantities={ESPIONAGE_PROBE_CODE: 2},
            cargo={},
            user=user,
            at=now,
        )

        process_fleets_for_user(user, at=fleet.return_time)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, ESPIONAGE_PROBE_CODE), 2)
        self.assertEqual(Report.objects.filter(owner=user).count(), 1)

    def test_send_espionage_fleet_rejects_transporter(self):
        user = self.create_user("espionage_transporter_sender")
        target_owner = self.create_user("espionage_transporter_target_owner")
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
                ship_quantities={"transporter": 1},
                cargo={},
                user=user,
            )

        self.assertEqual(Fleet.objects.count(), 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 1)

    def test_send_espionage_fleet_rejects_mixed_fleet(self):
        user = self.create_user("espionage_mixed_sender")
        target_owner = self.create_user("espionage_mixed_target_owner")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=9,
            position=1,
            helion=10_000,
            transporter_count=1,
        )
        self.add_espionage_probes(source_planet, 1)
        target_planet = self.create_planet(
            owner=target_owner,
            name="Target",
            galaxy=1,
            system=10,
            position=1,
            is_homeland=True,
        )

        with self.assertRaises(FleetError):
            send_espionage_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={
                    ESPIONAGE_PROBE_CODE: 1,
                    "transporter": 1,
                },
                cargo={},
                user=user,
            )

        self.assertEqual(Fleet.objects.count(), 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, ESPIONAGE_PROBE_CODE), 1)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 1)

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
                "target_coordinates": target_planet.coordinates,
                "speed_profile": "standard",
                f"ship_{ESPIONAGE_PROBE_CODE}": 1,
                "metal": 0,
                "crystal": 0,
                "helion": 0,
            },
            user=user,
            source_planet=source_planet,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_form_allows_transport_target_owned_by_other_user(self):
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
                "target_coordinates": target_planet.coordinates,
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
        self.assertEqual(form.cleaned_data["target_planet"], target_planet)

    def test_form_rejects_station_target_owned_by_other_user(self):
        user = self.create_user("station_form_sender")
        target_owner = self.create_user("station_form_target_owner")
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
                "mission_type": Fleet.MissionType.STATION,
                "target_coordinates": target_planet.coordinates,
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
                "target_coordinates": target_planet.coordinates,
                "speed_profile": "standard",
                f"ship_{ESPIONAGE_PROBE_CODE}": 1,
                "metal": 1,
                "crystal": 0,
                "helion": 0,
            },
            user=user,
            source_planet=source_planet,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_form_resolves_selected_own_target_planet_to_coordinates(self):
        user = self.create_user("coordinates_form_sender")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=2,
            system=7,
            position=1,
            transporter_count=1,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Target",
            galaxy=2,
            system=8,
            position=1,
            is_homeland=False,
        )

        form = SendFleetForm(
            data={
                "mission_type": Fleet.MissionType.TRANSPORT,
                "target_planet": target_planet.pk,
                "target_coordinates": "",
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
        self.assertEqual(form.cleaned_data["target_planet"], target_planet)
        self.assertEqual(form.cleaned_data["target_coordinates"], target_planet.coordinates)

    def test_parse_planet_coordinates_rejects_invalid_format(self):
        with self.assertRaisesMessage(Exception, "format"):
            parse_planet_coordinates("2-8-1")

    def test_form_rejects_unknown_target_coordinates(self):
        user = self.create_user("coordinates_form_unknown")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=2,
            system=9,
            position=1,
            transporter_count=1,
        )

        form = SendFleetForm(
            data={
                "mission_type": Fleet.MissionType.TRANSPORT,
                "target_coordinates": "99:99:99",
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

    def test_form_allows_colonization_empty_target_coordinates(self):
        user = self.create_user("colonization_form_sender")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=2,
            system=10,
            position=1,
            transporter_count=1,
        )

        form = SendFleetForm(
            data={
                "mission_type": Fleet.MissionType.COLONIZE,
                "target_coordinates": "2:99:9",
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
        self.assertIsNone(form.cleaned_data["target_planet"])
        self.assertEqual(form.cleaned_data["target_coordinates"], "2:99:9")

    def test_form_rejects_colonization_existing_target_coordinates(self):
        user = self.create_user("colonization_form_occupied_sender")
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=2,
            system=10,
            position=1,
            transporter_count=1,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Occupied",
            galaxy=2,
            system=99,
            position=9,
            is_homeland=False,
        )

        form = SendFleetForm(
            data={
                "mission_type": Fleet.MissionType.COLONIZE,
                "target_coordinates": target_planet.coordinates,
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
