from dataclasses import dataclass

from apps.game.domain.exceptions import InvalidPlanetNameError


PLANET_NAME_MAX_LENGTH = 50
DEFAULT_PLANET_FIELDS_TOTAL = 90

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


@dataclass(frozen=True, slots=True)
class PlanetLimitStatus:
    current: int
    maximum: int

    @property
    def remaining(self) -> int:
        return max(self.maximum - self.current, 0)

    @property
    def is_reached(self) -> bool:
        return self.current >= self.maximum


def normalize_planet_name(name: str) -> str:
    normalized_name = name.strip()

    if not normalized_name:
        raise InvalidPlanetNameError("Nazwa planety nie może być pusta.")

    if len(normalized_name) > PLANET_NAME_MAX_LENGTH:
        raise InvalidPlanetNameError("Nazwa planety jest zbyt długa.")

    return normalized_name
