from apps.game.models import Report


REPORT_CATEGORY_TABS = (
    {
        "category": Report.Category.ESPIONAGE.value,
        "label": Report.Category.ESPIONAGE.label,
    },
)


def get_report_category_tabs(*, active_category: str):
    return [
        {
            **tab,
            "is_active": tab["category"] == active_category,
        }
        for tab in REPORT_CATEGORY_TABS
    ]


def get_default_report_category() -> str:
    return Report.Category.ESPIONAGE.value


def get_valid_report_category(category: str | None) -> str:
    valid_categories = {tab["category"] for tab in REPORT_CATEGORY_TABS}

    if category in valid_categories:
        return category

    return get_default_report_category()


def get_report_planet_intel_rows(report: Report) -> list[dict]:
    sections = report.payload.get("sections", {})
    moon_section = sections.get("moon")

    if moon_section is not None:
        return [
            {
                "label": "Średnica",
                "value": f"{moon_section.get('diameter', '-')} km",
            },
        ]

    planet_section = sections.get("planet", {})

    return [
        {
            "label": "Typ planety",
            "value": planet_section.get("planet_type", "-"),
        },
        {
            "label": "Promień",
            "value": f"{planet_section.get('radius_km', '-')} km",
        },
        {
            "label": "Temperatura min.",
            "value": f"{planet_section.get('temperature_min', '-')} C",
        },
        {
            "label": "Temperatura max.",
            "value": f"{planet_section.get('temperature_max', '-')} C",
        },
    ]
