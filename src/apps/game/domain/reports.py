from collections.abc import Iterable


REPORT_PAYLOAD_SCHEMA_VERSION = 1
ESPIONAGE_PLANET_SECTION = "planet"
ESPIONAGE_MOON_SECTION = "moon"


def build_planet_intel_section(planet) -> dict:
    return {
        "planet_type": planet.planet_type,
        "radius_km": planet.radius_km,
        "temperature_min": planet.temperature_min,
        "temperature_max": planet.temperature_max,
    }


def build_moon_intel_section(moon) -> dict:
    return {
        "diameter": moon.diameter,
    }


def build_espionage_payload(
    *,
    target_planet=None,
    target_moon=None,
    sections: Iterable[str] | None = None,
) -> dict:
    section_builders = {}

    if target_planet is not None:
        section_builders[ESPIONAGE_PLANET_SECTION] = (
            lambda: build_planet_intel_section(target_planet)
        )

    if target_moon is not None:
        section_builders[ESPIONAGE_MOON_SECTION] = (
            lambda: build_moon_intel_section(target_moon)
        )

    selected_sections = tuple(sections or section_builders.keys())
    unknown_sections = [
        section
        for section in selected_sections
        if section not in section_builders
    ]

    if unknown_sections:
        raise ValueError(f"Nieznane sekcje raportu szpiegowskiego: {', '.join(unknown_sections)}.")

    return {
        "schema_version": REPORT_PAYLOAD_SCHEMA_VERSION,
        "sections": {
            section: section_builders[section]()
            for section in selected_sections
        },
    }
