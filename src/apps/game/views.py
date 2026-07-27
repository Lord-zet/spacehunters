from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Planet, Fleet
from .forms import SendFleetForm, ShipConstructionForm
from .buildings import BUILDINGS
from .ships import SHIPS
from .domain_services.fleet import send_transport_fleet, send_stationing_fleet
from .domain_services.buildings import start_building_upgrade, get_upgrade_cost, get_upgrade_time, cancel_building_upgrade
from .domain_services.resources import get_production_per_hour, get_storage_capacity
from .domain_services.sync import advance_user_state
from .domain_services.shipyard import (
    start_ship_construction,
    get_ship_construction_cost,
    get_ship_construction_time_seconds,
)
from .domain_services.energy import get_energy_balance
from apps.game.domain.exceptions import DomainError
from .selectors import (
    get_active_fleets_for_user,
    get_user_fleets,
    get_user_homeland,
    get_user_planet_or_404,
)
from .presenters.planets import (
    get_planet_trait_rows,
    get_planet_type_summary,
    get_planet_background,
    get_planet_field_usage
)
from .presenters.buildings import (
    get_active_building_upgrade_summary,
    get_storage_capacities,
    get_building_cards
)


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

    advance_result = advance_user_state(request.user, planet=planet)
    planet = advance_result.planet

    active_fleets = get_active_fleets_for_user(request.user)

    request.session["active_planet_id"] = planet.id

    background = get_planet_background(planet)

    context = {
        "planet": planet,
        "planet_buildings": planet.get_buildings(),
        "building_overview_rows": get_building_cards(planet, dashboard_only=True, category="production"),
        "background": background,
        "storage_capacities": get_storage_capacities(planet),
        "active_fleets": active_fleets,
        "field_usage": get_planet_field_usage(planet),
        "energy_balance": get_energy_balance(planet),
        "planet_trait_rows": get_planet_trait_rows(planet),
        "planet_type_summary": get_planet_type_summary(planet),
    }
    return render(request, "game/planet_detail.html", context)


@login_required
def planet_buildings(request, pk):
    planet = get_user_planet_or_404(request.user, pk)

    advance_result = advance_user_state(request.user, planet=planet)
    planet = advance_result.planet

    request.session["active_planet_id"] = planet.id

    if advance_result.building_finished:
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
    building_time = {
        name: get_upgrade_time(planet, name)
        for name in BUILDINGS.keys()
    }

    background = get_planet_background(planet)

    context = {
        "planet": planet,
        "planet_buildings": planet.get_buildings(),
        "building_in_progress": planet.is_building_in_progress(),
        "background": background,
        "storage_capacities": get_storage_capacities(planet),
        "field_usage": get_planet_field_usage(planet),
        "building_time": building_time,
        "energy_balance": get_energy_balance(planet),
        "building_cards": get_building_cards(planet),
        "active_building_upgrade": get_active_building_upgrade_summary(planet.get_buildings())
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

    advance_result = advance_user_state(request.user, planet=source_planet)
    source_planet = advance_result.planet

    if request.method == "POST":
        form = SendFleetForm(request.POST, user=request.user, source_planet=source_planet)

        if form.is_valid():
            mission_type = form.cleaned_data.get("mission_type")
            tc = form.cleaned_data.get("transporter_count")
            target_planet = form.cleaned_data.get("target_planet")
            metal_to_send = form.cleaned_data.get("metal_to_send")
            crystal_to_send = form.cleaned_data.get("crystal_to_send")
            helion_to_send = form.cleaned_data.get("helion_to_send")
            speed_profile = form.cleaned_data["speed_profile"]

            try:
                if mission_type == Fleet.MissionType.STATION:
                    fleet = send_stationing_fleet(
                        source_planet,
                        target_planet,
                        tc,
                        metal_to_send,
                        crystal_to_send,
                        helion_to_send,
                        request.user,
                        speed_profile,
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
                        helion_to_send,
                        request.user,
                        speed_profile,
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
        "energy_balance": get_energy_balance(source_planet),
    }
    return render(request, "game/send_fleet.html", context)


@login_required
def fleet_list(request, pk):
    advance_user_state(request.user)

    fleets = get_user_fleets(request.user)
    planet = get_user_planet_or_404(request.user, pk)

    background = get_planet_background(planet)

    context = {
        "fleets": fleets,
        "planet": planet,
        "planet_buildings": planet.get_buildings(),
        "background": background,
        "now": timezone.now(),
        "storage_capacities": get_storage_capacities(planet),
        "energy_balance": get_energy_balance(planet),
    }
    return render(request, "game/fleet_list.html", context)


@login_required
def planet_shipyard(request, pk):
    planet = get_user_planet_or_404(request.user, pk)

    advance_result = advance_user_state(request.user, planet=planet)
    planet = advance_result.planet

    request.session["active_planet_id"] = planet.id

    if advance_result.ship_construction_finished:
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
        "energy_balance": get_energy_balance(planet),
    }
    return render(request, "game/shipyard.html", context)


@login_required
@require_POST
def cancel_building(request, pk):
    planet = get_user_planet_or_404(request.user, pk)
    now = timezone.now()

    advance_result = advance_user_state(request.user, planet=planet, at=now)
    planet = advance_result.planet

    try:
        cancellation = cancel_building_upgrade(planet, at=now)
    except DomainError as exc:
        messages.error(request, str(exc))
    else:
        refund_text = ", ".join(
            f"{amount} {resource}"
            for resource, amount in cancellation.refund.items()
        )

        if not refund_text:
            refund_text = "brak"

        messages.success(
            request, f"Anulowano budowę: {cancellation.building_type}.\nZwrot: {refund_text}."
        )

    return redirect("game:buildings", pk=planet.pk)
