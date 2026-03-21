from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Planet


def get_active_planet(request):
    planet_id = request.session.get("active_planet_id")
    if planet_id:
        planet = Planet.objects.filter(pk=planet_id, owner=request.user).first()
        if planet:
            return planet
    return request.user.planets.filter(is_main=True).first()

@login_required
def dashboard(request):
    planet = request.user.planets.filter(is_homeland=True).first()
    if not planet:
        return redirect("login")
    request.session["active_planet_id"] = planet.id
    return redirect("game:planet_detail", pk=planet.pk)

@login_required
def planet_detail(request, pk):
    planet = get_object_or_404(Planet, pk=pk, owner=request.user)
    request.session["active_planet_id"] = planet.id
    return render(request, "game/planet_detail.html", {"planet": planet})

@login_required
def switch_planet(request, pk):
    planet = get_object_or_404(Planet, pk=pk, owner=request.user)
    request.session["active_planet_id"] = planet.id
    return redirect("game:planet_detail", pk=planet.pk)
