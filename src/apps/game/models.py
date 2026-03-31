from datetime import timedelta

from django.conf import settings
from django.db import models
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

    def get_building_config(self, building_name):
        return BUILDINGS.get(building_name)

    def get_building_level(self, config):
        return getattr(self, config["level_field"])

    def calculate_upgrade_cost(self, config):
        level = self.get_building_level(config)
        return {
            resource: base * level
            for resource, base in config["base_cost"].items()
        }

    def get_upgrade_cost(self, building_name):
        config = self.get_building_config(building_name)
        if not config:
            return None
        return self.calculate_upgrade_cost(config)

    def has_enough_resources(self, cost):
        for resource, amount in cost.items():
            if getattr(self, resource) < amount:
                return False
        return True

    def spend_resources(self, cost):
        for resource, amount in cost.items():
            total = getattr(self, resource) - amount
            setattr(self, resource, total)

    def is_building_in_progress(self):
        return self.building_ends_at is not None and self.building_ends_at > timezone.now()

    def start_upgrade(self, building_name):
        if self.is_building_in_progress():
            return False, "Na tej planecie trwa już budowa."

        config = self.get_building_config(building_name)
        if not config:
            return False, "Nieznany budynek."

        cost = self.calculate_upgrade_cost(config)

        if not self.has_enough_resources(cost):
            return False, "Za mało surowców."

        self.spend_resources(cost)

        self.building_type = building_name
        self.building_ends_at = timezone.now() + timedelta(seconds=config["build_time"])
        self.save()
        return True, f"Rozpoczęto rozbudowę {building_name}."

    def finish_building_if_ready(self):
        if not self.building_ends_at:
            return False

        if self.building_ends_at > timezone.now():
            return False

        config = self.get_building_config(self.building_type)
        if not config:
            self.building_type = ""
            self.building_ends_at = None
            self.save()
            return False

        level_field = config["level_field"]
        current_level = getattr(self, level_field)
        setattr(self, level_field, current_level + 1)

        self.building_type = ""
        self.save()
        return True

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
