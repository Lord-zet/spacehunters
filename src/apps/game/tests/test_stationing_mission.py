from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import InvalidStationingTargetError
from apps.game.domain_services.fleet import send_stationing_fleet, process_fleets_for_user
from apps.game.domain_services.resources import Resource
from apps.game.models import Fleet, FleetShip
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
            cargo={
                Resource.METAL: 1000,
                Resource.CRYSTAL: 500,
                Resource.HELION: 0,
            },
            user=user,
        )

        self.assertEqual(fleet.mission_type, Fleet.MissionType.STATION)
        self.assertEqual(fleet.status, Fleet.Status.OUTBOUND)
        self.assertIsNone(fleet.return_time)

    def test_process_fleets_for_user_completes_stationing_and_leaves_ships_on_target(self):
        user = self.create_user("station2")

        start_time = timezone.now()
        arrival_time = start_time + timezone.timedelta(minutes=30)
        process_time = start_time + timezone.timedelta(hours=1)

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=4,
            last_resource_update=start_time,
            metal_mine_level=0,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
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
            last_resource_update=start_time,
            metal_mine_level=0,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )

        fleet = Fleet.objects.create(
            owner=user,
            source_planet=source_planet,
            target_planet=target_planet,
            mission_type=Fleet.MissionType.STATION,
            metal=1000,
            crystal=500,
            status=Fleet.Status.OUTBOUND,
            departure_time=start_time,
            arrival_time=arrival_time,
            return_time=None,
        )

        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=3,
        )

        process_fleets_for_user(user, at=process_time)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()
        target_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertIsNone(fleet.return_time)
        self.assertEqual(target_planet.metal, 1100)
        self.assertEqual(target_planet.crystal, 550)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"),4)
        self.assertEqual(self.get_planet_ship_quantity(target_planet, "transporter"),3)
        self.assertEqual(target_planet.last_resource_update, arrival_time)

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
                cargo={
                    Resource.METAL: 1000,
                    Resource.CRYSTAL: 500,
                    Resource.HELION: 0,
                },
                user=user1,
            )

        self.assertEqual(
            str(ctx.exception),
            "Misja stacjonowania jest możliwa tylko na własną planetę.",
        )
