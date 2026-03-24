
def metal_mine_production(level):
    return {"metal": int(120 * level * (1.1 ** level))}


def crystal_mine_production(level):
    return {"crystal": int(80 * level * (1.1 ** level))}


BUILDINGS = {
    "metal_mine": {
        "level_field": "metal_mine_level",
        "base_cost": {"metal": 100},
        "build_time": 60,
        "production_fn": metal_mine_production,
    },
    "crystal_mine": {
        "level_field": "crystal_mine_level",
        "base_cost": {"metal": 80},
        "build_time": 90,
        "production_fn": crystal_mine_production,
    },
}