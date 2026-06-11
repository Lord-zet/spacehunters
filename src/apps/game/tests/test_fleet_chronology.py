from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.fleet import process_fleets_for_user
from apps.game.models import Fleet, FleetShip

from .helpers import PlanetTestMixin


class FleetChronologyTests(PlanetTestMixin, TestCase):
    def test_transport_arrival_is_processed_at_arrival_time(self):
        user = self.create_user("fleet_chrono_1")

        start_time = timezone.now()
        arrival_time = start_time + timezone.timedelta(minutes=30)
        target_time = start_time + timezone.timedelta(hours=1)

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
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            metal=4990,
            crystal=0,
            metal_mine_level=5,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=0,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=start_time,
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
            return_time=target_time + timezone.timedelta(minutes=30),
        )

        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=3,
        )

        process_fleets_for_user(
            user,
            at=target_time,
        )

        fleet.refresh_from_db()
        target_planet.refresh_from_db()

        self.assertEqual(
            fleet.status,
            Fleet.Status.RETURNING,
        )
        self.assertEqual(
            fleet.metal,
            0,
        )

        # Planeta miała 4990 metalu i magazyn poziomu 0, czyli capacity 5000.
        # Do arrival_time może dobić tylko do 5000.
        # W arrival_time dostaje +100 transportu, czyli ma 5100.
        # Po arrival_time produkcja nie zwiększa zasobów, bo planeta jest
        # powyżej pojemności magazynu.
        self.assertEqual(
            target_planet.metal,
            5100,
        )
        self.assertEqual(
            target_planet.last_resource_update,
            arrival_time,
        )

    def test_planet_can_advance_after_transport_arrival(self):
        from apps.game.domain_services.sync import advance_planet_state

        user = self.create_user("fleet_chrono_2")

        start_time = timezone.now()
        arrival_time = start_time + timezone.timedelta(minutes=30)
        target_time = start_time + timezone.timedelta(hours=1)

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
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            metal=4990,
            crystal=0,
            metal_mine_level=5,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=0,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=start_time,
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
            return_time=target_time + timezone.timedelta(minutes=30),
        )

        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=3,
        )

        process_fleets_for_user(
            user,
            at=target_time,
        )

        result = advance_planet_state(
            target_planet,
            at=target_time,
        )

        refreshed_planet = result.planet

        self.assertEqual(
            refreshed_planet.metal,
            5100,
        )
        self.assertEqual(
            refreshed_planet.last_resource_update,
            target_time,
        )

    def test_returning_fleet_is_processed_at_return_time(self):
        user = self.create_user("fleet_chrono_3")

        start_time = timezone.now()
        return_time = start_time + timezone.timedelta(minutes=30)
        target_time = start_time + timezone.timedelta(hours=1)

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=500,
            crystal=0,
            metal_mine_level=5,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
            metal_storage_level=10,
            transporter_count=7,
            last_resource_update=start_time,
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

        process_fleets_for_user(
            user,
            at=target_time,
        )

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(
            fleet.status,
            Fleet.Status.COMPLETED,
        )
        self.assertEqual(
            self.get_planet_ship_quantity(
                source_planet,
                "transporter",
            ),
            10,
        )
        self.assertEqual(
            source_planet.last_resource_update,
            return_time,
        )

    def test_fleet_events_are_processed_in_chronological_order(self):
        user = self.create_user("fleet_chrono_4")

        start_time = timezone.now()
        first_event_time = start_time + timezone.timedelta(minutes=20)
        second_event_time = start_time + timezone.timedelta(minutes=40)
        target_time = start_time + timezone.timedelta(hours=1)

        planet_a = self.create_planet(
            owner=user,
            name="A",
            galaxy=1,
            system=1,
            position=1,
            transporter_count=5,
            last_resource_update=start_time,
        )

        planet_b = self.create_planet(
            owner=user,
            name="B",
            galaxy=1,
            system=1,
            position=2,
            is_homeland=False,
            transporter_count=0,
            last_resource_update=start_time,
        )

        returning_fleet = Fleet.objects.create(
            owner=user,
            source_planet=planet_a,
            target_planet=planet_b,
            mission_type=Fleet.MissionType.TRANSPORT,
            metal=0,
            crystal=0,
            status=Fleet.Status.RETURNING,
            departure_time=start_time - timezone.timedelta(hours=1),
            arrival_time=start_time - timezone.timedelta(minutes=30),
            return_time=first_event_time,
        )

        FleetShip.objects.create(
            fleet=returning_fleet,
            ship_code="transporter",
            quantity=2,
        )

        outbound_fleet = Fleet.objects.create(
            owner=user,
            source_planet=planet_a,
            target_planet=planet_b,
            mission_type=Fleet.MissionType.TRANSPORT,
            metal=100,
            crystal=0,
            status=Fleet.Status.OUTBOUND,
            departure_time=start_time,
            arrival_time=second_event_time,
            return_time=target_time + timezone.timedelta(minutes=30),
        )

        FleetShip.objects.create(
            fleet=outbound_fleet,
            ship_code="transporter",
            quantity=1,
        )

        process_fleets_for_user(
            user,
            at=target_time,
        )

        returning_fleet.refresh_from_db()
        outbound_fleet.refresh_from_db()
        planet_a.refresh_from_db()
        planet_b.refresh_from_db()

        self.assertEqual(
            returning_fleet.status,
            Fleet.Status.COMPLETED,
        )
        self.assertEqual(
            outbound_fleet.status,
            Fleet.Status.RETURNING,
        )
        self.assertEqual(
            planet_a.last_resource_update,
            first_event_time,
        )
        self.assertEqual(
            planet_b.last_resource_update,
            second_event_time,
        )
