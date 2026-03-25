from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Planet
from .forms import SendFleetForm
from .buildings import BUILDINGS
from .services import send_transport_fleet


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
    planet.update_resources()
    planet.save()

    request.session["active_planet_id"] = planet.id

    finished = planet.finish_building_if_ready()
    if finished:
        messages.success(request, "Budowa została zakończona.")

    if request.method == "POST":
        building_name = request.POST.get("building")
        success, msg = planet.start_upgrade(building_name)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)

        return redirect("game:planet_detail", pk=planet.pk)

    building_costs = {
        name: planet.get_upgrade_cost(name)
        for name in BUILDINGS.keys()
    }

    context = {
        "planet": planet,
        "production": planet.get_production_per_hour(),
        "building_costs": building_costs,
        "building_in_progress": planet.is_building_in_progress(),
    }
    return render(request, "game/planet_detail.html", context)

@login_required
def switch_planet(request, pk):
    planet = get_object_or_404(Planet, pk=pk, owner=request.user)
    request.session["active_planet_id"] = planet.id
    return redirect("game:planet_detail", pk=planet.pk)

@login_required
def send_fleet(request, pk):
    source_planet = get_object_or_404(Planet, pk=pk, owner=request.user)
    source_planet.update_resources()
    source_planet.save()

    if request.method == "POST":
        form = SendFleetForm(request.POST, user=request.user, source_planet=source_planet)

        if form.is_valid():
            tc = form.cleaned_data.get("transporter_count")
            target_planet = form.cleaned_data.get("target_planet")
            metal_to_send = form.cleaned_data.get("metal_to_send")
            crystal_to_send = form.cleaned_data.get("crystal_to_send")

            try:
                success, message = send_transport_fleet(source_planet, target_planet, tc, metal_to_send, crystal_to_send, request.user)
            except Planet.DoesNotExist:
                messages.error(request, "Nie znaleziono planety")
                return redirect("game:send_fleet", pk=source_planet.pk)

            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect("game:send_fleet", pk=source_planet.pk)
    else:
        form = SendFleetForm(user=request.user, source_planet=source_planet)
    source_planet.save()
    context = {
        "planet": source_planet,
        "form": form,
        "available_transporters": source_planet.transporter_count,
        "metal": source_planet.metal,
    }
    return render(request, "game/send_fleet.html", context)
