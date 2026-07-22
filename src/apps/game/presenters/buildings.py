from apps.game.domain_services.buildings import get_building_label


def get_active_building_upgrade_summary(planet_buildings) -> dict | None:
    if not planet_buildings.building_type:
        return None

    return {
        "code": planet_buildings.building_type,
        "label": get_building_label(planet_buildings.building_type),
        "ends_at": planet_buildings.building_ends_at,
    }
