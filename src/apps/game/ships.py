def transporter_total_cargo(quantity: int) -> int:
    return 1000 * quantity


SHIPS = {
    "transporter": {
        "label": "Transporter",
        "cargo_capacity": 1000,
        "base_speed": 1.0,
        "fuel_burn": 10,
        "base_cost": {
            "metal": 2000,
            "crystal": 1000,
            "helion": 0,
        },
    },
}
