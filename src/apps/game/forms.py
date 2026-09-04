from django.contrib.auth.forms import AuthenticationForm
from django import forms
from .models import Planet, Fleet, PLANET_NAME_MAX_LENGTH

from .ships import SHIPS
from apps.game.fleet_speed_profiles import (
    DEFAULT_FLEET_SPEED_PROFILE,
    get_fleet_speed_profile_choices,
)
from .domain_services.resources import Resource


TAILWIND_INPUT = (
    "w-full bg-black/40 border border-white/10 rounded px-4 py-3 text-sm "
    "focus:border-accent-cyan outline-none transition-all text-white"
)


class RenamePlanetForm(forms.Form):
    name = forms.CharField(
        label="Nazwa planety",
        max_length=PLANET_NAME_MAX_LENGTH,
        min_length=2,
        widget=forms.TextInput(attrs={
            "class": TAILWIND_INPUT,
            "placeholder": "Nowa nazwa planety",
            "autocomplete": "off",
            "x-ref": "planetNameInput",
        }),
    )

    def __init__(self, *args, user=None, planet=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.planet = planet

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError("Nazwa planety nie może być pusta.")

        queryset = Planet.objects.filter(name__iexact=name)

        if self.user is not None:
            queryset = queryset.filter(owner=self.user)

        if self.planet is not None:
            queryset = queryset.exclude(pk=self.planet.pk)

        if queryset.exists():
            raise forms.ValidationError("Planeta o podanej nazwie już istnieje.")

        return name


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({
            "class": TAILWIND_INPUT,
            "placeholder": "Wprowadź identyfikator...",
        })

        self.fields["password"].widget.attrs.update({
            "class": TAILWIND_INPUT,
            "placeholder": "••••••••",
        })


TAILWIND_FLEET_RESOURCE_INPUT = (
    "flex-1 bg-black/40 border border-white/10 rounded px-3 py-2 text-sm outline-none focus:border-accent-orange"
)
TAILWIND_FLEET_SHIP_INPUT = (
    "w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-xs focus:border-accent-cyan outline-none transition-all"
)
TAILWIND_FLEET_MISSION_TYPE = (
    "w-full bg-black/60 border border-white/10 rounded px-3 py-2 text-sm focus:border-accent-cyan outline-none appearance-none cursor-pointer"
)
TAILWIND_FLEET_TARGET_INPUT = (
    "w-full bg-black/60 border border-white/10 rounded px-3 py-2 text-sm focus:border-accent-cyan outline-none appearance-none cursor-pointer"
)
TAILWIND_FLEET_SPEED_PROFILE = (
    "w-full bg-black/60 border border-white/10 rounded px-3 py-2 text-sm focus:border-accent-cyan outline-none appearance-none cursor-pointer"
)

class SendFleetForm(forms.Form):
    mission_type = forms.ChoiceField(
        choices=Fleet.MissionType.choices,
        initial=Fleet.MissionType.TRANSPORT,
        label="Misja",
    )
    metal = forms.IntegerField(
        label="Ilość metalu",
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(),
    )
    crystal = forms.IntegerField(
        label="Ilość kryształu",
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(),
    )
    helion = forms.IntegerField(
        label="Ilość Helionu",
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(),
    )
    target_planet = forms.ModelChoiceField(
        queryset=Planet.objects.none(),
        label="Planeta docelowa",
        empty_label="Wybierz planetę",
    )
    speed_profile = forms.ChoiceField(
        choices=get_fleet_speed_profile_choices(),
        initial=DEFAULT_FLEET_SPEED_PROFILE,
        label="Profil prędkości",
    )

    def __init__(self, *args, user=None, source_planet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["mission_type"].widget.attrs.update({
            "class": TAILWIND_FLEET_MISSION_TYPE,
            "placeholder": "0",
        })
        self.fields["metal"].widget.attrs.update({
            "class": TAILWIND_FLEET_RESOURCE_INPUT,
            "placeholder": "0",
        })
        self.fields["crystal"].widget.attrs.update({
            "class": TAILWIND_FLEET_RESOURCE_INPUT,
            "placeholder": "0",
        })
        self.fields["helion"].widget.attrs.update({
            "class": TAILWIND_FLEET_RESOURCE_INPUT,
            "placeholder": "0",
        })
        self.fields["target_planet"].widget.attrs.update({
            "class": TAILWIND_FLEET_TARGET_INPUT,
            "placeholder": "0",
        })
        self.fields["speed_profile"].widget.attrs.update({
            "class": TAILWIND_FLEET_SPEED_PROFILE,
            "placeholder": "0",
        })

        queryset = Planet.objects.none()
        if user is not None:
            queryset = Planet.objects.all()
            if source_planet is not None:
                queryset = queryset.exclude(pk=source_planet.pk)
        self.fields["target_planet"].queryset = queryset
        self.fields["target_planet"].label_from_instance = (
            lambda planet: f"{planet.name} [{planet.coordinates}]"
        )
        self.user = user
        self.source_planet = source_planet

        for ship_code, config in SHIPS.items():
            field_name = f"ship_{ship_code}"
            self.fields[field_name] = forms.IntegerField(
                label=config["label"],
                required=False,
                min_value=0,
                initial=0,
                widget=forms.NumberInput(attrs={
                    "class": TAILWIND_FLEET_SHIP_INPUT
                })
            )

    def clean_metal(self):
        return self.cleaned_data.get("metal") or 0

    def clean_crystal(self):
        return self.cleaned_data.get("crystal") or 0

    def clean_helion(self):
        return self.cleaned_data.get("helion") or 0

    def clean(self):
        cleaned_data = super().clean()
        mission_type = cleaned_data.get("mission_type")
        target_planet = cleaned_data.get("target_planet")

        if (
            mission_type != Fleet.MissionType.ESPIONAGE
            and target_planet is not None
            and self.user is not None
            and target_planet.owner_id != self.user.id
        ):
            raise forms.ValidationError("Ten typ misji można wysłać tylko na własną planetę.")

        if mission_type == Fleet.MissionType.ESPIONAGE:
            cargo_amount = sum(
                cleaned_data.get(resource.value) or 0
                for resource in Resource
            )
            if cargo_amount > 0:
                raise forms.ValidationError("Misja szpiegowska nie może przewozić ładunku.")

        # Walidujemy, czy gracz podał przynajmniej 1 statek jakiegokolwiek typu
        ship_quantities = {
            ship_code: cleaned_data.get(f"ship_{ship_code}") or 0
            for ship_code in SHIPS.keys()
        }
        if sum(ship_quantities.values()) <= 0:
            raise forms.ValidationError("Musisz wybrać co najmniej jeden statek do wysłania.")

        return cleaned_data

    def get_cargo(self) -> dict[Resource, int]:
        if not self.is_valid():
            raise ValueError("Nie można pobrać cargo z niepoprawnego formularza.")
        return {resource: self.cleaned_data[resource.value] for resource in Resource}

    def get_ship_quantities(self) -> dict[str, int]:
        """
        Zwraca słownik {'transporter': 5, 'large_transporter': 2} zawierający tylko
        statki z ilością większą niż 0.
        """
        if not self.is_valid():
            raise ValueError("Nie można pobrać statków z niepoprawnego formularza.")

        return {
            ship_code: self.cleaned_data[f"ship_{ship_code}"]
            for ship_code in SHIPS.keys()
            if self.cleaned_data.get(f"ship_{ship_code}", 0) > 0
        }


class ShipConstructionForm(forms.Form):
    ship_code = forms.ChoiceField(
        label="Ship"
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Quantity"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["ship_code"].choices = [
            (code, config["label"])
            for code, config in SHIPS.items()
        ]
