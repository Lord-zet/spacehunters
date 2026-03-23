from django.conf import settings
from django.db import models
from django.utils import timezone

from .buildings import BUILDINGS


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
    is_homeland = models.BooleanField(default=False)
    last_resource_update = models.DateTimeField(auto_now_add=True)

    def update_resources(self):
        now = timezone.now()
        elapsed_seconds = (now - self.last_resource_update).total_seconds()

        if elapsed_seconds <= 0:
            return

        production = self.get_production_per_hour()

        for resource, per_hour in production.items():
            gain = int(per_hour * elapsed_seconds / 3600)
            current_amount = getattr(self, resource, 0)
            setattr(self, resource, current_amount + gain)

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

    def upgrade_building(self, building_name):
        config = self.get_building_config(building_name)
        if not config:
            return False, "Nieznany budynek."

        cost = self.calculate_upgrade_cost(config)

        if not self.has_enough_resources(cost):
            return False, "Za mało surowców."

        self.spend_resources(cost)
        current_level = self.get_building_level(config)
        setattr(self, config["level_field"], current_level + 1)
        self.save()

        return True, f"Rozpoczęto rozbudowę {building_name}."

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

    def __str__(self):
        return self.name
