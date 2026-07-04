
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
    },
    "metal_storage": {
        "label": "Magazyn metalu",
        "category": "production",
        "dashboard_visible": True,
        "level_field": "metal_storage_level",
        "base_cost": {"metal": 120, "crystal": 40},
        "build_time": 75,
        "cost_growth_factor": 1.28,
    },
    "crystal_storage": {
        "label": "Magazyn kryształu",
        "category": "production",
        "dashboard_visible": True,
        "level_field": "crystal_storage_level",
        "base_cost": {"metal": 120, "crystal": 80},
        "build_time": 75,
        "cost_growth_factor": 1.28,
    },
    "helion_storage": {
        "label": "Magazyn Helionu",
        "category": "production",
        "dashboard_visible": True,
        "level_field": "helion_storage_level",
        "base_cost": {"metal": 160, "crystal": 120},
        "build_time": 90,
        "cost_growth_factor": 1.27,
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
    },
}
