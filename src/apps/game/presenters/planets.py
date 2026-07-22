from apps.game.planet_types import get_planet_type_config


def get_planet_background(planet):
    backgrounds = [
        "game/backgrounds/bg1.jpg",
    ]
    return backgrounds[planet.id % len(backgrounds)]


def get_planet_field_usage(planet):
    buildings = planet.get_buildings()
    return {
        "used": buildings.get_used_fields(),
        "free": buildings.get_free_fields(),
        "total": planet.planet_fields_total,
    }


def format_temperature_range(temperature_min: int, temperature_max: int) -> str:
    return f"{temperature_min}°C do {temperature_max}°C"


def format_radius(radius_km: int) -> str:
    return f"{radius_km:,} km".replace(",", " ")


def get_planet_trait_rows(planet) -> list[dict]:
    return [
        {
            "label": "Typ planety",
            "value": get_planet_type_config(planet.planet_type)["label"],
        },
        {
            "label": "Promień",
            "value": format_radius(planet.radius_km),
        },
        {
            "label": "Temperatura",
            "value": format_temperature_range(
                planet.temperature_min,
                planet.temperature_max,
            ),
        },
    ]


def get_planet_type_summary(planet) -> dict:
    return {
        "code": planet.planet_type,
        "label": get_planet_type_config(planet.planet_type)["label"],
        "description": get_planet_type_config(planet.planet_type)["description"],
    }
