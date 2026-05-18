from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone


class Planet(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="planets"
    )
    name = models.CharField(max_length=100)
    x = models.IntegerField()
    y = models.IntegerField()
    metal = models.BigIntegerField(default=500)
    crystal = models.BigIntegerField(default=200)
    metal_mine_level = models.PositiveIntegerField(default=1)
    crystal_mine_level = models.PositiveIntegerField(default=0)
    metal_storage_level = models.PositiveIntegerField(default=1)
    crystal_storage_level = models.PositiveIntegerField(default=1)
    is_homeland = models.BooleanField(default=False)
    last_resource_update = models.DateTimeField(auto_now_add=True)
    building_type = models.CharField(max_length=50, blank=True, default="")
    building_ends_at = models.DateTimeField(null=True, blank=True)
    transporter_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(is_homeland=True),
                name="unique_homeland_per_owner",
            )
        ]
        ordering = ["x", "y"]

    def clean(self):
        if self.is_homeland:
            qs = Planet.objects.filter(owner=self.owner, is_homeland=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("User can only have one main planet.")

    def is_building_in_progress(self):
        return self.building_ends_at is not None and self.building_ends_at > timezone.now()

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

    def is_building_in_progress(self, *, at=None):
        now = at or timezone.now()
        return self.building_ends_at is not None and self.building_ends_at > now

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
