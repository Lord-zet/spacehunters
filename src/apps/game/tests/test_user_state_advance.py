from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.sync import advance_user_state
from apps.game.models import Fleet, FleetShip

from .helpers import PlanetTestMixin


class UserStateAdvanceTests(PlanetTestMixin, TestCase):
    def test_advance_user_state_processes_fleet_before_advancing_planet_to_target_time(self):
        user = self.create_user("user_state_1")

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
            transporter_count=7,
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
            metal=4990,
            crystal=0,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=start_time,
            metal_mine_level=5,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=0,
        )

        fleet = Fleet.objects.create(
            owner=user,
            source_planet=source_planet,
            target_planet=target_planet,
            mission_type=Fleet.MissionType.TRANSPORT,
            metal=100,
            crystal=0,
            status=Fleet.Status.OUTBOUND,
            departure_time=start_time,
            arrival_time=arrival_time,
            return_time=process_time + timezone.timedelta(minutes=30),
        )

        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=3,
        )

        result = advance_user_state(user, planet=target_planet, at=process_time)

        target_planet = result.planet
        fleet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.RETURNING)
        self.assertEqual(fleet.metal, 0)

        # Chronologia:
        # start: 4990 metalu, magazyn lvl 0 = 5000 capacity
        # do arrival_time planeta dobija do 5000
        # arrival_time: flota dodaje 100, razem 5100
        # potem advance_planet_state przesuwa planetę do process_time,
        # ale produkcja nic nie dodaje, bo planeta jest ponad capacity.
        self.assertEqual(target_planet.metal, 5100)
        self.assertEqual(target_planet.last_resource_update, process_time)

    def test_advance_user_state_without_planet_processes_only_fleet_events(self):
        user = self.create_user("user_state_2")

        start_time = timezone.now()
        return_time = start_time + timezone.timedelta(minutes=30)
        process_time = start_time + timezone.timedelta(hours=1)

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            transporter_count=7,
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
            is_homeland=False,
            last_resource_update=start_time,
        )

        fleet = Fleet.objects.create(
            owner=user,
            source_planet=source_planet,
            target_planet=target_planet,
            mission_type=Fleet.MissionType.TRANSPORT,
            metal=0,
            crystal=0,
            status=Fleet.Status.RETURNING,
            departure_time=start_time - timezone.timedelta(hours=1),
            arrival_time=start_time - timezone.timedelta(minutes=30),
            return_time=return_time,
        )

        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=3,
        )

        result = advance_user_state(user, at=process_time)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertIsNone(result.planet)
        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 10)

        # Bez przekazania planety wrapper nie przesuwa jej do process_time.
        # Rozlicza tylko zdarzenie floty w return_time.
        self.assertEqual(source_planet.last_resource_update, return_time)
