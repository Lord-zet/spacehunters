from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from .buildings import BUILDINGS
from .ships import SHIPS


PLANET_NAME_MAX_LENGTH = 50


class Planet(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="planets"
    )
    name = models.CharField(max_length=PLANET_NAME_MAX_LENGTH)
    galaxy = models.PositiveIntegerField(default=1)
    system = models.PositiveIntegerField()
    position = models.PositiveIntegerField()

    planet_type = models.CharField(max_length=50, default="terrestrial")
    radius_km = models.PositiveIntegerField(default=6_000)
    temperature_min = models.SmallIntegerField(default=-20)
    temperature_max = models.SmallIntegerField(default=40)

    metal = models.BigIntegerField(default=500)
    crystal = models.BigIntegerField(default=200)
    helion = models.BigIntegerField(default=0)
    metal_production_remainder_micro = models.PositiveIntegerField(default=0)
    crystal_production_remainder_micro = models.PositiveIntegerField(default=0)
    helion_production_remainder_micro = models.PositiveIntegerField(default=0)

    is_homeland = models.BooleanField(default=False)
    last_resource_update = models.DateTimeField(auto_now_add=True)
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
        return self.buildings

    def is_building_in_progress(self, *, at=None):
        return self.get_buildings().is_building_in_progress(at=at)

    @property
    def coordinates(self):
        return f"{self.galaxy}:{self.system}:{self.position}"

    @property
    def transporter_count(self):
        ship = self.ships.filter(ship_code="transporter").first()
        return ship.quantity if ship else 0

    def get_ship_quantity(self, ship_code: str) -> int:
        ship = self.ships.filter(ship_code=ship_code).first()
        return ship.quantity if ship else 0

    def get_ship_construction(self):
        return self.ship_construction

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
    helion_synthesizer_level = models.PositiveIntegerField(default=0)
    solar_array_level = models.PositiveIntegerField(default=1)
    metal_storage_level = models.PositiveIntegerField(default=1)
    crystal_storage_level = models.PositiveIntegerField(default=1)
    helion_storage_level = models.PositiveIntegerField(default=0)
    shipyard_level = models.PositiveIntegerField(default=0)
    building_type = models.CharField(max_length=50, blank=True, default="")
    building_ends_at = models.DateTimeField(null=True, blank=True)
    building_cost_paid = models.JSONField(default=dict, blank=True)

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

    def clear_building_progress(self) -> None:
        self.building_type = ""
        self.building_ends_at = None
        self.building_cost_paid = {}

    def __str__(self):
        return f"Buildings<{self.planet_id}>"


class PlanetShip(models.Model):
    planet = models.ForeignKey(
        Planet,
        on_delete=models.CASCADE,
        related_name="ships",
    )
    ship_code = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["planet", "ship_code"],
                name="unique_ship_type_per_planet",
            ),
        ]
        ordering = ["planet_id", "ship_code"]

    def __str__(self):
        return f"{self.planet_id}:{self.ship_code}={self.quantity}"


class PlanetShipConstruction(models.Model):
    planet = models.OneToOneField(
        Planet,
        on_delete=models.CASCADE,
        related_name="ship_construction",
    )
    ship_code = models.CharField(max_length=50, blank=True, default="")
    quantity = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    def is_in_progress(self, *, at=None):
        now = at or timezone.now()
        return bool(self.ship_code) and self.ends_at is not None and self.ends_at > now

    def clear(self):
        self.ship_code = ""
        self.quantity = 0
        self.started_at = None
        self.ends_at = None

    def __str__(self):
        return f"ShipConstruction<{self.planet_id}>"


class Fleet(models.Model):
    class Status(models.TextChoices):
        OUTBOUND = "outbound", "Outbound"
        RETURNING = "returning", "Returning"
        COMPLETED = "completed", "Completed"

    class MissionType(models.TextChoices):
        TRANSPORT = "transport", "Transport"
        STATION = "station", "Station"

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
    metal = models.BigIntegerField(default=0)
    crystal = models.BigIntegerField(default=0)
    helion = models.BigIntegerField(default=0)
    helion_cost = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OUTBOUND)
    speed_profile = models.CharField(
        max_length=30,
        default="standard",
    )
    mission_type = models.CharField(
        max_length=30,
        choices=MissionType.choices,
        default=MissionType.TRANSPORT,
    )
    departure_time = models.DateTimeField(auto_now_add=True)
    arrival_time = models.DateTimeField()
    return_time = models.DateTimeField(null=True, blank=True)

    @property
    def next_event_at(self):
        if self.status == self.Status.OUTBOUND:
            return self.arrival_time
        if self.status == self.Status.RETURNING:
            return self.return_time
        return None

    @property
    def ships_display(self) -> list[dict]:
        """
        Zwraca listę słowników ze szczegółami statków we flocie, łącząc dane
        z bazy (quantity) z bazą konfiguracyjną SHIPS.
        """
        result = []
        # self.ships.all() zamiast filter(), aby wykorzystać cache'owany prefetch_related
        for fleet_ship in self.ships.all():
            if fleet_ship.quantity <= 0:
                continue

            config = SHIPS.get(fleet_ship.ship_code, {})
            result.append({
                "code": fleet_ship.ship_code,
                "label": config.get("label", fleet_ship.ship_code),
                "quantity": fleet_ship.quantity,
                "thumb": config.get("thumb"),
            })
        return result

    @property
    def total_ships_count(self) -> int:
        return sum(ship.quantity for ship in self.ships.all())

    def __str__(self):
        return f"{self.source_planet} -> {self.target_planet}"


class FleetShip(models.Model):
    fleet = models.ForeignKey(
        Fleet,
        on_delete=models.CASCADE,
        related_name="ships",
    )
    ship_code = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fleet", "ship_code"],
                name="unique_ship_type_per_fleet",
            ),
        ]
        ordering = ["fleet_id", "ship_code"]

    def __str__(self):
        return f"{self.fleet_id}:{self.ship_code}={self.quantity}"
