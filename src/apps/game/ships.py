def transporter_total_cargo(quantity: int) -> int:
    return 1000 * quantity


SHIPS = {
    "transporter": {
        "label": "Transporter",
        "cargo_capacity": 1000,
        "base_speed": 1.0,
        "fuel_burn": 10,
        "build_time": 120,
        "required_shipyard_level": 1,
        "base_cost": {
            "metal": 2000,
            "crystal": 1000,
            "helion": 0,
        },
    },
}
