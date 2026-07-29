from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.fleet import send_transport_fleet

from .helpers import PlanetTestMixin
from apps.game.domain_services.resources import Resource


class FleetSpeedProfileMissionTests(PlanetTestMixin, TestCase):
    def test_transport_fleet_stores_selected_speed_profile(self):
        now = timezone.now()
        user = self.create_user("speed_profile_user")

        source = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            helion=10_000,
            transporter_count=1,
            last_resource_update=now,
        )
        target = self.create_planet(
            owner=user,
            name="Target",
            galaxy=1,
            system=2,
            position=1,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        fleet = send_transport_fleet(
            user=user,
            source_planet=source,
            target_planet=target,
            transporter_count=1,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            speed_profile="fast",
        )

        self.assertEqual(fleet.speed_profile, "fast")

    def test_fast_profile_arrives_before_standard_profile(self):
        now = timezone.now()
        user = self.create_user("fast_profile_user")

        source = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            helion=100_000,
            transporter_count=2,
            last_resource_update=now,
        )
        target = self.create_planet(
            owner=user,
            name="Target",
            galaxy=1,
            system=5,
            position=1,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        standard_fleet = send_transport_fleet(
            user=user,
            source_planet=source,
            target_planet=target,
            transporter_count=1,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            speed_profile="standard",
        )

        fast_fleet = send_transport_fleet(
            user=user,
            source_planet=source,
            target_planet=target,
            transporter_count=1,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            speed_profile="fast",
        )

        self.assertLess(fast_fleet.arrival_time, standard_fleet.arrival_time)

    def test_fast_profile_costs_more_helion_than_standard_profile(self):
        now = timezone.now()
        user = self.create_user("fuel_profile_user")

        source = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            helion=100_000,
            transporter_count=2,
            last_resource_update=now,
        )
        target = self.create_planet(
            owner=user,
            name="Target",
            galaxy=1,
            system=5,
            position=1,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        standard_fleet = send_transport_fleet(
            user=user,
            source_planet=source,
            target_planet=target,
            transporter_count=1,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            speed_profile="standard",
        )

        fast_fleet = send_transport_fleet(
            user=user,
            source_planet=source,
            target_planet=target,
            transporter_count=1,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            speed_profile="fast",
        )

        self.assertGreater(fast_fleet.helion_cost, standard_fleet.helion_cost)

    def test_economy_profile_arrives_later_and_costs_less_than_standard(self):
        now = timezone.now()
        user = self.create_user("economy_profile_user")

        source = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            helion=100_000,
            transporter_count=2,
            last_resource_update=now,
        )
        target = self.create_planet(
            owner=user,
            name="Target",
            galaxy=1,
            system=5,
            position=1,
            transporter_count=0,
            is_homeland=False,
            last_resource_update=now,
        )

        standard_fleet = send_transport_fleet(
            user=user,
            source_planet=source,
            target_planet=target,
            transporter_count=1,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            speed_profile="standard",
        )

        economy_fleet = send_transport_fleet(
            user=user,
            source_planet=source,
            target_planet=target,
            transporter_count=1,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            speed_profile="economy",
        )

        self.assertGreater(economy_fleet.arrival_time, standard_fleet.arrival_time)
        self.assertLess(economy_fleet.helion_cost, standard_fleet.helion_cost)
