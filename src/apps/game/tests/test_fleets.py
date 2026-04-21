from django.test import TestCase
from django.utils import timezone

from apps.game.models import Fleet
from apps.game.domain_services.fleet import send_transport_fleet, process_fleets_for_user
from .helpers import PlanetTestMixin


class SendTransportFleetTests(PlanetTestMixin, TestCase):
    def test_send_transport_fleet_creates_fleet_and_spends_resources(self):
        user = self.create_user("fleet1")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            x=1,
            y=1,
            metal=5000,
            crystal=3000,
            transporter_count=10,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=2,
            y=2,
            metal=100,
            crystal=50,
            transporter_count=0,
            is_homeland=False,
        )

        success, message = send_transport_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=3,
            metal=1000,
            crystal=500,
            user=user,
        )

        source_planet.refresh_from_db()

        self.assertTrue(success)
        self.assertIn("Wysłano flotę", message)
        self.assertEqual(source_planet.transporter_count, 7)
        self.assertEqual(source_planet.metal, 4000)
        self.assertEqual(source_planet.crystal, 2500)

        fleet = Fleet.objects.get()
        self.assertEqual(fleet.owner, user)
        self.assertEqual(fleet.source_planet, source_planet)
        self.assertEqual(fleet.target_planet, target_planet)
        self.assertEqual(fleet.transporter_count, 3)
        self.assertEqual(fleet.metal, 1000)
        self.assertEqual(fleet.crystal, 500)
        self.assertEqual(fleet.status, Fleet.Status.OUTBOUND)
        self.assertIsNotNone(fleet.departure_time)
        self.assertIsNotNone(fleet.arrival_time)
        self.assertIsNotNone(fleet.return_time)

    def test_send_transport_fleet_returns_error_for_same_source_and_target_planet(self):
        user = self.create_user("fleet2")

        planet = self.create_planet(
            owner=user,
            name="Earth",
            metal=5000,
            crystal=3000,
            transporter_count=10,
        )

        success, message = send_transport_fleet(
            source_planet=planet,
            target_planet=planet,
            transporter_count=3,
            metal=1000,
            crystal=500,
            user=user,
        )

        planet.refresh_from_db()

        self.assertFalse(success)
        self.assertEqual(message, "Nie można wysłać floty na tę samą planetę.")
        self.assertEqual(planet.transporter_count, 10)
        self.assertEqual(planet.metal, 5000)
        self.assertEqual(planet.crystal, 3000)
        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_transport_fleet_returns_error_when_not_enough_transporters(self):
        user = self.create_user("fleet3")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            metal=5000,
            crystal=3000,
            transporter_count=2,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=2,
            y=2,
            is_homeland=False,
        )

        success, message = send_transport_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=3,
            metal=1000,
            crystal=500,
            user=user,
        )

        source_planet.refresh_from_db()

        self.assertFalse(success)
        self.assertEqual(message, "Nie masz wystarczającej liczby transportowców.")
        self.assertEqual(source_planet.transporter_count, 2)
        self.assertEqual(source_planet.metal, 5000)
        self.assertEqual(source_planet.crystal, 3000)
        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_transport_fleet_returns_error_when_cargo_exceeds_capacity(self):
        user = self.create_user("fleet4")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            metal=10000,
            crystal=10000,
            transporter_count=1,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=2,
            y=2,
            is_homeland=False,
        )

        success, message = send_transport_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=1,
            metal=900,
            crystal=200,  # razem 1100 > capacity 1000
            user=user,
        )

        source_planet.refresh_from_db()

        self.assertFalse(success)
        self.assertEqual(message, "Ładunek nie mieści się w pojemności transportowców.")
        self.assertEqual(source_planet.transporter_count, 1)
        self.assertEqual(source_planet.metal, 10000)
        self.assertEqual(source_planet.crystal, 10000)
        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_transport_fleet_returns_error_when_not_enough_resources(self):
        user = self.create_user("fleet5")

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            metal=100,
            crystal=50,
            transporter_count=10,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=2,
            y=2,
            is_homeland=False,
        )

        success, message = send_transport_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=2,
            metal=500,
            crystal=200,
            user=user,
        )

        source_planet.refresh_from_db()

        self.assertFalse(success)
        self.assertEqual(message, "Nie masz wystarczających zasobów.")
        self.assertEqual(source_planet.transporter_count, 10)
        self.assertEqual(source_planet.metal, 100)
        self.assertEqual(source_planet.crystal, 50)
        self.assertEqual(Fleet.objects.count(), 0)

class ProcessFleetsForUserTests(PlanetTestMixin, TestCase):
    def test_process_fleets_for_user_delivers_resources_to_target_and_sets_returning_status(self):
        user = self.create_user("process1")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            x=1,
            y=1,
            metal=5000,
            crystal=3000,
            transporter_count=7,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=2,
            y=2,
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
            transporter_count=3,
            metal=1000,
            crystal=500,
            status=Fleet.Status.OUTBOUND,
            departure_time=now - timezone.timedelta(minutes=2),
            arrival_time=now - timezone.timedelta(seconds=1),
            return_time=now + timezone.timedelta(minutes=1),
        )

        process_fleets_for_user(user, at=now)

        fleet.refresh_from_db()
        target_planet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(target_planet.metal, 1100)
        self.assertEqual(target_planet.crystal, 550)
        self.assertEqual(fleet.status, Fleet.Status.RETURNING)
        self.assertEqual(fleet.metal, 0)
        self.assertEqual(fleet.crystal, 0)

        # Transportowce jeszcze nie wróciły
        self.assertEqual(source_planet.transporter_count, 7)

    def test_process_fleets_for_user_returns_transporters_to_source_and_completes_fleet(self):
        user = self.create_user("process2")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            x=1,
            y=1,
            metal=5000,
            crystal=3000,
            transporter_count=7,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=2,
            y=2,
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
            transporter_count=3,
            metal=0,
            crystal=0,
            status=Fleet.Status.RETURNING,
            departure_time=now - timezone.timedelta(minutes=4),
            arrival_time=now - timezone.timedelta(minutes=2),
            return_time=now - timezone.timedelta(seconds=1),
        )

        process_fleets_for_user(user, at=now)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertEqual(source_planet.transporter_count, 10)

    def test_process_fleets_for_user_does_nothing_for_outbound_fleet_that_has_not_arrived_yet(self):
        user = self.create_user("process3")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            x=1,
            y=1,
            metal=5000,
            crystal=3000,
            transporter_count=7,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=2,
            y=2,
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
            transporter_count=3,
            metal=1000,
            crystal=500,
            status=Fleet.Status.OUTBOUND,
            departure_time=now - timezone.timedelta(seconds=10),
            arrival_time=now + timezone.timedelta(minutes=1),
            return_time=now + timezone.timedelta(minutes=2),
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
        self.assertEqual(source_planet.transporter_count, 7)

    def test_process_fleets_for_user_does_nothing_for_returning_fleet_that_has_not_returned_yet(self):
        user = self.create_user("process4")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            x=1,
            y=1,
            metal=5000,
            crystal=3000,
            transporter_count=7,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            x=2,
            y=2,
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
            transporter_count=3,
            metal=0,
            crystal=0,
            status=Fleet.Status.RETURNING,
            departure_time=now - timezone.timedelta(minutes=4),
            arrival_time=now - timezone.timedelta(minutes=2),
            return_time=now + timezone.timedelta(minutes=1),
        )

        process_fleets_for_user(user, at=now)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.RETURNING)
        self.assertEqual(source_planet.transporter_count, 7)
