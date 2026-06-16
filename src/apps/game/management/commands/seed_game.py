from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.game.models import Planet
from apps.game.domain_services.planets import create_planet

User = get_user_model()


class Command(BaseCommand):
    help = "Creates test user and its planets"

    def ensure_planet(self, *, owner, galaxy, system, position, name, is_homeland):
        planet = Planet.objects.filter(
            owner=owner,
            galaxy=galaxy,
            system=system,
            position=position,
        ).first()

        if planet is not None:
            return planet

        return create_planet(
            owner=owner,
            galaxy=galaxy,
            system=system,
            position=position,
            name=name,
            is_homeland=is_homeland,
            resources={
                "metal": 500,
                "crystal": 300,
                "helion": 300,
            },
            buildings={
                "metal_mine_level": 1,
                "crystal_mine_level": 1,
                "helion_synthesizer_level": 1,
                "metal_storage_level": 0,
                "crystal_storage_level": 0,
                "helion_storage_level": 0,
                "shipyard_level": 0,
                "building_type": "",
                "building_ends_at": None,
            },
            ships={
                "transporter": 2,
            },
        )

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            username="user1",
            defaults={"is_staff": False},
        )
        user.set_password("Test1234")
        user.save()

        self.ensure_planet(
            owner=user,
            galaxy=1,
            system=2,
            position=5,
            name="Planet1",
            is_homeland=True,
        )

        self.ensure_planet(
            owner=user,
            galaxy=1,
            system=2,
            position=12,
            name="Planet2",
            is_homeland=False,
        )

        self.stdout.write(self.style.SUCCESS("Test data created."))