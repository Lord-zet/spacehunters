from dataclasses import dataclass

from apps.game.buildings import BUILDINGS


@dataclass(frozen=True, slots=True)
class PlanetEnergyBalance:
    produced: int
    consumed: int

    @property
    def available(self) -> int:
        return self.produced - self.consumed

    @property
    def shortage(self) -> int:
        return max(self.consumed - self.produced, 0)

    @property
    def efficiency_percent(self) -> int:
        if self.consumed <= 0:
            return 100

        if self.produced >= self.consumed:
            return 100

        return int(self.produced * 100 / self.consumed)

    @property
    def is_shortage(self) -> bool:
        return self.consumed > self.produced


def get_energy_production(planet, *, buildings=None) -> int:
    if buildings is None:
        buildings = planet.get_buildings()

    total = 0

    for config in BUILDINGS.values():
        energy_production_fn = config.get("energy_production_fn")

        if not energy_production_fn:
            continue

        level = getattr(buildings, config["level_field"])
        total += energy_production_fn(level)

    return total


def get_energy_consumption(planet, *, buildings=None) -> int:
    if buildings is None:
        buildings = planet.get_buildings()

    total = 0

    for config in BUILDINGS.values():
        energy_consumption_fn = config.get("energy_consumption_fn")

        if not energy_consumption_fn:
            continue

        level = getattr(buildings, config["level_field"])
        total += energy_consumption_fn(level)

    return total


def get_energy_balance(planet, *, buildings=None) -> PlanetEnergyBalance:
    if buildings is None:
        buildings = planet.get_buildings()

    return PlanetEnergyBalance(
        produced=get_energy_production(
            planet,
            buildings=buildings,
        ),
        consumed=get_energy_consumption(
            planet,
            buildings=buildings,
        ),
    )

def apply_energy_efficiency_to_production(
    production: dict[str, int],
    energy_balance: PlanetEnergyBalance,
) -> dict[str, int]:
    if energy_balance.consumed <= 0:
        return production

    if energy_balance.produced >= energy_balance.consumed:
        return production

    return {
        resource: amount * energy_balance.produced // energy_balance.consumed
        for resource, amount in production.items()
    }
