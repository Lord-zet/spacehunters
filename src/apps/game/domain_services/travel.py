GALAXY_DISTANCE_WEIGHT = 20_000
SYSTEM_DISTANCE_WEIGHT = 95
POSITION_DISTANCE_WEIGHT = 5
MIN_DISTANCE = 5


def calculate_distance(source_planet, target_planet) -> int:
    galaxy_gap = abs(source_planet.galaxy - target_planet.galaxy)
    system_gap = abs(source_planet.system - target_planet.system)
    position_gap = abs(source_planet.position - target_planet.position)

    distance = (
        galaxy_gap * GALAXY_DISTANCE_WEIGHT
        + system_gap * SYSTEM_DISTANCE_WEIGHT
        + position_gap * POSITION_DISTANCE_WEIGHT
    )

    return max(distance, MIN_DISTANCE)


def calculate_flight_time_seconds(
    source_planet,
    target_planet,
    speed_multiplier: float = 1.0,
    base_time: int = 60,
    per_distance: int = 30,
) -> int:
    distance = calculate_distance(source_planet, target_planet)
    raw_time = base_time + distance * per_distance
    return max(1, int(raw_time / speed_multiplier))
