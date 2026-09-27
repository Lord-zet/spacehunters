def get_next_due_planet_event_time(
    *,
    buildings,
    ship_construction,
    target_time,
):
    candidates = []

    if (
        buildings.building_ends_at is not None
        and buildings.building_ends_at <= target_time
    ):
        candidates.append(buildings.building_ends_at)

    if (
        ship_construction.ends_at is not None
        and ship_construction.ends_at <= target_time
    ):
        candidates.append(ship_construction.ends_at)

    return min(candidates) if candidates else None
