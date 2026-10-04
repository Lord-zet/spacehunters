from django.db import IntegrityError

from apps.game.models import Fleet, Planet, SpaceObject
from apps.game.domain.exceptions import (
    FleetError,
    PlanetLimitReachedError,
    UnsupportedFleetMissionError,
)
from apps.game.domain.fleet import (
    MISSION_TARGET_EMPTY_COORDINATES,
    MISSION_TARGET_EXISTING_OBJECT,
    MISSION_TARGET_EXISTING_PLANET,
    MISSION_TARGET_OWN_PLANET,
    get_fleet_flight_duration,
    get_safe_fleet_event_time,
    validate_espionage_fleet_composition,
    validate_mission_fleet_composition,
)
from apps.game.domain.resources import RESOURCE_STATE_FIELDS, transfer_resources
from .fleet_ships import add_fleet_ships_to_planet
from .planets import create_planet, get_planet_at_coordinates, get_planet_limit_status
from .reports import create_espionage_report
from .sync import advance_planet_state


def send_fleet_back_from_target(fleet, *, at) -> None:
    flight_duration = get_fleet_flight_duration(fleet)

    fleet.status = Fleet.Status.RETURNING
    fleet.return_time = at + flight_duration
    fleet.save(update_fields=["status", "return_time"])


def prepare_planet_for_fleet_event(planet_id, at):
    planet = (
        Planet.objects
        .select_for_update()
        .get(pk=planet_id)
    )
    safe_event_time = get_safe_fleet_event_time(at, planet)
    advance_result = advance_planet_state(planet, at=safe_event_time)
    return advance_result.planet


def create_colony_from_fleet(fleet, *, at):
    coordinates = fleet.target_coordinates

    if get_planet_at_coordinates(coordinates) is not None:
        return None

    try:
        planet = create_planet(
            owner=fleet.owner,
            name=f"Kolonia {fleet.target_coordinates}",
            is_homeland=False,
            resources={
                "metal": 0,
                "crystal": 0,
                "helion": 0,
            },
            coordinates=coordinates,
        )
    except (IntegrityError, PlanetLimitReachedError):
        return None

    planet.last_resource_update = at
    return planet


class BaseMission:
    """Klasa bazowa dla wszystkich misji flot."""

    target_requirement = MISSION_TARGET_EXISTING_PLANET
    allowed_target_types = (SpaceObject.ObjectType.PLANET,)

    def validate_target_type(self, target):
        if target.object_type not in self.allowed_target_types:
            raise FleetError("Ten typ misji nie może zostać wysłany na wybrany typ celu.")

    def validate_dispatch(self, source_planet, target_planet, user):
        """Specyficzna walidacja dla danego typu misji przed wylotem."""
        pass

    def validate_fleet_composition(self, ship_quantities: dict[str, int], mission_type: str):
        """Sprawdza, czy wybrane statki mogą wykonać dany typ misji."""
        validate_mission_fleet_composition(ship_quantities, mission_type)

    def calculate_return_time(self, arrival_time, flight_duration):
        """Oblicza czas powrotu floty (domyślnie powrót trwa tyle samo co dolot)."""
        return arrival_time + flight_duration

    def handle_arrival(self, fleet, *, at):
        """Zdarzenie wywoływane w momencie dotarcia floty do celu."""
        raise NotImplementedError("Subclasses must implement handle_arrival")


class TransportMission(BaseMission):
    def handle_arrival(self, fleet, *, at):
        target_planet = prepare_planet_for_fleet_event(fleet.target_planet_id, at)

        fleet_resource_fields, _ = transfer_resources(source=fleet, target=target_planet)

        fleet.status = Fleet.Status.RETURNING

        target_planet.save(update_fields=RESOURCE_STATE_FIELDS)
        fleet.save(update_fields=[*fleet_resource_fields, "status"])


class StationMission(BaseMission):
    target_requirement = MISSION_TARGET_OWN_PLANET

    def calculate_return_time(self, arrival_time, flight_duration):
        # Misja stacjonuj nie wraca
        return None

    def handle_arrival(self, fleet, *, at):
        target_planet = prepare_planet_for_fleet_event(fleet.target_planet_id, at)

        fleet_resource_fields, _ = transfer_resources(source=fleet, target=target_planet)

        add_fleet_ships_to_planet(fleet, target_planet)

        fleet.status = Fleet.Status.COMPLETED
        fleet.return_time = None

        target_planet.save(update_fields=RESOURCE_STATE_FIELDS)
        fleet.save(update_fields=[*fleet_resource_fields, "status", "return_time"])


class EspionageMission(BaseMission):
    target_requirement = MISSION_TARGET_EXISTING_OBJECT
    allowed_target_types = (
        SpaceObject.ObjectType.PLANET,
        SpaceObject.ObjectType.MOON,
    )

    def validate_fleet_composition(self, ship_quantities: dict[str, int], mission_type: str):
        validate_espionage_fleet_composition(ship_quantities, mission_type)

    def handle_arrival(self, fleet, *, at):
        target_planet = None
        target_object = fleet.target_object

        if fleet.target_object_type == SpaceObject.ObjectType.PLANET:
            target_planet = prepare_planet_for_fleet_event(fleet.target_planet_id, at)
            target_object = target_planet.space_object

        create_espionage_report(
            owner=fleet.owner,
            source_planet=fleet.source_planet,
            target_planet=target_planet,
            target_object=target_object,
            fleet=fleet,
        )

        fleet.status = Fleet.Status.RETURNING

        if target_planet is not None:
            target_planet.save(update_fields=RESOURCE_STATE_FIELDS)
        fleet.save(update_fields=["status"])


class ColonizationMission(BaseMission):
    target_requirement = MISSION_TARGET_EMPTY_COORDINATES

    def validate_dispatch(self, source_planet, target_planet, user):
        if get_planet_limit_status(user).is_reached:
            raise FleetError("Osiągnięto maksymalną liczbę planet gracza.")

    def calculate_return_time(self, arrival_time, flight_duration):
        return None

    def handle_arrival(self, fleet, *, at):
        target_planet = create_colony_from_fleet(fleet, at=at)

        if target_planet is None:
            send_fleet_back_from_target(fleet, at=at)
            return

        fleet_resource_fields, _ = transfer_resources(source=fleet, target=target_planet)
        add_fleet_ships_to_planet(fleet, target_planet)

        fleet.target_planet = target_planet
        fleet.status = Fleet.Status.COMPLETED
        fleet.return_time = None

        target_planet.save(update_fields=RESOURCE_STATE_FIELDS)
        fleet.save(update_fields=[
            *fleet_resource_fields,
            "target_planet",
            "status",
            "return_time",
        ])


MISSION_HANDLERS = {
    Fleet.MissionType.TRANSPORT: TransportMission(),
    Fleet.MissionType.STATION: StationMission(),
    Fleet.MissionType.ESPIONAGE: EspionageMission(),
    Fleet.MissionType.COLONIZE: ColonizationMission(),
}


def get_mission_handler(mission_type: str) -> BaseMission:
    handler = MISSION_HANDLERS.get(mission_type)
    if not handler:
        raise UnsupportedFleetMissionError("Nieobsługiwany typ misji floty.")
    return handler


def get_mission_target_type_rules() -> dict[str, list[str]]:
    return {
        mission_type: list(handler.allowed_target_types)
        for mission_type, handler in MISSION_HANDLERS.items()
    }
