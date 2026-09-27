from collections.abc import Iterable

from apps.game.domain.reports import build_espionage_payload
from apps.game.models import Planet, Report


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
