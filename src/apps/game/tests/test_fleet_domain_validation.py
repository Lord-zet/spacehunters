from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import (
    FleetError,
    NotEnoughTransportersError,
    PlanetOwnershipError,
    UnknownShipError,
    UnsupportedFleetMissionError,
)
from apps.game.domain_services.fleet import (
    _send_fleet_mission,
    send_transport_fleet,
)
from apps.game.models import Fleet

from .helpers import PlanetTestMixin


class FleetDomainValidationTests(PlanetTestMixin, TestCase):
    def test_send_fleet_rejects_source_planet_owned_by_other_user(self):
        user = self.create_user("fleet_owner_1")
        other_user = self.create_user("fleet_owner_2")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=other_user,
            name="Other",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mine",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=True,
            last_resource_update=now,
        )

        with self.assertRaises(PlanetOwnershipError):
            send_transport_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                transporter_count=1,
                metal=100,
                crystal=0,
                user=user,
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_unsupported_mission_type(self):
        user = self.create_user("fleet_mission_1")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(UnsupportedFleetMissionError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={"transporter": 1},
                metal=100,
                crystal=0,
                user=user,
                mission_type="unsupported",
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_unknown_ship_code(self):
        user = self.create_user("fleet_ship_1")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(UnknownShipError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={"ghost_ship": 1},
                metal=100,
                crystal=0,
                user=user,
                mission_type=Fleet.MissionType.TRANSPORT,
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_empty_ship_payload(self):
        user = self.create_user("fleet_ship_2")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(FleetError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={},
                metal=100,
                crystal=0,
                user=user,
                mission_type=Fleet.MissionType.TRANSPORT,
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_negative_ship_quantity(self):
        user = self.create_user("fleet_ship_3")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(FleetError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={"transporter": -1},
                metal=100,
                crystal=0,
                user=user,
                mission_type=Fleet.MissionType.TRANSPORT,
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_zero_total_ship_quantity(self):
        user = self.create_user("fleet_ship_4")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(FleetError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={"transporter": 0},
                metal=100,
                crystal=0,
                user=user,
                mission_type=Fleet.MissionType.TRANSPORT,
            )

        self.assertEqual(Fleet.objects.count(), 0)
