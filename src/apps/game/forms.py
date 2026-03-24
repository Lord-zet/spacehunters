from django import forms
from .models import Planet


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
        widget=forms.NumberInput(),
    )
    crystal_to_send = forms.IntegerField(
        label="Ilość kryształu",
        required=False,
        min_value=0,
        widget=forms.NumberInput(),
    )
    target_planet = forms.ModelChoiceField(
        queryset=Planet.objects.none(),
        label="Planeta docelowa",
        empty_label="Wybierz planetę",
    )

    def __init__(self, *args, user=None, source_planet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["target_planet"].queryset = Planet.objects.exclude(
            pk=getattr(source_planet, "pk", None)
        )
        self.user = user
        self.source_planet = source_planet
