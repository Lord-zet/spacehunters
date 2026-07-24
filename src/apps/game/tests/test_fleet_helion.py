from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import NotEnoughFuelError
from apps.game.domain_services.fleet import (
    calculate_helion_cost_for_flight,
    send_transport_fleet,
)
from apps.game.models import Fleet
from .helpers import PlanetTestMixin


class FleetHelionConsumptionTests(PlanetTestMixin, TestCase):
    def test_send_transport_fleet_deducts_helion_and_saves_cost_on_fleet(self):
        user = self.create_user("helion1")
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
            system=3,
            position=8,
            metal=100,
            crystal=50,
            helion=0,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        expected_helion_cost = calculate_helion_cost_for_flight(
            source_planet,
            target_planet,
            {"transporter": 3},
        )

        fleet = send_transport_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            transporter_count=3,
            metal=1000,
            crystal=500,
            helion=0,
            user=user,
        )

        source_planet.refresh_from_db()
        fleet.refresh_from_db()

        self.assertEqual(source_planet.helion, 500 - expected_helion_cost)
        self.assertEqual(fleet.helion_cost, expected_helion_cost)
        self.assertEqual(fleet.status, Fleet.Status.OUTBOUND)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 7)

    def test_send_transport_fleet_raises_when_not_enough_helion(self):
        user = self.create_user("helion2")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=0,
            transporter_count=10,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            galaxy=2,
            system=6,
            position=5,
            metal=100,
            crystal=50,
            helion=0,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(NotEnoughFuelError) as ctx:
            send_transport_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                transporter_count=3,
                metal=1000,
                crystal=500,
                helion=0,
                user=user,
            )

        source_planet.refresh_from_db()

        self.assertEqual(str(ctx.exception), "Nie masz wystarczającej ilości helionu na lot.")
        self.assertEqual(source_planet.helion, 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 10)
