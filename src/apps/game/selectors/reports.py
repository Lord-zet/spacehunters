from django.shortcuts import get_object_or_404

from apps.game.models import Report


def get_user_reports(user, *, category: str | None = None):
    reports = (
        Report.objects
        .filter(owner=user)
        .select_related("source_planet", "target_planet", "fleet")
        .order_by("-created_at")
    )

    if category:
        reports = reports.filter(category=category)

    return reports


def get_user_report_or_404(user, pk):
    return get_object_or_404(
        Report.objects.select_related("source_planet", "target_planet", "fleet"),
        owner=user,
        pk=pk,
    )


def get_unread_reports_count(user, *, category: str | None = None) -> int:
    reports = Report.objects.filter(owner=user, read_at__isnull=True)

    if category:
        reports = reports.filter(category=category)

    return reports.count()
