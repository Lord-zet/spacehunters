from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.game.domain.world import Coordinates
from apps.game.models import Fleet, FleetShip

from .helpers import PlanetTestMixin


class NullableFleetTargetViewTests(PlanetTestMixin, TestCase):
    def test_planet_detail_renders_active_fleet_without_target_planet(self):
        user = self.create_user("nullable_target_dashboard_user")
        now = timezone.now()
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            last_resource_update=now,
        )
        fleet = self.create_fleet_without_target_planet(
            owner=user,
            source_planet=source_planet,
            now=now,
        )

        self.client.force_login(user)

        response = self.client.get(
            reverse("game:planet_detail", kwargs={"pk": source_planet.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(fleet.target_coordinates))

    def test_fleet_list_renders_fleet_without_target_planet(self):
        user = self.create_user("nullable_target_fleet_list_user")
        now = timezone.now()
        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            last_resource_update=now,
        )
        fleet = self.create_fleet_without_target_planet(
            owner=user,
            source_planet=source_planet,
            now=now,
        )

        self.client.force_login(user)

        response = self.client.get(
            reverse("game:fleet_list", kwargs={"pk": source_planet.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(fleet.target_coordinates))

    def create_fleet_without_target_planet(self, *, owner, source_planet, now):
        fleet = Fleet.objects.create(
            owner=owner,
            source_planet=source_planet,
            target_planet=None,
            **Fleet.target_coordinate_fields(
                Coordinates(galaxy=1, system=99, position=9)
            ),
            mission_type=Fleet.MissionType.COLONIZE,
            status=Fleet.Status.OUTBOUND,
            departure_time=now,
            arrival_time=now + timezone.timedelta(days=1),
            return_time=None,
        )
        FleetShip.objects.create(
            fleet=fleet,
            ship_code="transporter",
            quantity=1,
        )
        return fleet
