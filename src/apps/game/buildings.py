
def metal_mine_production(level):
    return {"metal": int(120 * level * (1.1 ** level))}


def crystal_mine_production(level):
    return {"crystal": int(80 * level * (1.1 ** level))}


BUILDINGS = {
    "metal_mine": {
        "level_field": "metal_mine_level",
        "production_fn": metal_mine_production,
    },
    "crystal_mine": {
        "level_field": "crystal_mine_level",
        "production_fn": crystal_mine_production,
    },
}