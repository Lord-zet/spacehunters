from ..buildings import BUILDINGS
from apps.game.domain_services.buildings import get_building_label, get_upgrade_cost, get_upgrade_time
from apps.game.domain_services.resources import get_storage_capacity


def get_storage_capacities(planet):
    return {
        "metal": get_storage_capacity(planet, "metal"),
        "crystal": get_storage_capacity(planet, "crystal"),
        "helion": get_storage_capacity(planet, "helion"),
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

    parts = [
        format_resource_amount(resource, amount)
        for resource, amount in production.items()
    ]

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


def build_storage_stat(planet, config: dict) -> dict | None:
    if config.get("category") != "storage":
        return None

    resource = config.get("resource")

    if not resource:
        return None

    capacity = get_storage_capacity(planet, resource)

    return {
        "label": "Pojemność",
        "value": format_resource_amount(resource, capacity)
    }


def get_building_detail_stats(planet, building_code: str, config: dict, level: int) -> list[dict]:
    stats = []

    production_stat = build_production_stat(config, level)
    if production_stat:
        stats.append(production_stat)

    energy_stat = build_energy_stat(config, level)
    if energy_stat:
        stats.append(energy_stat)

    storage_stat = build_storage_stat(planet, config)
    if storage_stat:
        stats.append(storage_stat)

    build_time = get_upgrade_time(planet, building_code)
    stats.append({
        "label": "Czas budowy",
        "value": format_seconds(build_time),
    })

    cost = get_upgrade_cost(planet, building_code)
    stats.append({
        "label": "Koszt rozbudowy",
        "value": format_cost(cost),
    })

    return stats


def get_building_cards(planet, *, dashboard_only=False, category=None) -> list[dict]:
    planet_buildings = planet.get_buildings()

    cards = []

    for code, config in BUILDINGS.items():
        if dashboard_only and not config.get("dashboard_visible", False):
            continue

        if category is not None and config.get("category") != category:
            continue

        level = getattr(planet_buildings, config["level_field"], 0)
        cards.append({
            "code": code,
            "config": config,
            "level": level,
            "stats": get_building_detail_stats(planet, code, config, level),
            "order": config.get("order", 999),
        })

    return sorted(cards, key=lambda card: card["order"])


def get_active_building_upgrade_summary(planet_buildings) -> dict | None:
    if not planet_buildings.building_type:
        return None

    return {
        "code": planet_buildings.building_type,
        "label": get_building_label(planet_buildings.building_type),
        "ends_at": planet_buildings.building_ends_at,
    }
