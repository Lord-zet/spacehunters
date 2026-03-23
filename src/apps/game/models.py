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

    def __str__(self):
        return self.name
