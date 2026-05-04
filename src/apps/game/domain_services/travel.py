
def calculate_distance(source_planet, target_planet) -> int:
    return abs(source_planet.x - target_planet.x) + abs(source_planet.y - target_planet.y)


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
