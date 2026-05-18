from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.game.models import Planet, PlanetBuildings

User = get_user_model()


class Command(BaseCommand):
    help = "Creates test user and its planets"

    def ensure_planet(self, *, owner, x, y, name, is_homeland):
        planet, _ = Planet.objects.get_or_create(
            owner=owner,
            x=x,
            y=y,
            defaults={
                "name": name,
                "metal": 500,
                "crystal": 300,
                "transporter_count": 2,
                "is_homeland": is_homeland,
            },
        )

        PlanetBuildings.objects.get_or_create(
            planet=planet,
            defaults={
                "metal_mine_level": 1,
                "crystal_mine_level": 1,
                "metal_storage_level": 1,
                "crystal_storage_level": 1,
                "building_type": "",
                "building_ends_at": None,
            },
        )

        return planet

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            username="user1",
            defaults={"is_staff": False},
        )
        user.set_password("Test1234")
        user.save()

        self.ensure_planet(
            owner=user,
            x=2,
            y=5,
            name="Planet1",
            is_homeland=True,
        )

        self.ensure_planet(
            owner=user,
            x=2,
            y=12,
            name="Planet2",
            is_homeland=False,
        )

        self.stdout.write(self.style.SUCCESS("Test data created."))