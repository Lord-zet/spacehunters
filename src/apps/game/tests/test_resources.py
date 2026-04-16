from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.game.models import Planet
from apps.game.domain_services.resources import synchronize_resources, get_production_per_hour, get_storage_capacity


class SynchronizeResourcesTests(TestCase):
    def test_synchronize_resources_adds_resources_for_elapsed_time(self):
        User = get_user_model()
        user = User.objects.create_user(username="tester", password="secret")

        start_time = timezone.now()

        planet = Planet.objects.create(
            owner=user,
            name="Earth",
            x=1,
            y=1,
            metal=500,
            crystal=200,
            metal_mine_level=2,
            crystal_mine_level=1,
            metal_storage_level=10,
            crystal_storage_level=10,
            is_homeland=True,
            last_resource_update=start_time,
        )

        production = get_production_per_hour(planet)
        target_time = start_time + timezone.timedelta(hours=2)

        synchronize_resources(planet, at=target_time, save=True)

        planet.refresh_from_db()

        expected_metal_gain = int(production["metal"] * 2)
        expected_crystal_gain = int(production["crystal"] * 2)

        self.assertEqual(planet.metal, 500 + expected_metal_gain)
        self.assertEqual(planet.crystal, 200 + expected_crystal_gain)
        self.assertEqual(planet.last_resource_update, target_time)

    def test_synchronize_resources_does_not_exceed_storage_capacity(self):
        User = get_user_model()
        user = User.objects.create_user(username="tester", password="secret")

        start_time = timezone.now()

        planet = Planet.objects.create(
            owner=user,
            name="Mars",
            x=2,
            y=3,
            metal=7400,
            crystal=7300,
            metal_mine_level=20,
            crystal_mine_level=20,
            metal_storage_level=1,
            crystal_storage_level=1,
            is_homeland=True,
            last_resource_update=start_time,
        )

        metal_capacity = get_storage_capacity(planet, "metal")
        crystal_capacity = get_storage_capacity(planet, "crystal")

        target_time = start_time + timezone.timedelta(hours=24)

        synchronize_resources(planet, at=target_time, save=True)
        planet.refresh_from_db()

        self.assertEqual(planet.metal, metal_capacity)
        self.assertEqual(planet.crystal, crystal_capacity)
        self.assertEqual(planet.last_resource_update, target_time)

    def test_synchronize_resources_does_nothing_when_no_time_has_elapsed(self):
        User = get_user_model()
        user = User.objects.create_user(username="tester", password="secret")

        start_time = timezone.now()

        planet = Planet.objects.create(
            owner=user,
            name="Venus",
            x=4,
            y=5,
            metal=1200,
            crystal=800,
            metal_mine_level=3,
            crystal_mine_level=2,
            metal_storage_level=5,
            crystal_storage_level=5,
            is_homeland=True,
            last_resource_update=start_time,
        )

        synchronize_resources(planet, at=start_time, save=True)
        planet.refresh_from_db()

        self.assertEqual(planet.metal, 1200)
        self.assertEqual(planet.crystal, 800)
        self.assertEqual(planet.last_resource_update, start_time)

    def test_synchronize_resources_does_nothing_when_time_is_earlier_than_last_update(self):
        User = get_user_model()
        user = User.objects.create_user(username="tester2", password="secret")

        start_time = timezone.now()

        planet = Planet.objects.create(
            owner=user,
            name="Jupiter",
            x=6,
            y=7,
            metal=1500,
            crystal=900,
            metal_mine_level=4,
            crystal_mine_level=3,
            metal_storage_level=5,
            crystal_storage_level=5,
            is_homeland=True,
            last_resource_update=start_time,
        )

        earlier_time = start_time - timezone.timedelta(minutes=10)

        synchronize_resources(planet, at=earlier_time, save=True)
        planet.refresh_from_db()

        self.assertEqual(planet.metal, 1500)
        self.assertEqual(planet.crystal, 900)
        self.assertEqual(planet.last_resource_update, start_time)

    def test_synchronize_resources_with_save_false_updates_only_in_memory(self):
        User = get_user_model()
        user = User.objects.create_user(username="tester", password="secret")

        start_time = timezone.now()

        planet = Planet.objects.create(
            owner=user,
            name="Saturn",
            x=8,
            y=9,
            metal=500,
            crystal=200,
            metal_mine_level=2,
            crystal_mine_level=1,
            metal_storage_level=10,
            crystal_storage_level=10,
            is_homeland=True,
            last_resource_update=start_time,
        )

        production = get_production_per_hour(planet)
        target_time = start_time + timezone.timedelta(hours=2)

        synchronize_resources(planet, at=target_time, save=False)

        expected_metal_gain = int(production["metal"] * 2)
        expected_crystal_gain = int(production["crystal"] * 2)

        # Obiekt w pamięci został zmieniony
        self.assertEqual(planet.metal, 500 + expected_metal_gain)
        self.assertEqual(planet.crystal, 200 + expected_crystal_gain)
        self.assertEqual(planet.last_resource_update, target_time)

        # Rekord w bazie nadal ma stare wartości
        fresh_planet = Planet.objects.get(pk=planet.pk)
        self.assertEqual(fresh_planet.metal, 500)
        self.assertEqual(fresh_planet.crystal, 200)
        self.assertEqual(fresh_planet.last_resource_update, start_time)
