from django.test import TestCase
from django.utils import timezone

from apps.game.models import Fleet, FleetShip
from apps.game.domain_services.fleet import send_transport_fleet, process_fleets_for_user
from apps.game.domain.exceptions import (
    CargoCapacityExceededError,
    NotEnoughResourcesError,
    NotEnoughTransportersError,
    SamePlanetTransportError,
)
from .helpers import PlanetTestMixin


class SendTransportFleetTests(PlanetTestMixin, TestCase):
    def test_send_transport_fleet_creates_fleet_and_spends_resources(self):
        user = self.create_user("fleet1")
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
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        fleet = send_transport_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=3,
            metal=1000,
            crystal=500,
            user=user,
        )

        source_planet.refresh_from_db()

        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 7)
        self.assertEqual(source_planet.metal, 4000)
        self.assertEqual(source_planet.crystal, 2500)

        self.assertEqual(fleet.owner, user)
        self.assertEqual(fleet.source_planet, source_planet)
        self.assertEqual(fleet.target_planet, target_planet)
        self.assertEqual(
            self.get_fleet_ship_quantity(fleet, "transporter"),
            3,
        )
        self.assertEqual(fleet.mission_type, Fleet.MissionType.TRANSPORT)
        self.assertEqual(fleet.metal, 1000)
        self.assertEqual(fleet.crystal, 500)
        self.assertEqual(fleet.status, Fleet.Status.OUTBOUND)
        self.assertIsNotNone(fleet.departure_time)
        self.assertIsNotNone(fleet.arrival_time)
        self.assertIsNotNone(fleet.return_time)

    def test_send_transport_fleet_raises_for_same_source_and_target_planet(self):
        user = self.create_user("fleet2")

        planet = self.create_planet(
            owner=user,
            name="Earth",
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
        )

        with self.assertRaises(SamePlanetTransportError) as ctx:
            send_transport_fleet(
                source_planet=planet,
                target_planet=planet,
                transporter_count=3,
                metal=1000,
                crystal=500,
                user=user,
            )

        planet.refresh_from_db()

        self.assertEqual(str(ctx.exception), "Nie można wysłać floty na tę samą planetę.")
        self.assertEqual(self.get_planet_ship_quantity(planet, "transporter"), 10)
        self.assertEqual(planet.metal, 5000)
        self.assertEqual(planet.crystal, 3000)
        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_transport_fleet_raises_when_not_enough_transporters(self):
        user = self.create_user("fleet3")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=2,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=False,
        )

        with self.assertRaises(NotEnoughTransportersError) as ctx:
            send_transport_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                transporter_count=3,
                metal=1000,
                crystal=500,
                user=user,
            )

        source_planet.refresh_from_db()

        self.assertEqual(str(ctx.exception), "Nie masz wystarczającej liczby transportowców.")
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 2)
        self.assertEqual(source_planet.metal, 5000)
        self.assertEqual(source_planet.crystal, 3000)
        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_transport_fleet_raises_when_not_enough_resources(self):
        user = self.create_user("fleet4")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            metal=100,
            crystal=50,
            helion=500,
            transporter_count=10,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=False,
        )

        with self.assertRaises(NotEnoughResourcesError) as ctx:
            send_transport_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                transporter_count=2,
                metal=500,
                crystal=200,
                user=user,
            )

        source_planet.refresh_from_db()

        self.assertEqual(str(ctx.exception), "Nie masz wystarczających zasobów.")
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 10)
        self.assertEqual(source_planet.metal, 100)
        self.assertEqual(source_planet.crystal, 50)
        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_transport_fleet_raises_when_cargo_exceeds_capacity(self):
        user = self.create_user("fleet5")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            metal=10000,
            crystal=10000,
            helion=500,
            transporter_count=1,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            is_homeland=False,
        )

        with self.assertRaises(CargoCapacityExceededError) as ctx:
            send_transport_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                transporter_count=1,
                metal=900,
                crystal=200,
                user=user,
            )

        source_planet.refresh_from_db()

        self.assertEqual(str(ctx.exception), "Ładunek nie mieści się w pojemności floty.")
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 1)
        self.assertEqual(source_planet.metal, 10000)
        self.assertEqual(source_planet.crystal, 10000)
        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_transport_fleet_uses_fleet_composition_for_cargo_capacity(self):
        user = self.create_user("fleet_capacity_regression")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=10000,
            crystal=10000,
            helion=500,
            transporter_count=2,
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

        fleet = send_transport_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=2,
            metal=1500,
            crystal=500,
            user=user,
        )

        self.assertEqual(fleet.metal, 1500)
        self.assertEqual(fleet.crystal, 500)


