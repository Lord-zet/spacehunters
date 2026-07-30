from apps.game.models import Fleet

def get_user_fleets(user):
    return (
        Fleet.objects
        .filter(owner=user)
        .select_related("source_planet", "target_planet")
        .prefetch_related("ships")
        .order_by("-departure_time")
    )


def get_active_fleets_for_user(user):
    return (
        Fleet.objects
        .filter(owner=user, status__in=[Fleet.Status.OUTBOUND, Fleet.Status.RETURNING])
        .select_related("source_planet", "target_planet")
        .prefetch_related("ships")
        .order_by("-departure_time")
    )
