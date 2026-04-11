from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.game.models import Planet

User = get_user_model()


class Command(BaseCommand):
    help = "Creates test user and its planets"

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            username="user1",
            defaults={"is_staff": False}
        )
        user.set_password("Test1234")
        user.save()


        Planet.objects.get_or_create(
            owner=user,
            x=2,
            y=5,
            defaults={
                "name": "Planet1",
                "metal": 500,
                "crystal": 300,
                "metal_mine_level": 1,
                "crystal_mine_level": 1,
                "transporter_count": 2,
                "is_homeland": True,
            }
        )

        Planet.objects.get_or_create(
            owner=user,
            x=2,
            y=12,
            defaults={
                "name": "Planet2",
                "metal": 500,
                "crystal": 300,
                "metal_mine_level": 1,
                "crystal_mine_level": 1,
                "transporter_count": 2,
                "is_homeland": False,
            }
        )

        self.stdout.write(self.style.SUCCESS("Test data created."))
