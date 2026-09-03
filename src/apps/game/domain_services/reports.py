from collections.abc import Iterable

from apps.game.models import Planet, Report


REPORT_PAYLOAD_SCHEMA_VERSION = 1
ESPIONAGE_PLANET_SECTION = "planet"


def create_report(
    *,
    owner,
    category: str,
    report_type: str,
    title: str,
    summary: str = "",
    payload: dict | None = None,
    source_planet: Planet | None = None,
    target_planet: Planet | None = None,
    fleet=None,
) -> Report:
    return Report.objects.create(
        owner=owner,
        category=category,
        report_type=report_type,
        title=title,
        summary=summary,
        payload=payload or {},
        source_planet=source_planet,
        target_planet=target_planet,
        fleet=fleet,
    )


def build_planet_intel_section(planet: Planet) -> dict:
    return {
        "planet_type": planet.planet_type,
        "radius_km": planet.radius_km,
        "temperature_min": planet.temperature_min,
        "temperature_max": planet.temperature_max,
    }


def build_espionage_payload(
    *,
    target_planet: Planet,
    sections: Iterable[str] | None = None,
) -> dict:
    section_builders = {
        ESPIONAGE_PLANET_SECTION: lambda: build_planet_intel_section(target_planet),
    }

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


def create_espionage_report(
    *,
    owner,
    source_planet: Planet,
    target_planet: Planet,
    fleet=None,
    sections: Iterable[str] | None = None,
) -> Report:
    payload = build_espionage_payload(
        target_planet=target_planet,
        sections=sections,
    )

    title = f"Raport szpiegowski: {target_planet.name} [{target_planet.coordinates}]"
    summary = "Skan podstawowych parametrow planety zakonczony."

    return create_report(
        owner=owner,
        category=Report.Category.ESPIONAGE,
        report_type=Report.ReportType.PLANET_SCAN,
        title=title,
        summary=summary,
        payload=payload,
        source_planet=source_planet,
        target_planet=target_planet,
        fleet=fleet,
    )
