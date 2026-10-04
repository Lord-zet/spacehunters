from collections.abc import Iterable

from apps.game.domain.reports import build_espionage_payload
from apps.game.models import Planet, Report, SpaceObject


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
    target_object: SpaceObject | None = None,
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
        target_object=target_object,
        fleet=fleet,
    )


def create_espionage_report(
    *,
    owner,
    source_planet: Planet,
    target_planet: Planet | None = None,
    target_object: SpaceObject | None = None,
    fleet=None,
    sections: Iterable[str] | None = None,
) -> Report:
    if target_object is None and target_planet is not None:
        target_object = target_planet.space_object

    target_moon = None
    if target_object is not None and target_object.object_type == SpaceObject.ObjectType.MOON:
        target_moon = target_object.moon

    payload = build_espionage_payload(
        target_planet=target_planet,
        target_moon=target_moon,
        sections=sections,
    )

    if target_planet is not None:
        target_label = f"{target_planet.name} [{target_planet.coordinates}]"
        summary = "Skan podstawowych parametrow planety zakonczony."
        report_type = Report.ReportType.PLANET_SCAN
    elif target_moon is not None:
        target_label = f"Moon [{target_moon.coordinates}]"
        summary = "Skan podstawowych parametrow ksiezyca zakonczony."
        report_type = Report.ReportType.MOON_SCAN
    else:
        target_label = "Nieznany cel"
        summary = "Skan celu zakonczony."
        report_type = Report.ReportType.PLANET_SCAN

    title = f"Raport szpiegowski: {target_label}"

    return create_report(
        owner=owner,
        category=Report.Category.ESPIONAGE,
        report_type=report_type,
        title=title,
        summary=summary,
        payload=payload,
        source_planet=source_planet,
        target_planet=target_planet,
        target_object=target_object,
        fleet=fleet,
    )
