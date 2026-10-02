from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from apps.game.models import Fleet, Planet, PlanetShip, SpaceObject
from apps.game.domain.exceptions import (
    FleetError,
    CargoCapacityExceededError,
    NotEnoughResourcesError,
    SamePlanetTransportError,
    NotEnoughFuelError,
    PlanetOwnershipError,
)
from apps.game.domain.travel import calculate_flight_time_seconds
from apps.game.domain.ships import SHIPS
from apps.game.domain.fleet import (
    FLEET_EVENT_ARRIVAL,
    FLEET_EVENT_RETURN,
    FleetTarget,
    calculate_cargo_capacity,
    calculate_effective_fleet_speed_multiplier,
    calculate_helion_cost_for_flight,
    get_due_fleet_events_for_fleets,
    get_safe_fleet_event_time,
    validate_mission_target_requirement,
    validate_target_coordinates,
)
from apps.game.domain.resources import (
    RESOURCE_STATE_FIELDS,
    Resource,
    ResourceAmounts,
    total_resources,
    has_resources,
    combine_resources,
    subtract_resources,
    resource_amounts_to_model_fields,
    transfer_resources,
    normalize_resource_amounts
)
from apps.game.services.resources import synchronize_resources
from .sync import advance_planet_state
from apps.game.domain.fleet_speed_profiles import (
    DEFAULT_FLEET_SPEED_PROFILE,
    get_fleet_fuel_multiplier,
)
from .fleet_ships import (
    add_fleet_ships_to_planet,
    check_and_get_planet_ships,
    create_fleet_ships,
    deduct_planet_ships_bulk,
)
from .missions import get_mission_handler
from .space_objects import get_space_object_at_coordinates, normalize_space_object_type


def get_planet_ships_display(planet, form=None):
    """
    Pobiera ilości statków dla planety z bazy i łączy je ze słownikiem SHIPS
    oraz odpowiadającymi im polami z formularza SendFleetForm.
    """
    planet_ships = {
        ship.ship_code: ship.quantity
        for ship in PlanetShip.objects.filter(planet=planet)
    }

    result = []
    for code, config in SHIPS.items():
        ship_data = {
            "code": code,
            "label": config["label"],
            "quantity": planet_ships.get(code, 0),
            "thumb": config.get("thumb"),
            "cargo_capacity": config.get("cargo_capacity", 0),
            "description": config.get("description", ""),
            "form_field": form[f"ship_{code}"] if form and f"ship_{code}" in form.fields else None,
        }
        result.append(ship_data)

    return result


def _get_planet_for_space_object(space_object):
    if space_object is None:
        return None

    if space_object.object_type != SpaceObject.ObjectType.PLANET:
        return None

    try:
        return space_object.planet
    except Planet.DoesNotExist:
        return None


def resolve_fleet_target(
    *,
    target_planet=None,
    target_coordinates=None,
    target_type=SpaceObject.ObjectType.PLANET,
) -> FleetTarget:
    if target_planet is None and target_coordinates is None:
        raise FleetError("Podaj koordynaty celu floty.")

    try:
        target_type = normalize_space_object_type(target_type)
    except ValueError as exc:
        raise FleetError(str(exc)) from exc

    if target_planet is not None:
        target_planet = Planet.objects.get(pk=target_planet.pk)
        planet_coordinates = target_planet.coordinates

        if target_type != SpaceObject.ObjectType.PLANET:
            raise FleetError("Wybrana planeta docelowa wymaga typu celu: planeta.")

        if target_coordinates is not None:
            requested_coordinates = validate_target_coordinates(target_coordinates)
            if requested_coordinates != planet_coordinates:
                raise FleetError("Planeta docelowa nie pasuje do podanych koordynatów.")

        return FleetTarget(
            coordinates=target_planet.coordinates,
            planet=target_planet,
            space_object=target_planet.space_object,
            object_type=SpaceObject.ObjectType.PLANET,
        )

    coordinates = validate_target_coordinates(target_coordinates)
    target_space_object = get_space_object_at_coordinates(
        coordinates=coordinates,
        object_type=target_type,
    )
    target_planet = _get_planet_for_space_object(target_space_object)

    return FleetTarget(
        coordinates=coordinates,
        planet=target_planet,
        space_object=target_space_object,
        object_type=target_type,
    )


def validate_mission_target(mission_handler, source_planet, target, user) -> None:
    requirement = mission_handler.target_requirement
    target_planet = target.planet

    validate_mission_target_requirement(requirement, target_planet, user)
    mission_handler.validate_dispatch(source_planet, target_planet, user)


