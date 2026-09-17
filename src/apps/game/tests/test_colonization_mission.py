from django.test import TestCase
from django.utils import timezone

from apps.game.domain_services.fleet import (
    process_fleets_for_user,
    send_colonization_fleet,
)
from apps.game.domain.world import DEFAULT_UNIVERSE_RULES
from apps.game.domain_services.resources import Resource
from apps.game.models import Fleet, Planet

from .helpers import PlanetTestMixin


class ColonizationMissionTests(PlanetTestMixin, TestCase):
    def test_process_colonization_arrival_creates_planet_and_leaves_ships_on_target(self):
        user = self.create_user("colonization_success_user")
        start_time = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=start_time,
        )

        fleet = send_colonization_fleet(
            source_planet=source_planet,
            target_coordinates=(1, 99, 9),
            ship_quantities={"transporter": 1},
            cargo={
                Resource.METAL: 700,
                Resource.CRYSTAL: 200,
                Resource.HELION: 0,
            },
            user=user,
            at=start_time,
        )

        process_fleets_for_user(user, at=fleet.arrival_time)

        fleet.refresh_from_db()
        colony = Planet.objects.get(galaxy=1, system=99, position=9)

        self.assertEqual(colony.owner, user)
        self.assertEqual(colony.name, "Kolonia 1:99:9")
        self.assertEqual(colony.metal, 700)
        self.assertEqual(colony.crystal, 200)
        self.assertEqual(colony.helion, 0)
        self.assertEqual(self.get_planet_ship_quantity(colony, "transporter"), 1)
        self.assertEqual(fleet.target_planet, colony)
        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertIsNone(fleet.return_time)
        self.assertEqual(fleet.metal, 0)
        self.assertEqual(fleet.crystal, 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 2)

    def test_process_colonization_arrival_returns_fleet_when_target_becomes_occupied(self):
        user = self.create_user("colonization_return_user")
        other_user = self.create_user("colonization_occupier_user")
        start_time = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=start_time,
            metal_mine_level=0,
            crystal_mine_level=0,
            helion_synthesizer_level=0,
        )

        fleet = send_colonization_fleet(
            source_planet=source_planet,
            target_coordinates=(1, 99, 9),
            ship_quantities={"transporter": 1},
            cargo={
                Resource.METAL: 300,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            user=user,
            at=start_time,
        )
        occupied_planet = self.create_planet(
            owner=other_user,
            name="Occupied",
            galaxy=1,
            system=99,
            position=9,
            is_homeland=True,
            last_resource_update=start_time,
        )

        process_fleets_for_user(user, at=fleet.arrival_time)

        fleet.refresh_from_db()
        occupied_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.RETURNING)
        self.assertIsNotNone(fleet.return_time)
        self.assertIsNone(fleet.target_planet)
        self.assertEqual(fleet.metal, 300)
        self.assertEqual(self.get_planet_ship_quantity(occupied_planet, "transporter"), 0)
        self.assertEqual(Planet.objects.filter(galaxy=1, system=99, position=9).count(), 1)

        process_fleets_for_user(user, at=fleet.return_time)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertEqual(fleet.metal, 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 3)

    def test_process_colonization_arrival_returns_fleet_when_player_reaches_planet_limit(self):
        user = self.create_user("colonization_planet_limit_user")
        start_time = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            galaxy=1,
            system=1,
            position=1,
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=start_time,
        )

        fleet = send_colonization_fleet(
            source_planet=source_planet,
            target_coordinates=(1, 99, 9),
            ship_quantities={"transporter": 1},
            cargo={
                Resource.METAL: 300,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            user=user,
            at=start_time,
        )

        for index in range(2, DEFAULT_UNIVERSE_RULES.max_planets_per_player + 1):
            self.create_planet(
                owner=user,
                name=f"Colony {index}",
                galaxy=1,
                system=index,
                position=1,
                is_homeland=False,
                last_resource_update=start_time,
            )

        process_fleets_for_user(user, at=fleet.arrival_time)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.RETURNING)
        self.assertIsNone(fleet.target_planet)
        self.assertFalse(Planet.objects.filter(galaxy=1, system=99, position=9).exists())

        process_fleets_for_user(user, at=fleet.return_time)

        fleet.refresh_from_db()
        source_planet.refresh_from_db()

        self.assertEqual(fleet.status, Fleet.Status.COMPLETED)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 3)
