
from dataclasses import dataclass


EARLY_COST_MULTIPLIERS = [
    1.0,   # lvl 1
    2.5,   # lvl 2
    4.5,   # lvl 3
    7.0,   # lvl 4
    10.0,  # lvl 5
]

DEFAULT_COST_GROWTH_FACTOR = 1.33

DEFAULT_BUILD_TIME_MULTIPLIER = 1.3

BUILDING_CANCEL_REFUND_PERCENT = 50


@dataclass(frozen=True, slots=True)
class BuildingCancellationResult:
    building_type: str
    paid_cost: dict[str, int]
    refund: dict[str, int]


def calculate_resource_production(level, base_output, exponent):
    if level <= 0:
        return 0
    return int(round(base_output * (level ** exponent)))


def make_resource_production_fn(resource, base_output, exponent):
    def production(level):
        return {
            resource: calculate_resource_production(level, base_output, exponent)
        }
    return production


def metal_mine_production(level):
    return {"metal": calculate_resource_production(level, 120, 1.18)}


def crystal_mine_production(level):
    return {"crystal": calculate_resource_production(level, 80, 1.17)}


def helion_synthesizer_production(level):
    return {"helion": calculate_resource_production(level, 40, 1.16)}


def calculate_energy_value(level, base_value, exponent):
    if level <= 0:
        return 0

    return int(round(base_value * (level ** exponent)))


def make_energy_production_fn(base_output, exponent):
    def production(level):
        return calculate_energy_value(level, base_output, exponent)

    return production


def make_energy_consumption_fn(base_usage, exponent):
    def consumption(level):
        return calculate_energy_value(level, base_usage, exponent)

    return consumption


def round_building_cost(value: float) -> int:
    if value < 1000:
        return int(round(value))
    if value < 10000:
        return int(round(value / 50) * 50)
    if value < 100000:
        return int(round(value / 100) * 100)
    return int(round(value / 500) * 500)


def get_upgrade_cost_multiplier(
    next_level: int,
    growth_factor: float = DEFAULT_COST_GROWTH_FACTOR,
) -> float:
    if next_level <= len(EARLY_COST_MULTIPLIERS):
        return EARLY_COST_MULTIPLIERS[next_level - 1]

    anchor_multiplier = EARLY_COST_MULTIPLIERS[-1]
    extra_levels = next_level - len(EARLY_COST_MULTIPLIERS)
    return anchor_multiplier * (growth_factor ** extra_levels)


def calculate_build_cost(
    target_level: int,
    base_cost: dict[str, int],
    growth_factor: float = DEFAULT_COST_GROWTH_FACTOR,
) -> dict[str, int]:
    """
    Cost of reaching target_level.

    Example:
        calculate_build_cost(3, ...)
        -> cost of upgrade 2 -> 3
    """
    if target_level <= 0:
        raise ValueError("target_level must be greater than 0")

    level_multiplier = get_upgrade_cost_multiplier(
        target_level,
        growth_factor=growth_factor,
    )

    result = {}

    for resource, base in base_cost.items():
        raw_cost = base * level_multiplier

        if target_level <= len(EARLY_COST_MULTIPLIERS):
            result[resource] = int(round(raw_cost))
        else:
            result[resource] = round_building_cost(raw_cost)

    return result


def get_building_config(building_name):
    return BUILDINGS.get(building_name)


def get_building_label(building_name: str) -> str:
    config = get_building_config(building_name)
    return config.get("label", building_name)


def get_build_cost_for_level(config: dict, target_level: int) -> dict[str, int]:
    growth_factor = config.get("cost_growth_factor", DEFAULT_COST_GROWTH_FACTOR)
    return calculate_build_cost(
        target_level,
        config["base_cost"],
        growth_factor=growth_factor,
    )


def calculate_build_time(
    target_level: int,
    base_build_time: int,
    multiplier: float = DEFAULT_BUILD_TIME_MULTIPLIER,
) -> int:
    """
    Time needed to reach target_level.

    Example:
        calculate_build_time(3, ...)
        -> duration of upgrade 2 -> 3
    """
    if target_level <= 0:
        raise ValueError("target_level must be greater than 0")

    return int(base_build_time * (multiplier ** target_level))


def get_build_time_for_level(config: dict, target_level: int) -> int:
    multiplier = config.get("build_time_multiplier", DEFAULT_BUILD_TIME_MULTIPLIER)
    return calculate_build_time(target_level, config["build_time"], multiplier)


def calculate_building_cancel_refund(paid_cost, *, refund_percent=BUILDING_CANCEL_REFUND_PERCENT):
    return {
        resource: amount * refund_percent // 100
        for resource, amount in paid_cost.items()
        if amount > 0
    }


