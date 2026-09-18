from django.test import TestCase
from django.utils import timezone

from apps.game.domain.exceptions import (
    FleetError,
    PlanetOwnershipError,
    UnknownShipError,
    UnsupportedFleetMissionError,
)
from apps.game.domain_services.fleet import (
    _send_fleet_mission,
    send_colonization_fleet,
    send_transport_fleet,
)
from apps.game.domain.world import Coordinates, DEFAULT_UNIVERSE_RULES
from apps.game.models import Fleet

from .helpers import PlanetTestMixin
from apps.game.domain_services.resources import Resource


class FleetDomainValidationTests(PlanetTestMixin, TestCase):
    def test_send_fleet_rejects_source_planet_owned_by_other_user(self):
        user = self.create_user("fleet_owner_1")
        other_user = self.create_user("fleet_owner_2")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=other_user,
            name="Other",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mine",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=True,
            last_resource_update=now,
        )

        with self.assertRaises(PlanetOwnershipError):
            send_transport_fleet(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities=1,
                cargo={
                    Resource.METAL: 100,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_transport_fleet_allows_target_owned_by_other_user(self):
        user = self.create_user("fleet_transport_target_owner_1")
        target_owner = self.create_user("fleet_transport_target_owner_2")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=target_owner,
            name="Foreign Target",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=True,
            last_resource_update=now,
        )

        fleet = send_transport_fleet(
            source_planet=source_planet,
            target_planet=target_planet,
            ship_quantities=1,
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            user=user,
        )

        self.assertEqual(fleet.target_planet, target_planet)
        self.assertEqual(fleet.mission_type, Fleet.MissionType.TRANSPORT)

    def test_send_fleet_resolves_existing_target_from_coordinates(self):
        user = self.create_user("fleet_coordinates_target_user")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Target",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=False,
            last_resource_update=now,
        )

        fleet = send_transport_fleet(
            source_planet=source_planet,
            target_planet=None,
            target_coordinates=target_planet.coordinates,
            ship_quantities={"transporter": 1},
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            user=user,
        )

        self.assertEqual(fleet.target_planet, target_planet)
        self.assertEqual(fleet.target_coordinates, target_planet.coordinates)

    def test_transport_fleet_rejects_empty_target_coordinates(self):
        user = self.create_user("fleet_empty_coordinates_user")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=now,
        )

        with self.assertRaises(FleetError):
            send_transport_fleet(
                source_planet=source_planet,
                target_planet=None,
                target_coordinates=Coordinates(galaxy=1, system=99, position=9),
                ship_quantities={"transporter": 1},
                cargo={
                    Resource.METAL: 0,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
            )

        self.assertEqual(Fleet.objects.count(), 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 3)

    def test_colonization_fleet_allows_empty_target_coordinates(self):
        user = self.create_user("fleet_colonization_empty_target_user")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=now,
        )

        fleet = send_colonization_fleet(
            source_planet=source_planet,
            target_coordinates=Coordinates(galaxy=1, system=99, position=9),
            ship_quantities={"transporter": 1},
            cargo={
                Resource.METAL: 0,
                Resource.CRYSTAL: 0,
                Resource.HELION: 0,
            },
            user=user,
        )

        self.assertIsNone(fleet.target_planet)
        self.assertEqual(
            fleet.target_coordinates,
            Coordinates(galaxy=1, system=99, position=9),
        )
        self.assertEqual(fleet.mission_type, Fleet.MissionType.COLONIZE)
        self.assertIsNone(fleet.return_time)

    def test_colonization_fleet_rejects_target_coordinates_outside_universe(self):
        user = self.create_user("fleet_colonization_outside_universe_user")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=now,
        )

        with self.assertRaisesMessage(FleetError, "poza granicami"):
            send_colonization_fleet(
                source_planet=source_planet,
                target_coordinates=Coordinates(galaxy=10, system=1, position=1),
                ship_quantities={"transporter": 1},
                cargo={
                    Resource.METAL: 0,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
            )

        self.assertEqual(Fleet.objects.count(), 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 3)

    def test_colonization_fleet_rejects_dispatch_when_player_reached_planet_limit(self):
        user = self.create_user("fleet_colonization_limit_user")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=now,
        )

        for index in range(2, DEFAULT_UNIVERSE_RULES.max_planets_per_player + 1):
            self.create_planet(
                owner=user,
                name=f"Colony {index}",
                coordinates=Coordinates(galaxy=1, system=index, position=1),
                is_homeland=False,
                last_resource_update=now,
            )

        with self.assertRaisesMessage(FleetError, "maksymalną liczbę planet"):
            send_colonization_fleet(
                source_planet=source_planet,
                target_coordinates=Coordinates(galaxy=1, system=99, position=9),
                ship_quantities={"transporter": 1},
                cargo={
                    Resource.METAL: 0,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
            )

        self.assertEqual(Fleet.objects.count(), 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 3)

    def test_colonization_fleet_rejects_existing_target_planet(self):
        user = self.create_user("fleet_colonization_existing_target_user")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Source",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=3,
            last_resource_update=now,
        )
        target_planet = self.create_planet(
            owner=user,
            name="Occupied",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(FleetError):
            send_colonization_fleet(
                source_planet=source_planet,
                target_coordinates=target_planet.coordinates,
                ship_quantities={"transporter": 1},
                cargo={
                    Resource.METAL: 0,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
            )

        self.assertEqual(Fleet.objects.count(), 0)
        self.assertEqual(self.get_planet_ship_quantity(source_planet, "transporter"), 3)

    def test_send_fleet_rejects_unsupported_mission_type(self):
        user = self.create_user("fleet_mission_1")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(UnsupportedFleetMissionError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={"transporter": 1},
                cargo={
                    Resource.METAL: 100,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
                mission_type="unsupported",
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_unknown_ship_code(self):
        user = self.create_user("fleet_ship_1")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(UnknownShipError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={"ghost_ship": 1},
                cargo={
                    Resource.METAL: 100,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
                mission_type=Fleet.MissionType.TRANSPORT,
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_empty_ship_payload(self):
        user = self.create_user("fleet_ship_2")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(FleetError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={},
                cargo={
                    Resource.METAL: 100,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
                mission_type=Fleet.MissionType.TRANSPORT,
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_negative_ship_quantity(self):
        user = self.create_user("fleet_ship_3")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(FleetError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={"transporter": -1},
                cargo={
                    Resource.METAL: 100,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
                mission_type=Fleet.MissionType.TRANSPORT,
            )

        self.assertEqual(Fleet.objects.count(), 0)

    def test_send_fleet_rejects_zero_total_ship_quantity(self):
        user = self.create_user("fleet_ship_4")
        now = timezone.now()

        source_planet = self.create_planet(
            owner=user,
            name="Earth",
            coordinates=Coordinates(galaxy=1, system=1, position=1),
            metal=5000,
            crystal=3000,
            helion=500,
            transporter_count=10,
            last_resource_update=now,
        )

        target_planet = self.create_planet(
            owner=user,
            name="Mars",
            coordinates=Coordinates(galaxy=1, system=2, position=2),
            is_homeland=False,
            last_resource_update=now,
        )

        with self.assertRaises(FleetError):
            _send_fleet_mission(
                source_planet=source_planet,
                target_planet=target_planet,
                ship_quantities={"transporter": 0},
                cargo={
                    Resource.METAL: 100,
                    Resource.CRYSTAL: 0,
                    Resource.HELION: 0,
                },
                user=user,
                mission_type=Fleet.MissionType.TRANSPORT,
            )

        self.assertEqual(Fleet.objects.count(), 0)
