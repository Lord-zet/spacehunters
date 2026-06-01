from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.game.domain.exceptions import (
    InvalidShipQuantityError,
    NotEnoughResourcesError,
    ShipConstructionAlreadyInProgressError,
    ShipyardRequiredError,
    UnknownShipError,
)
from apps.game.models import Planet, PlanetShip, PlanetShipConstruction, PlanetBuildings
from apps.game.ships import SHIPS
from .resources import synchronize_resources, RESOURCE_FIELDS


def get_ship_config(ship_code):
    return SHIPS.get(ship_code)


def get_ship_construction_cost(ship_code, quantity):
    config = get_ship_config(ship_code)
    if not config:
        return None

    return {
        resource: amount * quantity
        for resource, amount in config["base_cost"].items()
    }


def get_ship_construction_time_seconds(ship_code, quantity):
    config = get_ship_config(ship_code)
    if not config:
        return None

    return config["build_time"] * quantity


def has_enough_resources(planet, cost):
    for resource, amount in cost.items():
        if getattr(planet, resource) < amount:
            return False
    return True


def spend_resources(planet, cost):
    for resource, amount in cost.items():
        setattr(planet, resource, getattr(planet, resource) - amount)


@transaction.atomic
def start_ship_construction(planet, ship_code, quantity, *, at=None):
    now = at or timezone.now()

    planet = Planet.objects.select_for_update().get(pk=planet.pk)
    buildings, _ = PlanetBuildings.objects.select_for_update().get_or_create(planet=planet)
    construction, _ = PlanetShipConstruction.objects.select_for_update().get_or_create(planet=planet)

    synchronize_resources(planet, at=now, save=False)

    config = get_ship_config(ship_code)
    if not config:
        raise UnknownShipError("Nieznany statek.")

    if quantity <= 0:
        raise InvalidShipQuantityError("Liczba statków musi być większa od zera.")

    if buildings.shipyard_level < config.get("required_shipyard_level", 1):
        raise ShipyardRequiredError("Wymagany jest odpowiedni poziom stoczni.")

    if construction.is_in_progress(at=now):
        raise ShipConstructionAlreadyInProgressError("Na tej planecie trwa już budowa statków.")

    cost = get_ship_construction_cost(ship_code, quantity)
    if cost is None:
        raise UnknownShipError("Nieznany statek.")

    if not has_enough_resources(planet, cost):
        raise NotEnoughResourcesError("Za mało surowców.")

    spend_resources(planet, cost)

    construction.ship_code = ship_code
    construction.quantity = quantity
    construction.started_at = now
    construction.ends_at = now + timedelta(seconds=get_ship_construction_time_seconds(ship_code, quantity))

    construction.save(update_fields=["ship_code", "quantity", "started_at", "ends_at"])
    planet.save(update_fields=[*RESOURCE_FIELDS, "last_resource_update"])

    return construction


@transaction.atomic
def finish_ship_construction_if_ready(planet, *, at=None):
    now = at or timezone.now()

    planet = Planet.objects.select_for_update().get(pk=planet.pk)
    construction, _ = PlanetShipConstruction.objects.select_for_update().get_or_create(planet=planet)

    if not construction.ends_at:
        return False

    if construction.ends_at > now:
        return False

    config = get_ship_config(construction.ship_code)
    if not config:
        construction.clear()
        construction.save(update_fields=["ship_code", "quantity", "started_at", "ends_at"])
        return False

    planet_ship, _ = PlanetShip.objects.select_for_update().get_or_create(
        planet=planet,
        ship_code=construction.ship_code,
        defaults={"quantity": 0},
    )
    planet_ship.quantity += construction.quantity
    planet_ship.save(update_fields=["quantity"])

    construction.clear()
    construction.save(update_fields=["ship_code", "quantity", "started_at", "ends_at"])

    return True
