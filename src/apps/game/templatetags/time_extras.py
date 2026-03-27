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
