from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from .buildings import BUILDINGS


class Planet(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="planets"
    )
    name = models.CharField(max_length=100)
    galaxy = models.PositiveIntegerField(default=1)
    system = models.PositiveIntegerField()
    position = models.PositiveIntegerField()
    metal = models.BigIntegerField(default=500)
    crystal = models.BigIntegerField(default=200)
    is_homeland = models.BooleanField(default=False)
    last_resource_update = models.DateTimeField(auto_now_add=True)
    transporter_count = models.PositiveIntegerField(default=0)
    planet_fields_total = models.PositiveIntegerField(default=90)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(is_homeland=True),
                name="unique_homeland_per_owner",
            ),
            models.UniqueConstraint(
                fields=["galaxy", "system", "position"],
                name="unique_planet_coordinates",
            ),
        ]
        ordering = ["galaxy", "system", "position"]

    def clean(self):
        if self.is_homeland:
            qs = Planet.objects.filter(owner=self.owner, is_homeland=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("User can only have one main planet.")

    def get_buildings(self):
        if hasattr(self, "buildings"):
            return self.buildings
        return PlanetBuildings.objects.create(planet=self)

    def is_building_in_progress(self, *, at=None):
        return self.get_buildings().is_building_in_progress(at=at)

    @property
    def coordinates(self):
        return f"{self.galaxy}:{self.system}:{self.position}"

    def __str__(self):
        return self.name


class PlanetBuildings(models.Model):
    planet = models.OneToOneField(
        Planet,
        on_delete=models.CASCADE,
        related_name="buildings",
    )
    metal_mine_level = models.PositiveIntegerField(default=1)
    crystal_mine_level = models.PositiveIntegerField(default=0)
    metal_storage_level = models.PositiveIntegerField(default=1)
    crystal_storage_level = models.PositiveIntegerField(default=1)
    building_type = models.CharField(max_length=50, blank=True, default="")
    building_ends_at = models.DateTimeField(null=True, blank=True)

    def get_level(self, level_field: str) -> int:
        return getattr(self, level_field)

    def is_building_in_progress(self, *, at=None):
        now = at or timezone.now()
        return (
            bool(self.building_type)
            and self.building_ends_at is not None
            and self.building_ends_at > now
        )

    def get_used_fields(self, *, at=None, include_in_progress=True) -> int:
        used_fields = 0

        for config in BUILDINGS.values():
            used_fields += getattr(self, config["level_field"], 0)

        if include_in_progress and self.is_building_in_progress(at=at):
            used_fields += 1

        return used_fields

    def get_free_fields(self, *, at=None, include_in_progress=True) -> int:
        free_fields = self.planet.planet_fields_total - self.get_used_fields(
            at=at,
            include_in_progress=include_in_progress,
        )
        return max(free_fields, 0)

    def has_free_field(self, *, at=None, include_in_progress=True) -> bool:
        return self.get_free_fields(
            at=at,
            include_in_progress=include_in_progress,
        ) > 0

    def __str__(self):
        return f"Buildings<{self.planet_id}>"


class Fleet(models.Model):
    class Status(models.TextChoices):
        OUTBOUND = "outbound", "Outbound"
        RETURNING = "returning", "Returning"
        COMPLETED = "completed", "Completed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fleets"
    )
    source_planet = models.ForeignKey(
        Planet,
        on_delete=models.CASCADE,
        related_name="outgoing_fleets"
    )
    target_planet = models.ForeignKey(
        Planet,
        on_delete=models.CASCADE,
        related_name="incoming_fleets"
    )
    transporter_count = models.BigIntegerField()
    metal = models.BigIntegerField(default=0)
    crystal = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OUTBOUND)
    departure_time = models.DateTimeField(auto_now_add=True)
    arrival_time = models.DateTimeField()
    return_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.source_planet} -> {self.target_planet}"
