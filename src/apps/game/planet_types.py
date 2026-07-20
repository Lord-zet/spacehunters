DEFAULT_PLANET_TYPE = "terrestrial"


PLANET_TYPES = {
    "terrestrial": {
        "label": "Planeta skalista",
        "description": "Stabilna planeta o umiarkowanych warunkach.",
        "radius_km_range": (4_500, 8_000),
        "temperature_min_range": (-50, 5),
        "temperature_max_range": (20, 70),
        "order": 10,
    },
    "desert": {
        "label": "Planeta pustynna",
        "description": "Sucha planeta z wysokimi temperaturami dziennymi.",
        "radius_km_range": (4_000, 8_500),
        "temperature_min_range": (-30, 20),
        "temperature_max_range": (50, 110),
        "order": 20,
    },
    "ice": {
        "label": "Planeta lodowa",
        "description": "Zimna planeta o niskich temperaturach powierzchni.",
        "radius_km_range": (3_500, 7_500),
        "temperature_min_range": (-180, -90),
        "temperature_max_range": (-80, -10),
        "order": 30,
    },
    "volcanic": {
        "label": "Planeta wulkaniczna",
        "description": "Niestabilna planeta o bardzo wysokich temperaturach.",
        "radius_km_range": (3_800, 7_800),
        "temperature_min_range": (30, 120),
        "temperature_max_range": (140, 320),
        "order": 40,
    },
    "ocean": {
        "label": "Planeta oceaniczna",
        "description": "Planeta z dominującą powierzchnią wodną.",
        "radius_km_range": (5_000, 9_000),
        "temperature_min_range": (-10, 15),
        "temperature_max_range": (20, 60),
        "order": 50,
    },
    "barren": {
        "label": "Planeta jałowa",
        "description": "Surowa planeta o ubogich warunkach środowiskowych.",
        "radius_km_range": (3_000, 7_000),
        "temperature_min_range": (-80, -10),
        "temperature_max_range": (0, 80),
        "order": 60,
    },
}


def get_planet_type_config(planet_type: str) -> dict:
    try:
        return PLANET_TYPES[planet_type]
    except KeyError as exc:
        raise ValueError(f"Nieznany typ planety: {planet_type}") from exc


def get_planet_type_choices() -> list[tuple[str, str]]:
    return [(code, config["label"])
        for code, config in sorted(
            PLANET_TYPES.items(),
            key=lambda item: item[1].get("order", 999),
        )
    ]
