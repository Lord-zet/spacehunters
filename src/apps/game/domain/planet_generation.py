from dataclasses import dataclass
import random

from apps.game.planet_types import (
    DEFAULT_PLANET_TYPE,
    PLANET_TYPES,
    get_planet_type_config,
)


@dataclass(frozen=True, slots=True)
class GeneratedPlanetTraits:
    planet_type: str
    radius_km: int
    temperature_min: int
    temperature_max: int


def get_random_planet_type(*, rng=None) -> str:
    rng = rng or random
    return rng.choice(list(PLANET_TYPES.keys()))


def generate_planet_traits(*, planet_type: str | None = None, rng=None) -> GeneratedPlanetTraits:
    rng = rng or random

    resolved_planet_type = (
        planet_type
        or get_random_planet_type(rng=rng)
        or DEFAULT_PLANET_TYPE
    )

    config = get_planet_type_config(resolved_planet_type)

    radius_min, radius_max = config["radius_km_range"]
    temp_min_low, temp_min_high = config["temperature_min_range"]
    temp_max_low, temp_max_high = config["temperature_max_range"]

    temperature_min = rng.randint(temp_min_low, temp_min_high)
    temperature_max = rng.randint(
        max(temp_max_low, temperature_min),
        temp_max_high,
    )

    return GeneratedPlanetTraits(
        planet_type=resolved_planet_type,
        radius_km=rng.randint(radius_min, radius_max),
        temperature_min=temperature_min,
        temperature_max=temperature_max,
    )
