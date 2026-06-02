from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Planet, Fleet
from .forms import SendFleetForm, ShipConstructionForm
from .buildings import BUILDINGS
from .ships import SHIPS
from .domain_services.fleet import send_transport_fleet, send_stationing_fleet
from .domain_services.buildings import start_building_upgrade, get_upgrade_cost
from .domain_services.resources import get_production_per_hour, get_storage_capacity
from .domain_services.sync import synchronize_planet_state, synchronize_user_state
from .domain_services.shipyard import (
    start_ship_construction,
    get_ship_construction_cost,
    get_ship_construction_time_seconds,
)
from apps.game.domain.exceptions import DomainError
from .selectors import (
    get_active_fleets_for_user,
    get_user_fleets,
    get_user_homeland,
    get_user_planet_or_404,
)


def get_planet_background(planet):
    backgrounds = [
        "game/backgrounds/bg1.jpg",
    ]
    return backgrounds[planet.id % len(backgrounds)]


def get_storage_capacities(planet):
    return {
        "metal": get_storage_capacity(planet, "metal"),
        "crystal": get_storage_capacity(planet, "crystal"),
        "helion": get_storage_capacity(planet, "helion"),
    }


def get_planet_field_usage(planet):
    buildings = planet.get_buildings()
    return {
        "used": buildings.get_used_fields(),
        "free": buildings.get_free_fields(),
        "total": planet.planet_fields_total,
    }


@login_required
def dashboard(request):
    planet = get_user_homeland(request.user)
    if not planet:
        return redirect("login")
    request.session["active_planet_id"] = planet.id
    return redirect("game:planet_detail", pk=planet.pk)


@login_required
def planet_detail(request, pk):
    planet = get_user_planet_or_404(request.user, pk)

    synchronize_user_state(request.user)
    planet, _ = synchronize_planet_state(planet)

    active_fleets = get_active_fleets_for_user(request.user)

    request.session["active_planet_id"] = planet.id

    background = get_planet_background(planet)

    context = {
        "planet": planet,
        "planet_buildings": planet.get_buildings(),
        "background": background,
        "storage_capacities": get_storage_capacities(planet),
        "active_fleets": active_fleets,
        "field_usage": get_planet_field_usage(planet),
    }
    return render(request, "game/planet_detail.html", context)


@login_required
def planet_buildings(request, pk):
    planet = get_user_planet_or_404(request.user, pk)
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
        "planet_buildings": planet.get_buildings(),
        "production": get_production_per_hour(planet),
        "building_costs": building_costs,
        "building_in_progress": planet.is_building_in_progress(),
        "background": background,
        "storage_capacities": get_storage_capacities(planet),
        "field_usage": get_planet_field_usage(planet),
    }
    return render(request, "game/buildings.html", context)


@login_required
def switch_planet(request, pk):
    planet = get_user_planet_or_404(request.user, pk)
    request.session["active_planet_id"] = planet.id
    return redirect("game:planet_detail", pk=planet.pk)


@login_required
def send_fleet(request, pk):
    source_planet = get_user_planet_or_404(request.user, pk)
    source_planet, _ = synchronize_planet_state(source_planet)

    if request.method == "POST":
        form = SendFleetForm(request.POST, user=request.user, source_planet=source_planet)

        if form.is_valid():
            mission_type = form.cleaned_data.get("mission_type")
            tc = form.cleaned_data.get("transporter_count")
            target_planet = form.cleaned_data.get("target_planet")
            metal_to_send = form.cleaned_data.get("metal_to_send")
            crystal_to_send = form.cleaned_data.get("crystal_to_send")

            try:
                if mission_type == Fleet.MissionType.STATION:
                    fleet = send_stationing_fleet(
                        source_planet,
                        target_planet,
                        tc,
                        metal_to_send,
                        crystal_to_send,
                        request.user,
                    )
                    messages.success(
                        request,
                        f"Wysłano flotę ({fleet.transporter_count} szt.) stacjonowania "
                        f"z planety {fleet.source_planet.name} na {fleet.target_planet.name}. "
                        f"Koszt lotu: {fleet.helion_cost} helionu."
                    )
                else:
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
                        f"z planety {fleet.source_planet.name} na {fleet.target_planet.name}. "
                        f"Koszt lotu: {fleet.helion_cost} helionu."
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
        "planet_buildings": source_planet.get_buildings(),
        "form": form,
        "background": background,
        "storage_capacities": get_storage_capacities(source_planet),
    }
    return render(request, "game/send_fleet.html", context)


@login_required
def fleet_list(request, pk):
    synchronize_user_state(request.user)

    fleets = get_user_fleets(request.user)
    planet = get_user_planet_or_404(request.user, pk)

    background = get_planet_background(planet)

    context = {
        "fleets": fleets,
        "planet": planet,
        "planet_buildings": planet.get_buildings(),
        "background": background,
        "now": timezone.now(),
    }
    return render(request, "game/fleet_list.html", context)


@login_required
def planet_shipyard(request, pk):
    planet = get_user_planet_or_404(request.user, pk)

    synchronize_user_state(request.user)
    planet, _ = synchronize_planet_state(planet)

    request.session["active_planet_id"] = planet.id

    if getattr(planet, "_ship_construction_finished", False):
        messages.success(request, "Budowa statków została zakończona.")

    if request.method == "POST":
        form = ShipConstructionForm(request.POST)

        if form.is_valid():
            ship_code = form.cleaned_data["ship_code"]
            quantity = form.cleaned_data["quantity"]

            try:
                start_ship_construction(planet, ship_code, quantity)
                messages.success(request, "Rozpoczęto budowę statków.")
                return redirect("game:shipyard", pk=planet.pk)
            except DomainError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Popraw błędy w formularzu.")
    else:
        form = ShipConstructionForm()

    background = get_planet_background(planet)
    construction = planet.get_ship_construction()

    active_ship_label = ""
    if construction.ship_code:
        active_ship_label = SHIPS.get(construction.ship_code, {}).get("label", construction.ship_code)

    shipyard_ships = {
        code: {
            "config": config,
            "owned_quantity": planet.get_ship_quantity(code),
            "unit_cost": get_ship_construction_cost(code, 1),
            "unit_build_time": get_ship_construction_time_seconds(code, 1),
        }
        for code, config in SHIPS.items()
    }

    context = {
        "planet": planet,
        "planet_buildings": planet.get_buildings(),
        "background": background,
        "storage_capacities": get_storage_capacities(planet),
        "field_usage": get_planet_field_usage(planet),
        "shipyard_ships": shipyard_ships,
        "ship_construction": construction,
        "ship_construction_in_progress": construction.is_in_progress(),
        "active_ship_label": active_ship_label,
        "form": form,
    }
    return render(request, "game/shipyard.html", context)
