from apps.game.domain.exceptions import UnknownFleetSpeedProfileError


DEFAULT_FLEET_SPEED_PROFILE = "standard"


FLEET_SPEED_PROFILES = {
    "economy": {
        "label": "Ekonomiczny",
        "description": "Wolniejszy lot, niższe zużycie helionu.",
        "speed_multiplier": 0.75,
        "fuel_multiplier": 0.65,
        "order": 10,
    },
    "standard": {
        "label": "Standardowy",
        "description": "Domyślny czas lotu i zużycie helionu.",
        "speed_multiplier": 1.0,
        "fuel_multiplier": 1.0,
        "order": 20,
    },
    "fast": {
        "label": "Szybki",
        "description": "Szybszy lot, wyższe zużycie helionu.",
        "speed_multiplier": 1.35,
        "fuel_multiplier": 1.8,
        "order": 30,
    },
}


def get_fleet_speed_profile_config(profile_code: str) -> dict:
    try:
        return FLEET_SPEED_PROFILES[profile_code]
    except KeyError as exc:
        raise UnknownFleetSpeedProfileError(f"Nieznany profil prędkości floty: {profile_code}") from exc


def get_fleet_speed_profile_label(profile_code: str) -> str:
    return get_fleet_speed_profile_config(profile_code)["label"]


def get_fleet_speed_profile_choices() -> list[tuple[str, str]]:
    return [
        (code, config["label"])
        for code, config in sorted(
            FLEET_SPEED_PROFILES.items(),
            key=lambda item: item[1].get("order", 999),
        )
    ]


def get_fleet_speed_multiplier(profile_code: str) -> float:
    return float(get_fleet_speed_profile_config(profile_code)["speed_multiplier"])


def get_fleet_fuel_multiplier(profile_code: str) -> float:
    return float(get_fleet_speed_profile_config(profile_code)["fuel_multiplier"])
