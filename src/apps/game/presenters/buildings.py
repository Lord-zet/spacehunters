from ..buildings import BUILDINGS
from apps.game.domain_services.buildings import (
    get_build_cost_for_level,
    get_build_time_for_level,
    get_building_label,
)
from apps.game.domain_services.resources import get_storage_capacity, get_storage_capacity_for_level


def get_storage_capacities(buildings):
    return {
        "metal": get_storage_capacity(buildings, "metal"),
        "crystal": get_storage_capacity(buildings, "crystal"),
        "helion": get_storage_capacity(buildings, "helion"),
    }


RESOURCE_LABELS = {
    "metal": "M:",
    "crystal": "K:",
    "helion": "H:",
}


def format_seconds(seconds: int | None) -> str:
    if seconds is None:
        return "-"

    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}h {minutes}m"

    if minutes:
        return f"{minutes}m {sec}s"

    return f"{sec}s"


def format_resource_amount(resource: str, amount: int) -> str:
    label = RESOURCE_LABELS.get(resource, resource)
    return f"{label} {amount}"


def format_cost(cost: dict[str, int] | None) -> str:
    if not cost:
        return "-"

    return " | ".join(
        format_resource_amount(resource, amount)
        for resource, amount in cost.items()
    )


def build_production_stat(config: dict, level: int) -> dict | None:
    production_fn = config.get("production_fn")

    if not production_fn:
        return None

    production = production_fn(level)

    if not production:
        return None

    parts = [str(amount) for resource, amount in production.items()]

    return {
        "label": "Produkcja/h",
        "value": ", ".join(parts),
    }


def build_energy_stat(config: dict, level: int) -> dict | None:
    energy_production_fn = config.get("energy_production_fn")

    if not energy_production_fn:
        return None

    return {
        "label": "Produkcja energii",
        "value": f"{energy_production_fn(level)}",
    }


def build_storage_stat(config: dict, level: int) -> dict | None:
    if config.get("category") != "storage":
        return None

    resource = config.get("resource")

    if not resource:
        return None

    capacity = get_storage_capacity_for_level(level)

    return {
        "label": "Pojemność",
        "value": str(capacity)
    }


def get_building_level_stats(config: dict, level: int) -> list[dict]:
    stats = []

    production_stat = build_production_stat(config, level)
    if production_stat:
        stats.append(production_stat)

    energy_stat = build_energy_stat(config, level)
    if energy_stat:
        stats.append(energy_stat)

    storage_stat = build_storage_stat(config, level)
    if storage_stat:
        stats.append(storage_stat)

    return stats


def get_building_upgrade_stats(config: dict, target_level: int) -> list[dict]:
    stats = []

    build_time = get_build_time_for_level(config, target_level)
    stats.append({
        "label": "Czas budowy",
        "value": format_seconds(build_time),
    })

    cost = get_build_cost_for_level(config, target_level)
    stats.append({
        "label": "Koszt rozbudowy",
        "value": format_cost(cost),
    })

    return stats


def get_building_detail_stats(config: dict, level: int) -> list[dict]:
    target_level = level + 1
    return [
        *get_building_level_stats(config, level),
        *get_building_upgrade_stats(config, target_level),
    ]


def get_building_level_row(config: dict, level: int) -> dict:
    return {
        "level": level,
        "stats": get_building_level_stats(config, level),
        "upgrade_stats": get_building_upgrade_stats(config, level),
    }


def get_building_card(buildings, building_code, config):
    level = buildings.get_level(config['level_field'])

    return {
            "code": building_code,
            "config": config,
            "level": level,
            "stats": get_building_detail_stats(config, level),
            "order": config.get("order", 999),
        }


def get_building_cards(buildings, dashboard_only=False, category=None):
    cards = []

    for code, config in BUILDINGS.items():
        if dashboard_only and not config.get("dashboard_visible", False):
            continue

        if category is not None and config.get("category") != category:
            continue

        cards.append(get_building_card(buildings, code, config))

    return sorted(cards, key=lambda card: card["order"])


def get_active_building_upgrade_summary(planet_buildings) -> dict | None:
    if not planet_buildings.building_type:
        return None

    return {
        "code": planet_buildings.building_type,
        "label": get_building_label(planet_buildings.building_type),
        "ends_at": planet_buildings.building_ends_at,
    }
