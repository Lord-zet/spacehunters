from django.db import transaction
from apps.game.domain_services.planet_generation import generate_planet_traits

from apps.game.models import (
    Planet,
    PLANET_NAME_MAX_LENGTH,
    PlanetBuildings,
    PlanetShip,
    PlanetShipConstruction,
)
from apps.game.ships import SHIPS
from apps.game.domain.exceptions import (
    InvalidPlanetNameError,
    PlanetNameAlreadyExistsError,
)


DEFAULT_PLANET_RESOURCES = {
    "metal": 500,
    "crystal": 200,
    "helion": 0,
}


DEFAULT_BUILDING_LEVELS = {
    "metal_mine_level": 1,
    "crystal_mine_level": 0,
    "helion_synthesizer_level": 0,
    "solar_array_level": 1,
    "metal_storage_level": 0,
    "crystal_storage_level": 0,
    "helion_storage_level": 0,
    "shipyard_level": 0,
    "building_type": "",
    "building_ends_at": None,
}


@transaction.atomic
def rename_planet(planet: Planet, new_name: str) -> Planet:
    normalized_name = new_name.strip()

    if not normalized_name:
        raise InvalidPlanetNameError("Nazwa planety nie moze byc pusta.")

    if len(normalized_name) > PLANET_NAME_MAX_LENGTH:
        raise InvalidPlanetNameError("Nazwa planety jest zbyt dluga.")

    locked_planet = Planet.objects.select_for_update().get(pk=planet.pk)

    name_exists = (
        Planet.objects
        .filter(owner_id=locked_planet.owner_id, name__iexact=normalized_name)
        .exclude(pk=locked_planet.pk)
        .exists()
    )
    if name_exists:
        raise PlanetNameAlreadyExistsError("Masz juz planete o takiej nazwie.")

    if locked_planet.name == normalized_name:
        return locked_planet

    locked_planet.name = normalized_name
    locked_planet.save(update_fields=["name"])
    return locked_planet


@transaction.atomic
def create_planet(*, owner, name: str, galaxy: int, system: int, position: int, is_homeland: bool = False,
                  planet_fields_total: int = 90, resources: dict | None = None, buildings: dict | None = None,
                  ships: dict | None = None, planet_type=None, radius_km=None, temperature_min=None,
                  temperature_max=None, rng=None,) -> Planet:

    resource_data = {**DEFAULT_PLANET_RESOURCES,**(resources or {})}
    building_data = {**DEFAULT_BUILDING_LEVELS, **(buildings or {})}

    generated_traits = generate_planet_traits(planet_type=planet_type, rng=rng)

    planet = Planet.objects.create(
        owner=owner,
        name=name,
        galaxy=galaxy,
        system=system,
        position=position,
        is_homeland=is_homeland,
        planet_fields_total=planet_fields_total,
        planet_type=(
            planet_type
            if planet_type is not None
            else generated_traits.planet_type
        ),
        radius_km=(
            radius_km
            if radius_km is not None
            else generated_traits.radius_km
        ),
        temperature_min=(
            temperature_min
            if temperature_min is not None
            else generated_traits.temperature_min
        ),
        temperature_max=(
            temperature_max
            if temperature_max is not None
            else generated_traits.temperature_max
        ),
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
