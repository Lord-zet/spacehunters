from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.game.models import Planet, PlanetBuildings

User = get_user_model()


class Command(BaseCommand):
    help = "Creates test user and its planets"

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            username="user1",
            defaults={"is_staff": False},
        )
        user.set_password("Test1234")
        user.save()

        planet1, _ = Planet.objects.get_or_create(
            owner=user,
            x=2,
            y=5,
            defaults={
                "name": "Planet1",
                "metal": 500,
                "crystal": 300,
                "transporter_count": 2,
                "is_homeland": True,
            },
        )

        PlanetBuildings.objects.get_or_create(
            planet=planet1,
            defaults={
                "metal_mine_level": 1,
                "crystal_mine_level": 1,
                "metal_storage_level": 1,
                "crystal_storage_level": 1,
                "building_type": "",
                "building_ends_at": None,
            },
        )

        planet2, _ = Planet.objects.get_or_create(
            owner=user,
            x=2,
            y=12,
            defaults={
                "name": "Planet2",
                "metal": 500,
                "crystal": 300,
                "transporter_count": 2,
                "is_homeland": False,
            },
        )

        PlanetBuildings.objects.get_or_create(
            planet=planet2,
            defaults={
                "metal_mine_level": 1,
                "crystal_mine_level": 1,
                "metal_storage_level": 1,
                "crystal_storage_level": 1,
                "building_type": "",
                "building_ends_at": None,
            },
        )

        self.stdout.write(self.style.SUCCESS("Test data created."))