class ProcessFleetsForUserTests(PlanetTestMixin, TestCase):
    def test_process_fleets_for_user_delivers_resources_to_target_and_sets_returning_status(self):
        user = self.create_user("process1")

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
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=1,
            system=2,
            position=2,
            metal=100,
            crystal=50,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=start_time,

            # Ważne: wyłączamy produkcję, bo ten test dotyczy floty, a nie naliczania zasobów.
            metal_mine_level=0,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )

        fleet = Fleet.objects.create(
            owner=user,
            source_planet=source_planet,
            target_planet=target_planet,
            mission_type=Fleet.MissionType.TRANSPORT,
            metal=1000,
            crystal=500,
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

        process_fleets_for_user(user, at=process_time)

        fleet.refresh_from_db()
        target_planet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(target_planet.metal, 1100)
        self.assertEqual(target_planet.crystal, 550)

        # W nowej chronologii planeta docelowa została przesunięta tylko
        # do momentu przylotu floty. Dalsze przesunięcie do process_time
        # robi później advance_planet_state() przy wejściu na planetę.
        self.assertEqual(target_planet.last_resource_update, arrival_time)

        self.assertEqual(fleet.status, Fleet.Status.RETURNING)
        self.assertEqual(fleet.metal, 0)
        self.assertEqual(fleet.crystal, 0)

        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"),7)

    def test_process_fleets_for_user_returns_transporters_to_source_and_completes_fleet(self):
        user = self.create_user("process2")

        start_time = timezone.now()
        arrival_time = start_time + timezone.timedelta(minutes=30)
        return_time = start_time + timezone.timedelta(hours=1)
        process_time = start_time + timezone.timedelta(hours=2)

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

            # Test dotyczy powrotu statków, nie produkcji.
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
            transporter_count=0,
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
            departure_time=start_time,
            arrival_time=arrival_time,
            return_time=return_time,
        )

        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=3,
        )

        process_fleets_for_user(user, at=process_time)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"),10)

        # W nowej chronologii źródłowa planeta jest przesunięta do return_time,
        # nie do process_time.
        self.assertEqual(source_planet.last_resource_update, return_time)

    def test_process_fleets_for_user_does_nothing_for_outbound_fleet_that_has_not_arrived_yet(self):
        user = self.create_user("process3")
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
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        fleet = Fleet.objects.create(
            owner=user,
            source_planet=source_planet,
            target_planet=target_planet,
            mission_type=Fleet.MissionType.TRANSPORT,
            metal=1000,
            crystal=500,
            status=Fleet.Status.OUTBOUND,
            departure_time=now - timezone.timedelta(seconds=10),
            arrival_time=now + timezone.timedelta(minutes=1),
            return_time=now + timezone.timedelta(minutes=2),
        )

        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=3,
        )

        process_fleets_for_user(user, at=now)

        fleet.refresh_from_db()
        target_planet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.OUTBOUND)
        self.assertEqual(fleet.metal, 1000)
        self.assertEqual(fleet.crystal, 500)
        self.assertEqual(target_planet.metal, 100)
        self.assertEqual(target_planet.crystal, 50)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 7)

    def test_process_fleets_for_user_does_nothing_for_returning_fleet_that_has_not_returned_yet(self):
        user = self.create_user("process4")
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
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        fleet = Fleet.objects.create(
            owner=user,
            source_planet=source_planet,
            target_planet=target_planet,
            mission_type=Fleet.MissionType.TRANSPORT,
            metal=0,
            crystal=0,
            status=Fleet.Status.RETURNING,
            departure_time=now - timezone.timedelta(minutes=4),
            arrival_time=now - timezone.timedelta(minutes=2),
            return_time=now + timezone.timedelta(minutes=1),
        )

        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=3,
        )

        process_fleets_for_user(user, at=now)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.RETURNING)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 7)
