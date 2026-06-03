
def calculate_resource_production(level, base_output, exponent):
    if level <= 0:
        return 0
    return int(round(base_output * (level ** exponent)))


def metal_mine_production(level):
    return {"metal": calculate_resource_production(level, 120, 1.18)}


def crystal_mine_production(level):
    return {"crystal": calculate_resource_production(level, 80, 1.17)}


def helion_synthesizer_production(level):
    return {"helion": calculate_resource_production(level, 40, 1.16)}


BUILDINGS = {
    "metal_mine": {
        "level_field": "metal_mine_level",
        "base_cost": {"metal": 100},
        "build_time": 60,
        "build_time_multiplier": 1.4,
        "cost_growth_factor": 1.33,
        "production_fn": metal_mine_production,
    },
    "crystal_mine": {
        "level_field": "crystal_mine_level",
        "base_cost": {"metal": 80},
        "build_time": 90,
        "cost_growth_factor": 1.33,
        "production_fn": crystal_mine_production,
    },
    "helion_synthesizer": {
        "level_field": "helion_synthesizer_level",
        "base_cost": {"metal": 120, "crystal": 80},
        "build_time": 120,
        "build_time_multiplier": 1.4,
        "cost_growth_factor": 1.31,
        "production_fn": helion_synthesizer_production,
    },
    "metal_storage": {
        "level_field": "metal_storage_level",
        "base_cost": {"metal": 120, "crystal": 40},
        "build_time": 75,
        "cost_growth_factor": 1.28,
    },
    "crystal_storage": {
        "level_field": "crystal_storage_level",
        "base_cost": {"metal": 120, "crystal": 80},
        "build_time": 75,
        "cost_growth_factor": 1.28,
    },
    "helion_storage": {
        "level_field": "helion_storage_level",
        "base_cost": {"metal": 160, "crystal": 120},
        "build_time": 90,
        "cost_growth_factor": 1.27,
    },
    "shipyard": {
        "level_field": "shipyard_level",
        "base_cost": {"metal": 400, "crystal": 200},
        "build_time": 180,
        "build_time_multiplier": 1.4,
        "cost_growth_factor": 1.32,
    },
}
