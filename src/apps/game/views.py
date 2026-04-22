from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Planet
from .forms import SendFleetForm
from .buildings import BUILDINGS
from .domain_services.fleet import send_transport_fleet, user_fleets_qs, active_fleets_qs
from .domain_services.buildings import start_building_upgrade, get_upgrade_cost
from .domain_services.resources import get_production_per_hour, get_storage_capacity
from .domain_services.sync import synchronize_planet_state, synchronize_user_state
from apps.game.domain.exceptions import DomainError


def get_planet_background(planet):
    backgrounds = [
        "game/backgrounds/bg1.jpg",
    ]
    return backgrounds[planet.id % len(backgrounds)]

def get_storage_capacities(planet):
    return {
        "metal": get_storage_capacity(planet, "metal"),
        "crystal": get_storage_capacity(planet, "crystal"),
    }

def get_active_planet(request):
    planet_id = request.session.get("active_planet_id")
    if planet_id:
        planet = Planet.objects.filter(pk=planet_id, owner=request.user).first()
        if planet:
            return planet
    return request.user.planets.filter(is_homeland=True).first()

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
    synchronize_user_state(request.user)
    planet, _ = synchronize_planet_state(planet)

    active_fleets = active_fleets_qs(request.user).order_by("-departure_time")

    request.session["active_planet_id"] = planet.id

    background = get_planet_background(planet)

    context = {
        "planet": planet,
        "background": background,
        "storage_capacities": get_storage_capacities(planet),
        "active_fleets": active_fleets,
    }
    return render(request, "game/planet_detail.html", context)

@login_required
def planet_buildings(request, pk):
    planet = get_object_or_404(Planet, pk=pk, owner=request.user)
    planet, finished = synchronize_planet_state(planet)

    request.session["active_planet_id"] = planet.id

    if finished:
        messages.success(request, "Budowa została zakończona.")

    if request.method == "POST":
        building_name = request.POST.get("building")

        try:
            start_building_upgrade(planet, building_name)
            messages.success(request, f"Rozpoczęto rozbudowę {building_name}.")
        except DomainError as e:
            messages.error(request, str(e))

        return redirect("game:buildings", pk=planet.pk)

    building_costs = {
        name: get_upgrade_cost(planet, name)
        for name in BUILDINGS.keys()
    }

    background = get_planet_background(planet)

    context = {
        "planet": planet,
        "production": get_production_per_hour(planet),
        "building_costs": building_costs,
        "building_in_progress": planet.is_building_in_progress(),
        "background": background,
        "storage_capacities": get_storage_capacities(planet),
    }
    return render(request, "game/buildings.html", context)


@login_required
def switch_planet(request, pk):
    planet = get_object_or_404(Planet, pk=pk, owner=request.user)
    request.session["active_planet_id"] = planet.id
    return redirect("game:planet_detail", pk=planet.pk)

@login_required
def send_fleet(request, pk):
    source_planet = get_object_or_404(Planet, pk=pk, owner=request.user)
    source_planet, _ = synchronize_planet_state(source_planet)

    if request.method == "POST":
        form = SendFleetForm(request.POST, user=request.user, source_planet=source_planet)

        if form.is_valid():
            tc = form.cleaned_data.get("transporter_count")
            target_planet = form.cleaned_data.get("target_planet")
            metal_to_send = form.cleaned_data.get("metal_to_send")
            crystal_to_send = form.cleaned_data.get("crystal_to_send")

            try:
                fleet = send_transport_fleet(
                    source_planet,
                    target_planet,
                    tc,
                    metal_to_send,
                    crystal_to_send,
                    request.user,
                )
                messages.success(
                    request,
                    f"Wysłano flotę ({fleet.transporter_count} szt.) transportową "
                    f"z planety {fleet.source_planet.name} na {fleet.target_planet.name}."
                )
            except Planet.DoesNotExist:
                messages.error(request, "Nie znaleziono planety.")
            except DomainError as e:
                messages.error(request, str(e))

            return redirect("game:send_fleet", pk=source_planet.pk)
    else:
        form = SendFleetForm(user=request.user, source_planet=source_planet)

    background = get_planet_background(source_planet)

    context = {
        "planet": source_planet,
        "form": form,
        "background": background,
    }
    return render(request, "game/send_fleet.html", context)

@login_required
def fleet_list(request, pk):
    synchronize_user_state(request.user)

    fleets = user_fleets_qs(request.user).order_by("-departure_time")
    planet = get_object_or_404(Planet, pk=pk, owner=request.user)

    background = get_planet_background(planet)

    context = {
        "fleets": fleets,
        "planet": planet,
        "background": background,
        "now": timezone.now(),
    }
    return render(request, "game/fleet_list.html", context)
