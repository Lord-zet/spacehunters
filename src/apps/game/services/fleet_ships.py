from apps.game.models import FleetShip, PlanetShip
from apps.game.domain.exceptions import FleetError, NotEnoughTransportersError
from apps.game.domain.fleet import validate_ship_quantities


def check_and_get_planet_ships(planet, ship_quantities: dict[str, int]) -> list[PlanetShip]:
    """
    Pobiera istniejące statki jednym zapytaniem i weryfikuje ich ilość.
    Zapobiega N+1 zapytaniom występującym przy pętlach walidujących poszczególne typy.
    """
    validate_ship_quantities(ship_quantities)
    active_quantities = {code: q for code, q in ship_quantities.items() if q > 0}

    existing_ships = list(
        PlanetShip.objects
        .select_for_update()
        .filter(planet=planet, ship_code__in=active_quantities.keys())
    )
    ship_map = {ship.ship_code: ship for ship in existing_ships}

    for ship_code, required_quantity in active_quantities.items():
        planet_ship = ship_map.get(ship_code)

        if not planet_ship or planet_ship.quantity < required_quantity:
            if "transporter" in ship_code:
                raise NotEnoughTransportersError("Nie masz wystarczającej liczby transportowców.")
            raise FleetError(f"Nie masz wystarczającej liczby statków ({ship_code}).")

    return existing_ships


def deduct_planet_ships_bulk(ships_to_update: list[PlanetShip], ship_quantities: dict[str, int]) -> None:
    """
    Odejmuje wartości statków w pamięci i wykonuje 1 zapytanie UPDATE (bulk_update).
    """
    if not ships_to_update:
        return

    for ship in ships_to_update:
        deduction = ship_quantities.get(ship.ship_code, 0)
        if deduction > 0:
            ship.quantity -= deduction

    PlanetShip.objects.bulk_update(ships_to_update, ["quantity"])


def create_fleet_ships(fleet, ship_quantities: dict[str, int]) -> None:
    fleet_ships = [
        FleetShip(
            fleet=fleet,
            ship_code=ship_code,
            quantity=quantity,
        )
        for ship_code, quantity in ship_quantities.items()
        if quantity > 0
    ]
    if fleet_ships:
        FleetShip.objects.bulk_create(fleet_ships)


def add_fleet_ships_to_planet(fleet, planet) -> None:
    """
    Dodaje statki z floty do planety.

    Przy prefetched fleet.ships wykonuje jedno zapytanie odczytujące PlanetShip oraz maksymalnie
    jeden bulk_update i jeden bulk_create.
    """
    fleet_ships = [fs for fs in fleet.ships.all() if fs.quantity > 0]
    if not fleet_ships:
        return

    ship_codes = [fs.ship_code for fs in fleet_ships]

    existing_ships = list(
        PlanetShip.objects
        .select_for_update()
        .filter(planet=planet, ship_code__in=ship_codes)
    )
    ship_map = {ship.ship_code: ship for ship in existing_ships}

    ships_to_update = []
    ships_to_create = []

    for fs in fleet_ships:
        if fs.ship_code in ship_map:
            planet_ship = ship_map[fs.ship_code]
            planet_ship.quantity += fs.quantity
            ships_to_update.append(planet_ship)
        else:
            ships_to_create.append(PlanetShip(
                planet=planet,
                ship_code=fs.ship_code,
                quantity=fs.quantity
            ))

    if ships_to_update:
        PlanetShip.objects.bulk_update(ships_to_update, ["quantity"])
    if ships_to_create:
        PlanetShip.objects.bulk_create(ships_to_create)
