from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from .buildings import BUILDINGS

TRANSPORTER_CAPACITY = 1000


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


    def get_storage_capacity(self, resource):
        storage_levels = {
            "metal": self.metal_storage_level,
            "crystal": self.crystal_storage_level,
        }
        level = storage_levels.get(resource, 0)

        base_capacity = 5000
        return int(base_capacity * (1.5 ** level))

    def update_resources(self):
        now = timezone.now()
        elapsed_seconds = (now - self.last_resource_update).total_seconds()

        if elapsed_seconds <= 0:
            return

        production = self.get_production_per_hour()

        for resource, per_hour in production.items():
            gain = int(per_hour * elapsed_seconds / 3600)
            if gain <= 0:
                continue

            current_amount = getattr(self, resource, 0)
            capacity = self.get_storage_capacity(resource)
            free_space = max(capacity - current_amount, 0)

            actual_gain = min(gain, free_space)
            setattr(self, resource, current_amount + actual_gain)

        self.last_resource_update = now

    def get_production_per_hour(self):
        total = {}
        for building_name, config in BUILDINGS.items():
            level = getattr(self, config["level_field"])

            production_fn = config.get("production_fn")
            if not production_fn:
                continue
            production = production_fn(level)

            for resource, amount in production.items():
                total[resource] = total.get(resource, 0) + amount
        return total

    def is_building_in_progress(self):
        return self.building_ends_at is not None and self.building_ends_at > timezone.now()

    def has_enough_resources_for_transport(self, metal, crystal):
        return self.metal >= metal and self.crystal >= crystal

    def has_enough_transporters(self, count):
        return self.transporter_count >= count

    def transport_capacity(self, transporter_count):
        return TRANSPORTER_CAPACITY * transporter_count

    def can_carry_resources(self, transporter_count, metal, crystal):
        return (metal + crystal) <= self.transport_capacity(transporter_count)

    def __str__(self):
        return self.name


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
