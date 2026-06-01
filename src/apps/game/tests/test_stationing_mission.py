from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import InvalidStationingTargetError
from apps.game.domain_services.fleet import send_stationing_fleet, process_fleets_for_user
from apps.game.models import Fleet
from .helpers import PlanetTestMixin


class StationingMissionTests(PlanetTestMixin, TestCase):
    def test_send_stationing_fleet_creates_outbound_station_mission_without_return_time(self):
        user = self.create_user("station1")
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
            metal=100,
            crystal=50,
            helion=0,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        fleet = send_stationing_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=3,
            metal=1000,
            crystal=500,
            user=user,
        )

        self.assertEqual(fleet.mission_type, Fleet.MissionType.STATION)
        self.assertEqual(fleet.status, Fleet.Status.OUTBOUND)
        self.assertIsNone(fleet.return_time)

    def test_process_fleets_for_user_completes_stationing_and_leaves_ships_on_target(self):
        user = self.create_user("station2")
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
            transporter_count=7,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            metal=100,
            crystal=50,
            helion=0,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        fleet = send_stationing_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=3,
            metal=1000,
            crystal=500,
            user=user,
        )

        Fleet.objects.filter(pk=fleet.pk).update(
            arrival_time=now - timezone.timedelta(seconds=1),
        )
        fleet.refresh_from_db()

        process_fleets_for_user(user, at=now)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()
        target_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertEqual(target_planet.metal, 1100)
        self.assertEqual(target_planet.crystal, 550)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 4)
        self.assertEqual(self.get_planet_ship_quantity(target_planet, "transporter"), 3)

    def test_send_stationing_fleet_raises_for_target_owned_by_other_user(self):
        user1 = self.create_user("station3")
        user2 = self.create_user("station4")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user1,
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
            owner=user2,
            name="Enemy",
            galaxy=1,
            system=2,
            position=2,
            metal=100,
            crystal=50,
            helion=0,
            transporter_count=0,
            is_homeland=True,
            last_resource_update=now,
        )

        with self.assertRaises(InvalidStationingTargetError) as ctx:
            send_stationing_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                transporter_count=3,
                metal=1000,
                crystal=500,
                user=user1,
            )

        self.assertEqual(
            str(ctx.exception),
            "Misja stacjonowania jest możliwa tylko na własną planetę.",
        )