def handle_fleet_return(fleet, *, at) -> None:
    source_planet = (
        Planet.objects
        .select_for_update()
        .get(pk=fleet.source_planet_id)
    )

    safe_event_time = get_safe_fleet_event_time(at, source_planet)
    advance_result = advance_planet_state(source_planet, at=safe_event_time)
    source_planet = advance_result.planet

    add_fleet_ships_to_planet(fleet, source_planet)
    fleet_resource_fields, _ = transfer_resources(source=fleet, target=source_planet)

    fleet.status = Fleet.Status.COMPLETED

    source_planet.save(update_fields=RESOURCE_STATE_FIELDS)
    fleet.save(update_fields=[*fleet_resource_fields, "status"])


def handle_outbound_fleet_arrival(fleet, *, at) -> None:
    handler = get_mission_handler(fleet.mission_type)
    handler.handle_arrival(fleet, at=at)


def ensure_source_planet_belongs_to_user(source_planet, user) -> None:
    if source_planet.owner_id != user.id:
        raise PlanetOwnershipError("Planeta źródłowa nie należy do tego gracza.")


@transaction.atomic
def _send_fleet_mission(
    source_planet,
    target_planet,
    ship_quantities: dict[str, int],
    cargo: ResourceAmounts,
    user,
    mission_type: str,
    speed_profile=DEFAULT_FLEET_SPEED_PROFILE,
    at=None,
    target_coordinates=None,
    target_type=SpaceObject.ObjectType.PLANET,
):
    now = at or timezone.now()

    cargo = normalize_resource_amounts(cargo)

    # Pobieramy handler misji i walidujemy
    mission_handler = get_mission_handler(mission_type)

    source_planet = Planet.objects.select_for_update().get(pk=source_planet.pk)
    target = resolve_fleet_target(
        target_planet=target_planet,
        target_coordinates=target_coordinates,
        target_type=target_type,
    )

    ensure_source_planet_belongs_to_user(source_planet, user)

    if source_planet.coordinates == target.coordinates:
        raise SamePlanetTransportError("Nie można wysłać floty na tę samą planetę.")

    validate_mission_target(mission_handler, source_planet, target, user)

    synchronize_resources(source_planet, at=now, save=False)

    # 1. Walidacja i pobranie rekordów PlanetShip
    existing_ships = check_and_get_planet_ships(source_planet, ship_quantities)
    mission_handler.validate_fleet_composition(ship_quantities, mission_type)

    # 2. Walidacja surowców
    if not has_resources(source_planet, cargo):
        raise NotEnoughResourcesError("Nie masz wystarczających zasobów.")

    cargo_amount = total_resources(cargo)
    cargo_capacity = calculate_cargo_capacity(ship_quantities)
    if cargo_amount > cargo_capacity:
        raise CargoCapacityExceededError("Ładunek nie mieści się w pojemności floty.")

    fuel_multiplier = get_fleet_fuel_multiplier(speed_profile)
    helion_cost = calculate_helion_cost_for_flight(
        source_planet,
        target,
        ship_quantities,
        fuel_multiplier,
    )

    fuel = {Resource.HELION: helion_cost}
    required_resources = combine_resources(cargo, fuel)
    if not has_resources(source_planet, required_resources):
        raise NotEnoughFuelError("Nie masz wystarczającej ilości helionu na lot.")

    # 3. Zapis zmian
    deduct_planet_ships_bulk(existing_ships, ship_quantities)

    subtract_resources(source_planet, required_resources)
    source_planet.save(update_fields=RESOURCE_STATE_FIELDS)

    speed_multiplier = calculate_effective_fleet_speed_multiplier(ship_quantities, speed_profile)
    flight_time_seconds = calculate_flight_time_seconds(
        source_planet.coordinates,
        target.coordinates,
        speed_multiplier,
    )
    flight_duration = timedelta(seconds=flight_time_seconds)

    arrival_time = now + flight_duration

    # Przekazanie decyzji o powrocie do handlera (stacjonuj zwraca None, transport zwraca +flight_duration)
    return_time = mission_handler.calculate_return_time(arrival_time, flight_duration)

    fleet_resource_fields = resource_amounts_to_model_fields(cargo, include_missing=True, default=0)

    fleet = Fleet.objects.create(
        owner=user,
        source_planet=source_planet,
        target_planet=target.planet,
        **Fleet.target_coordinate_fields(target.coordinates),
        helion_cost=helion_cost,
        mission_type=mission_type,
        status=Fleet.Status.OUTBOUND,
        speed_profile=speed_profile,
        departure_time=now,
        arrival_time=arrival_time,
        return_time=return_time,
        **fleet_resource_fields,
    )

    create_fleet_ships(fleet, ship_quantities)

    return fleet


