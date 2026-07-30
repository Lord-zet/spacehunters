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
        "description": ""
                       "Szybki, lekko opancerzony statek transportowy. Optymalny do transportu "
                       "ładunku między skolonizowanymi światami.",
        "thumb": "game/ships/transporter_thumb.png",
        "base_cost": {
            "metal": 2000,
            "crystal": 1000,
            "helion": 0,
        },
    },
    "large_transporter": {
        "label": "Duży Transporter",
        "cargo_capacity": 5000,
        "base_speed": 0.8,
        "fuel_burn": 30,
        "build_time": 480,
        "required_shipyard_level": 3,
        "description": ""
                       "Potężny statek handlowy o wzmocnionym pancerzu. Wolniejszy niż jego mniejszy odpowiednik, "
                       "ale potrafi przetransportować znacznie większe ilości surowców.",
        "thumb": "game/ships/large_transporter_thumb.png",
        "base_cost": {
            "metal": 6000,
            "crystal": 4000,
            "helion": 0,
        },
    },
}
