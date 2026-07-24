from django.contrib.auth.forms import AuthenticationForm
from django import forms
from .models import Planet, Fleet

from .ships import SHIPS


TAILWIND_INPUT = (
    "w-full bg-black/40 border border-white/10 rounded px-4 py-3 text-sm "
    "focus:border-accent-cyan outline-none transition-all text-white"
)

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

class SendFleetForm(forms.Form):
    mission_type = forms.ChoiceField(
        choices=Fleet.MissionType.choices,
        initial=Fleet.MissionType.TRANSPORT,
        label="Misja",
    )
    transporter_count = forms.IntegerField(
        label="Ilość transporterów",
        required=True,
        min_value=1,
    )
    metal_to_send = forms.IntegerField(
        label="Ilość metalu",
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(),
    )
    crystal_to_send = forms.IntegerField(
        label="Ilość kryształu",
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(),
    )
    helion_to_send = forms.IntegerField(
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

    def __init__(self, *args, user=None, source_planet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["mission_type"].widget.attrs.update({
            "class": TAILWIND_FLEET_MISSION_TYPE,
            "placeholder": "0",
        })
        self.fields["transporter_count"].widget.attrs.update({
            "class": TAILWIND_FLEET_SHIP_INPUT,
            "placeholder": "0",
        })
        self.fields["metal_to_send"].widget.attrs.update({
            "class": TAILWIND_FLEET_RESOURCE_INPUT,
            "placeholder": "0",
        })
        self.fields["crystal_to_send"].widget.attrs.update({
            "class": TAILWIND_FLEET_RESOURCE_INPUT,
            "placeholder": "0",
        })
        self.fields["helion_to_send"].widget.attrs.update({
            "class": TAILWIND_FLEET_RESOURCE_INPUT,
            "placeholder": "0",
        })
        self.fields["target_planet"].widget.attrs.update({
            "class": TAILWIND_FLEET_TARGET_INPUT,
            "placeholder": "0",
        })

        queryset = Planet.objects.none()
        if user is not None:
            queryset = Planet.objects.filter(owner=user)
            if source_planet is not None:
                queryset = queryset.exclude(pk=source_planet.pk)
        self.fields["target_planet"].queryset = queryset
        self.user = user
        self.source_planet = source_planet

    def clean_metal_to_send(self):
        return self.cleaned_data.get("metal_to_send") or 0

    def clean_crystal_to_send(self):
        return self.cleaned_data.get("crystal_to_send") or 0

    def clean_helion_to_send(self):
        return self.cleaned_data.get("helion_to_send") or 0


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
