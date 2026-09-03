from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Planet, Fleet
from .forms import RenamePlanetForm, SendFleetForm, ShipConstructionForm
from .buildings import BUILDINGS
from .ships import SHIPS
from .domain_services.fleet import send_transport_fleet, send_stationing_fleet, get_planet_ships_display
from .domain_services.buildings import start_building_upgrade, cancel_building_upgrade
from .domain_services.planets import rename_planet as update_planet_name
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
    get_unread_reports_count,
    get_user_report_or_404,
    get_user_reports,
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
    get_building_cards,
    get_building_card,
    get_building_level_row,
)
from .presenters.reports import (
    get_report_category_tabs,
    get_report_planet_intel_rows,
    get_valid_report_category,
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
    buildings = planet.get_buildings()

    context = {
        "planet": planet,
        "planet_buildings": buildings,
        "building_overview_rows": get_building_cards(buildings, dashboard_only=True, category="production"),
        "background": background,
        "storage_capacities": get_storage_capacities(buildings),
        "active_fleets": active_fleets,
        "field_usage": get_planet_field_usage(planet),
        "energy_balance": get_energy_balance(buildings),
        "planet_trait_rows": get_planet_trait_rows(planet),
        "planet_type_summary": get_planet_type_summary(planet),
        "rename_planet_form": RenamePlanetForm(initial={"name": planet.name}),
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

    buildings = planet.get_buildings()

    background = get_planet_background(planet)

    context = {
        "planet": planet,
        "planet_buildings": buildings,
        "building_in_progress": planet.is_building_in_progress(),
        "background": background,
        "storage_capacities": get_storage_capacities(buildings),
        "field_usage": get_planet_field_usage(planet),
        "energy_balance": get_energy_balance(buildings),
        "building_cards": get_building_cards(buildings),
        "active_building_upgrade": get_active_building_upgrade_summary(buildings)
    }
    return render(request, "game/buildings.html", context)


@login_required
def switch_planet(request, pk):
    planet = get_user_planet_or_404(request.user, pk)
    request.session["active_planet_id"] = planet.id
    return redirect("game:planet_detail", pk=planet.pk)


@login_required
@require_POST
def rename_planet(request, pk):
    planet = get_user_planet_or_404(request.user, pk)
    form = RenamePlanetForm(request.POST, user=request.user, planet=planet)

    if form.is_valid():
        try:
            update_planet_name(planet, form.cleaned_data["name"])
        except DomainError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Nazwa planety została zmieniona.")
    else:
        first_error = next(iter(form.errors.values()))[0]
        messages.error(request, first_error)

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
            ship_quantities = form.get_ship_quantities()
            target_planet = form.cleaned_data.get("target_planet")
            cargo = form.get_cargo()
            speed_profile = form.cleaned_data["speed_profile"]

            MISSION_DISPATCHERS = {
                Fleet.MissionType.STATION: send_stationing_fleet,
                Fleet.MissionType.TRANSPORT: send_transport_fleet,
            }

            dispatcher = MISSION_DISPATCHERS.get(mission_type)

            try:
                if not dispatcher:
                    raise DomainError("Nieobsługiwany typ misji.")

                fleet = dispatcher(
                    source_planet=source_planet,
                    target_planet=target_planet,
                    ship_quantities=ship_quantities,
                    cargo=cargo,
                    user=request.user,
                    speed_profile=speed_profile,
                )

                total_ships = sum(ship_quantities.values())
                messages.success(
                    request,
                    f"Wysłano flotę ({total_ships} szt. statków) "
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

    buildings = source_planet.get_buildings()
    background = get_planet_background(source_planet)

    context = {
        "planet": source_planet,
        "planet_buildings": buildings,
        "form": form,
        "background": background,
        "storage_capacities": get_storage_capacities(buildings),
        "energy_balance": get_energy_balance(buildings),
        "planet_ships": get_planet_ships_display(source_planet, form),
    }
    return render(request, "game/send_fleet.html", context)


@login_required
def fleet_list(request, pk):
    advance_user_state(request.user)

    fleets = get_user_fleets(request.user)
    planet = get_user_planet_or_404(request.user, pk)

    buildings = planet.get_buildings()
    background = get_planet_background(planet)

    context = {
        "fleets": fleets,
        "planet": planet,
        "planet_buildings": buildings,
        "background": background,
        "now": timezone.now(),
        "storage_capacities": get_storage_capacities(buildings),
        "energy_balance": get_energy_balance(buildings),
    }
    return render(request, "game/fleet_list.html", context)


@login_required
def reports(request, pk):
    advance_user_state(request.user)

    planet = get_user_planet_or_404(request.user, pk)
    category = get_valid_report_category(request.GET.get("category"))
    report_list = get_user_reports(request.user, category=category)

    buildings = planet.get_buildings()
    background = get_planet_background(planet)

    context = {
        "planet": planet,
        "planet_buildings": buildings,
        "background": background,
        "storage_capacities": get_storage_capacities(buildings),
        "energy_balance": get_energy_balance(buildings),
        "reports": report_list,
        "active_category": category,
        "category_tabs": get_report_category_tabs(active_category=category),
        "unread_reports_count": get_unread_reports_count(request.user),
    }
    return render(request, "game/reports.html", context)


@login_required
def report_detail(request, pk, report_id):
    advance_user_state(request.user)

    planet = get_user_planet_or_404(request.user, pk)
    report = get_user_report_or_404(request.user, report_id)

    if report.read_at is None:
        report.read_at = timezone.now()
        report.save(update_fields=["read_at"])

    buildings = planet.get_buildings()
    background = get_planet_background(planet)

    context = {
        "planet": planet,
        "planet_buildings": buildings,
        "background": background,
        "storage_capacities": get_storage_capacities(buildings),
        "energy_balance": get_energy_balance(buildings),
        "report": report,
        "planet_intel_rows": get_report_planet_intel_rows(report),
    }
    return render(request, "game/report_detail.html", context)


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

    buildings = planet.get_buildings()

    context = {
        "planet": planet,
        "planet_buildings": buildings,
        "background": background,
        "storage_capacities": get_storage_capacities(buildings),
        "field_usage": get_planet_field_usage(planet),
        "shipyard_ships": shipyard_ships,
        "ship_construction": construction,
        "ship_construction_in_progress": construction.is_in_progress(),
        "active_ship_label": active_ship_label,
        "form": form,
        "energy_balance": get_energy_balance(buildings),
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


@login_required
def building_detail(request, pk, building_code):
    planet = get_user_planet_or_404(request.user, pk)

    advance_result = advance_user_state(request.user, planet=planet)
    planet = advance_result.planet

    request.session["active_planet_id"] = planet.id

    if advance_result.building_finished:
        messages.success(request, "Budowa została zakończona.")

    config = BUILDINGS.get(building_code)
    if config is None:
        raise Http404("Building not found")

    buildings = planet.get_buildings()
    building = get_building_card(buildings, building_code, config)

    current_level = buildings.get_level(config["level_field"])
    next_level = current_level + 1

    level_rows = [
        get_building_level_row(config, level, is_next=(level == next_level))
        for level in range(next_level, next_level + 10)
    ]
    column_names = [
        stat["label"] for stat in level_rows[0]["columns"]
    ] if level_rows else []

    context = {
        "planet": planet,
        "building": building,
        "building_in_progress": planet.is_building_in_progress(),
        "next_level": next_level,
        "level_rows": level_rows,
        "building_in_progress": planet.is_building_in_progress(),
        "storage_capacities": get_storage_capacities(buildings),
        "energy_balance": get_energy_balance(buildings),
        "column_names": column_names,
    }
    return render(request, "game/building_detail.html", context)
