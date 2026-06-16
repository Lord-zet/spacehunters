from django.db import transaction

from apps.game.models import (
    Planet,
    PlanetBuildings,
    PlanetShip,
    PlanetShipConstruction,
)
from apps.game.ships import SHIPS


DEFAULT_PLANET_RESOURCES = {
    "metal": 500,
    "crystal": 200,
    "helion": 0,
}


DEFAULT_BUILDING_LEVELS = {
    "metal_mine_level": 1,
    "crystal_mine_level": 0,
    "helion_synthesizer_level": 0,
    "metal_storage_level": 0,
    "crystal_storage_level": 0,
    "helion_storage_level": 0,
    "shipyard_level": 0,
    "building_type": "",
    "building_ends_at": None,
}


@transaction.atomic
def create_planet(*, owner, name: str, galaxy: int, system: int, position: int, is_homeland: bool = False,
                  planet_fields_total: int = 90, resources: dict | None = None, buildings: dict | None = None,
                  ships: dict | None = None) -> Planet:

    resource_data = {**DEFAULT_PLANET_RESOURCES,**(resources or {})}
    building_data = {**DEFAULT_BUILDING_LEVELS, **(buildings or {})}

    planet = Planet.objects.create(
        owner=owner,
        name=name,
        galaxy=galaxy,
        system=system,
        position=position,
        is_homeland=is_homeland,
        planet_fields_total=planet_fields_total,
        **resource_data,
    )

    PlanetBuildings.objects.create(planet=planet, **building_data)

    PlanetShipConstruction.objects.create(planet=planet)

    ship_quantities = ships or {}

    for ship_code in SHIPS.keys():
        quantity = ship_quantities.get(ship_code, 0)

        if quantity <= 0:
            continue

        PlanetShip.objects.create(planet=planet, ship_code=ship_code, quantity=quantity)

    return planet