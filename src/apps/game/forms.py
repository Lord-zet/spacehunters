from django.contrib.auth.forms import AuthenticationForm
from django import forms
from .models import Planet


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

TAILWIND_FLEET_TARGET_INPUT = (
    "w-full bg-black/60 border border-white/10 rounded px-3 py-2 text-sm focus:border-accent-cyan outline-none appearance-none cursor-pointer"
)

class SendFleetForm(forms.Form):
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
    target_planet = forms.ModelChoiceField(
        queryset=Planet.objects.none(),
        label="Planeta docelowa",
        empty_label="Wybierz planetę",
    )

    def __init__(self, *args, user=None, source_planet=None, **kwargs):
        super().__init__(*args, **kwargs)

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
        self.fields["target_planet"].widget.attrs.update({
            "class": TAILWIND_FLEET_TARGET_INPUT,
            "placeholder": "0",
        })

        self.fields["target_planet"].queryset = Planet.objects.exclude(
            pk=getattr(source_planet, "pk", None)
        )
        self.user = user
        self.source_planet = source_planet

    def clean_metal_to_send(self):
        return self.cleaned_data.get("metal_to_send") or 0

    def clean_crystal_to_send(self):
        return self.cleaned_data.get("crystal_to_send") or 0
