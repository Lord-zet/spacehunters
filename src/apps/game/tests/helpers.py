from django.contrib.auth import get_user_model

from apps.game.models import Planet


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
