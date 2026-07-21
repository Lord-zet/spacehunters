from django.contrib.auth import get_user_model

from apps.game.models import Planet, PlanetShip, FleetShip
from apps.game.domain_services.planets import create_planet


class PlanetTestMixin:
    BUILDING_FIELDS = {
        "metal_mine_level",
        "crystal_mine_level",
        "helion_synthesizer_level",
        "solar_array_level",
        "metal_storage_level",
        "crystal_storage_level",
        "helion_storage_level",
        "shipyard_level",
        "building_type",
        "building_ends_at",
        "building_cost_paid",
    }

    SHIP_FIELDS = {
        "transporter_count",
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
            "helion": 0,
            "is_homeland": True,
            "planet_fields_total": 50,
            "planet_type": overrides.pop("planet_type", "terrestrial"),
            "radius_km": overrides.pop("radius_km", 6_000),
            "temperature_min": overrides.pop("temperature_min", -20),
            "temperature_max": overrides.pop("temperature_max", 40),
        }

        buildings_data = {
            "metal_mine_level": 2,
            "crystal_mine_level": 1,
            "helion_synthesizer_level": 0,
            "solar_array_level": 20,
            "metal_storage_level": 10,
            "crystal_storage_level": 10,
            "helion_storage_level": 0,
            "shipyard_level": 0,
            "building_type": "",
            "building_ends_at": None,
            "building_cost_paid": {},
        }

        ships_data = {
            "transporter_count": 0,
        }

        for key in list(overrides.keys()):
            if key in self.BUILDING_FIELDS:
                buildings_data[key] = overrides.pop(key)
            elif key in self.SHIP_FIELDS:
                ships_data[key] = overrides.pop(key)

        planet_data.update(overrides)

        planet = create_planet(
            owner=planet_data["owner"],
            name=planet_data["name"],
            galaxy=planet_data["galaxy"],
            system=planet_data["system"],
            position=planet_data["position"],
            is_homeland=planet_data["is_homeland"],
            planet_fields_total=planet_data["planet_fields_total"],
            resources={
                "metal": planet_data["metal"],
                "crystal": planet_data["crystal"],
                "helion": planet_data["helion"],
            },
            buildings=buildings_data,
            ships={
                "transporter": ships_data["transporter_count"],
            },
            planet_type=planet_data['planet_type'],
            radius_km=planet_data['radius_km'],
            temperature_min=planet_data['temperature_min'],
            temperature_max=planet_data['temperature_max'],
        )

        if last_resource_update is not None:
            Planet.objects.filter(pk=planet.pk).update(
                last_resource_update=last_resource_update
            )

        return self.reload_planet(planet)

    def reload_planet(self, planet):
        return Planet.objects.select_related("buildings").get(pk=planet.pk)

    def get_planet_ship_quantity(self, planet, ship_code):
        ship = PlanetShip.objects.filter(planet=planet, ship_code=ship_code).first()
        return ship.quantity if ship else 0

    def get_fleet_ship_quantity(self, fleet, ship_code):
        ship = FleetShip.objects.get(fleet=fleet, ship_code=ship_code)
        return ship.quantity
