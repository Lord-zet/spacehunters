from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def time_remaining(value):
    if not value:
        return ""

    now = timezone.now()
    delta = value - now

    total_seconds = int(delta.total_seconds())

    if total_seconds <= 0:
        return "0s"

    if total_seconds < 60:
        return f"{total_seconds}s"

    minutes = total_seconds // 60
    seconds = total_seconds % 60

    return f"{minutes}m {seconds}s"


@register.filter
def format_duration(value):
    try:
        total_seconds = int(value)
    except (TypeError, ValueError):
        return value

    if total_seconds < 0:
        total_seconds = 0

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02}:{minutes:02}:{seconds:02}"
