from django.contrib.auth import get_user_model

from apps.game.models import Planet, PlanetBuildings


class PlanetTestMixin:
    BUILDING_FIELDS = {
        "metal_mine_level",
        "crystal_mine_level",
        "metal_storage_level",
        "crystal_storage_level",
        "building_type",
        "building_ends_at",
    }

    def create_user(self, username="tester"):
        User = get_user_model()
        return User.objects.create_user(username=username, password="secret")

    def create_planet(self, owner=None, last_resource_update=None, **overrides):
        if owner is None:
            owner = self.create_user()

        planet_data = {
            "owner": owner,
            "name": "Test Planet",
            "galaxy": 1,
            "system": 1,
            "position": 1,
            "metal": 500,
            "crystal": 200,
            "is_homeland": True,
            "transporter_count": 0,
        }

        buildings_data = {
            "metal_mine_level": 2,
            "crystal_mine_level": 1,
            "metal_storage_level": 10,
            "crystal_storage_level": 10,
            "building_type": "",
            "building_ends_at": None,
        }

        for key in list(overrides.keys()):
            if key in self.BUILDING_FIELDS:
                buildings_data[key] = overrides.pop(key)

        planet_data.update(overrides)

        planet = Planet.objects.create(**planet_data)
        PlanetBuildings.objects.create(planet=planet, **buildings_data)

        if last_resource_update is not None:
            Planet.objects.filter(pk=planet.pk).update(
                last_resource_update=last_resource_update
            )

        return self.reload_planet(planet)

    def reload_planet(self, planet):
        return Planet.objects.select_related("buildings").get(pk=planet.pk)