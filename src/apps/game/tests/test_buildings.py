from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.game.models import Planet
from apps.game.domain_services.buildings  import start_building_upgrade, get_upgrade_cost


class PlanetTestMixin:
    def create_user(self, username="tester"):
        User = get_user_model()
        return User.objects.create_user(username=username, password="secret")

    def create_planet(self, owner=None, last_resource_update=None, **overrides):
        if owner is None:
            owner = self.create_user()

        data = {
            "owner": owner,
            "name": "Test Planet",
            "x": 1,
            "y": 1,
            "metal": 500,
            "crystal": 200,
            "metal_mine_level": 2,
            "crystal_mine_level": 1,
            "metal_storage_level": 10,
            "crystal_storage_level": 10,
            "is_homeland": True,
            "building_type": "",
            "building_ends_at": None,
            "transporter_count": 0,
        }
        data.update(overrides)

        planet = Planet.objects.create(**data)

        if last_resource_update is not None:
            Planet.objects.filter(pk=planet.pk).update(
                last_resource_update=last_resource_update
            )
            planet.refresh_from_db()

        return planet


class StartBuildingUpgradeTests(PlanetTestMixin, TestCase):
    def test_start_building_upgrade_starts_construction_and_spends_resources(self):
        user = self.create_user("builder1")
        start_time = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=start_time,
            name="Earth",
            metal=10000,
            crystal=10000,
            metal_mine_level=1,
            crystal_mine_level=0,
        )

        building_name = "metal_mine"
        cost = get_upgrade_cost(planet, building_name)

        success, message = start_building_upgrade(
            planet,
            building_name,
            at=start_time,
        )

        planet.refresh_from_db()

        self.assertTrue(success)
        self.assertIn("Rozpoczęto rozbudowę", message)
        self.assertEqual(planet.building_type, building_name)
        self.assertIsNotNone(planet.building_ends_at)
        self.assertGreater(planet.building_ends_at, start_time)
        self.assertEqual(planet.metal, 10000 - cost["metal"])

    def test_start_building_upgrade_returns_error_when_construction_is_already_in_progress(self):
        user = self.create_user("builder2")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            name="Mars",
            metal=10000,
            crystal=10000,
            building_type="metal_mine",
            building_ends_at=now + timezone.timedelta(minutes=10),
        )

        old_metal = planet.metal
        old_crystal = planet.crystal
        old_building_type = planet.building_type
        old_building_ends_at = planet.building_ends_at

        success, message = start_building_upgrade(
            planet,
            "crystal_mine",
            at=now,
        )

        planet.refresh_from_db()

        self.assertFalse(success)
        self.assertEqual(message, "Na tej planecie trwa już budowa.")
        self.assertEqual(planet.metal, old_metal)
        self.assertEqual(planet.crystal, old_crystal)
        self.assertEqual(planet.building_type, old_building_type)
        self.assertEqual(planet.building_ends_at, old_building_ends_at)

    def test_start_building_upgrade_returns_error_when_not_enough_resources(self):
        user = self.create_user("builder3")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            name="Venus",
            metal=0,
            crystal=0,
            metal_mine_level=1,
            crystal_mine_level=0,
        )

        success, message = start_building_upgrade(
            planet,
            "metal_mine",
            at=now,
        )

        planet.refresh_from_db()

        self.assertFalse(success)
        self.assertEqual(message, "Za mało surowców.")
        self.assertEqual(planet.building_type, "")
        self.assertIsNone(planet.building_ends_at)
        self.assertEqual(planet.metal, 0)
        self.assertEqual(planet.crystal, 0)

    def test_start_building_upgrade_returns_error_for_unknown_building(self):
        user = self.create_user("builder4")
        now = timezone.now()

        planet = self.create_planet(
            owner=user,
            last_resource_update=now,
            name="Jupiter",
            metal=10000,
            crystal=10000,
        )

        success, message = start_building_upgrade(
            planet,
            "unknown_building",
            at=now,
        )

        planet.refresh_from_db()

        self.assertFalse(success)
        self.assertEqual(message, "Nieznany budynek.")
        self.assertEqual(planet.building_type, "")
        self.assertIsNone(planet.building_ends_at)
