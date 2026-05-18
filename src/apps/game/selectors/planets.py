from django.shortcuts import get_object_or_404

from apps.game.models import Planet


def get_user_planet_or_404(user, pk):
    return get_object_or_404(
        Planet.objects.select_related("buildings"),
        owner=user,
        pk=pk,
    )


def get_user_homeland(user):
    return (
        Planet.objects
        .select_related("buildings")
        .filter(owner=user, is_homeland=True)
        .first()
    )


def get_active_planet_from_session(request):
    planet_id = request.session.get("active_planet_id")
    if planet_id:
        planet = (
            Planet.objects
            .select_related("owner")
            .filter(pk=planet_id, owner=request.user)
            .first()
        )
        if planet:
            return planet

    return get_user_homeland(request.user)


def get_user_planets(user):
    return user.planets.order_by("x", "y")