def send_transport_fleet(
    source_planet,
    target_planet,
    ship_quantities: dict[str, int],
    cargo: ResourceAmounts,
    user,
    speed_profile=DEFAULT_FLEET_SPEED_PROFILE,
    at=None,
    target_coordinates=None,
    target_type=SpaceObject.ObjectType.PLANET,
):
    """
    Wysyła flotę z misją transportu.
    """
    return _send_fleet_mission(
        source_planet=source_planet,
        target_planet=target_planet,
        ship_quantities=ship_quantities,
        cargo=cargo,
        speed_profile=speed_profile,
        user=user,
        mission_type=Fleet.MissionType.TRANSPORT,
        at=at,
        target_coordinates=target_coordinates,
        target_type=target_type,
    )


def send_stationing_fleet(
    source_planet,
    target_planet,
    ship_quantities: dict[str, int],
    cargo: ResourceAmounts,
    user,
    speed_profile=DEFAULT_FLEET_SPEED_PROFILE,
    at=None,
    target_coordinates=None,
    target_type=SpaceObject.ObjectType.PLANET,
):
    """
    Wysyła flotę z misją stacjonowania.
    """
    return _send_fleet_mission(
        source_planet=source_planet,
        target_planet=target_planet,
        ship_quantities=ship_quantities,
        cargo=cargo,
        speed_profile=speed_profile,
        user=user,
        mission_type=Fleet.MissionType.STATION,
        at=at,
        target_coordinates=target_coordinates,
        target_type=target_type,
    )


def send_espionage_fleet(
    source_planet,
    target_planet,
    ship_quantities: dict[str, int],
    cargo: ResourceAmounts,
    user,
    speed_profile=DEFAULT_FLEET_SPEED_PROFILE,
    at=None,
    target_coordinates=None,
    target_type=SpaceObject.ObjectType.PLANET,
):
    """
    Wysyła flotę z misją Szpiegowania. Misja nie przewozi ładunku i wraca po skanie celu.
    """
    normalized_cargo = normalize_resource_amounts(cargo or {})
    if total_resources(normalized_cargo) > 0:
        raise FleetError("Misja szpiegowska nie może przewozić ładunku.")

    return _send_fleet_mission(
        source_planet=source_planet,
        target_planet=target_planet,
        ship_quantities=ship_quantities,
        cargo={},
        speed_profile=speed_profile,
        user=user,
        mission_type=Fleet.MissionType.ESPIONAGE,
        at=at,
        target_coordinates=target_coordinates,
        target_type=target_type,
    )


def send_colonization_fleet(
    source_planet,
    ship_quantities: dict[str, int],
    target_planet=None,
    cargo: ResourceAmounts = None,
    user=None,
    speed_profile=DEFAULT_FLEET_SPEED_PROFILE,
    at=None,
    target_coordinates=None,
    target_type=SpaceObject.ObjectType.PLANET,
):
    return _send_fleet_mission(
        source_planet=source_planet,
        target_planet=None,
        ship_quantities=ship_quantities,
        cargo=cargo,
        speed_profile=speed_profile,
        user=user,
        mission_type=Fleet.MissionType.COLONIZE,
        at=at,
        target_coordinates=target_coordinates,
        target_type=SpaceObject.ObjectType.PLANET,
    )


def get_due_fleet_events(owner, *, at):
    owner_planet_ids = Planet.objects.filter(owner=owner).values("pk")

    fleets = list(
        Fleet.objects
        .select_for_update()
        .prefetch_related("ships")
        .filter(Q(owner=owner) | Q(target_planet_id__in=owner_planet_ids))
        .exclude(status=Fleet.Status.COMPLETED)
        .order_by("pk")
    )

    return get_due_fleet_events_for_fleets(
        fleets,
        at=at,
        outbound_status=Fleet.Status.OUTBOUND,
        returning_status=Fleet.Status.RETURNING,
    )


@transaction.atomic
def process_fleets_for_user(user, *, at=None):
    target_time = at or timezone.now()
    processed_events = []

    events = get_due_fleet_events(user, at=target_time)

    for event in events:
        fleet = event.fleet  # Wyciągamy model z pamięci zamiast ponownie strzelać zapytaniem do bazy

        if event.event_type == FLEET_EVENT_ARRIVAL:
            if fleet.status != Fleet.Status.OUTBOUND:
                continue

            handle_outbound_fleet_arrival(fleet, at=event.event_time)
            processed_events.append(event)

        elif event.event_type == FLEET_EVENT_RETURN:
            if fleet.status != Fleet.Status.RETURNING:
                continue

            handle_fleet_return(fleet, at=event.event_time)
            processed_events.append(event)

    return processed_events