BUILDINGS = {
    "metal_mine": {
        "label": "Kopalnia metalu",
        "category": "production",
        "dashboard_visible": True,
        "level_field": "metal_mine_level",
        "base_cost": {"metal": 100},
        "build_time": 60,
        "build_time_multiplier": 1.4,
        "cost_growth_factor": 1.33,
        "production_fn": make_resource_production_fn("metal", 120, 1.18),
        "energy_consumption_fn": make_energy_consumption_fn(8, 1.12),
        "description": ""
                       "Głębokie odwierty w skorupie planety pozwalające na wydobycie podstawowych rud żelaza "
                       "niezbędnych do budowy floty i struktur.",
        "thumb": "game/buildings/metal_mine_thumb.png",
    },
    "crystal_mine": {
        "label": "Kopalnia kryształu",
        "category": "production",
        "dashboard_visible": True,
        "level_field": "crystal_mine_level",
        "base_cost": {"metal": 80},
        "build_time": 90,
        "cost_growth_factor": 1.33,
        "production_fn": make_resource_production_fn("crystal", 80, 1.17),
        "energy_consumption_fn": make_energy_consumption_fn(10, 1.12),
        "description": ""
                       "Kryształy są głównym nośnikiem energii w obwodach elektronicznych. "
                       "Wydobywane z rzadkich formacji kwarcowych.",
        "thumb": "game/buildings/crystal_mine_thumb.png",
    },
    "helion_synthesizer": {
        "label": "Syntezator Helionu",
        "category": "production",
        "dashboard_visible": True,
        "level_field": "helion_synthesizer_level",
        "base_cost": {"metal": 120, "crystal": 80},
        "build_time": 120,
        "build_time_multiplier": 1.4,
        "cost_growth_factor": 1.31,
        "production_fn": make_resource_production_fn("helion", 40, 1.16),
        "energy_consumption_fn": make_energy_consumption_fn(16, 1.14),
        "description": ""
                       "Helion jest paliwem wykorzystywanym przez wszystkie statki.",
        "thumb": "game/buildings/helion_synthesizer_thumb.png",
    },
    "solar_array": {
        "label": "Elektrownia słoneczna",
        "category": "production",
        "dashboard_visible": True,
        "level_field": "solar_array_level",
        "base_cost": {"metal": 180, "crystal": 60},
        "build_time": 90,
        "build_time_multiplier": 1.35,
        "cost_growth_factor": 1.30,
        "energy_production_fn": make_energy_production_fn(40, 1.18),
        "description": ""
                       "Elektrownia produkuje energię niezbędną dla każdego budynku produkcyjnego.",
        "thumb": "game/buildings/solar_array_thumb.png",
    },
    "metal_storage": {
        "label": "Magazyn metalu",
        "category": "storage",
        "resource": "metal",
        "dashboard_visible": True,
        "level_field": "metal_storage_level",
        "base_cost": {"metal": 120, "crystal": 40},
        "build_time": 75,
        "cost_growth_factor": 1.28,
        "description": ""
                       "Ogromne silosy przeznaczone do bezpiecznego przechowywania rudy. "
                       "Zwiększa limit maksymalnego składowania metalu.",
        "thumb": "game/buildings/metal_storage_thumb.png",
    },
    "crystal_storage": {
        "label": "Magazyn kryształu",
        "category": "storage",
        "resource": "crystal",
        "dashboard_visible": True,
        "level_field": "crystal_storage_level",
        "base_cost": {"metal": 120, "crystal": 80},
        "build_time": 75,
        "cost_growth_factor": 1.28,
        "description": ""
                       "Termicznie izolowane komory chroniące strukturę krystaliczną przed "
                       "degradacją spowodowaną wahaniami temperatur.",
        "thumb": "game/buildings/crystal_storage_thumb.png",
    },
    "helion_storage": {
        "label": "Magazyn Helionu",
        "category": "storage",
        "resource": "helion",
        "dashboard_visible": True,
        "level_field": "helion_storage_level",
        "base_cost": {"metal": 160, "crystal": 120},
        "build_time": 90,
        "cost_growth_factor": 1.27,
        "description": ""
                       "Specjalne zbiorniki przystosowane do magazynowania ciekłego paliwa.",
        "thumb": "game/buildings/helion_storage_thumb.png",
    },
    "shipyard": {
        "label": "Stocznia",
        "category": "infrastructure",
        "dashboard_visible": True,
        "level_field": "shipyard_level",
        "base_cost": {"metal": 400, "crystal": 200},
        "build_time": 180,
        "build_time_multiplier": 1.4,
        "cost_growth_factor": 1.32,
        "description": ""
                       "Stocznia umożliwa budowę wszelkiego rodzaju statków - od transporterów po okręty wojenne.",
        "thumb": "game/buildings/shipyard_thumb.png",
    },
}
