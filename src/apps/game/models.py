from django.conf import settings
from django.db import models
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
    is_homeland = models.BooleanField(default=False)
    last_update_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
