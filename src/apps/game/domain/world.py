from dataclasses import dataclass

from apps.game.domain.exceptions import InvalidCoordinatesError


@dataclass(frozen=True, slots=True)
class Coordinates:
    galaxy: int
    system: int
    position: int

    @classmethod
    def parse(cls, value: str) -> "Coordinates":
        parts = value.strip().split(":")

        if len(parts) != 3:
            raise InvalidCoordinatesError(
                "Koordynaty muszą mieć format galaktyka:system:pozycja."
            )

        try:
            galaxy, system, position = (int(part) for part in parts)
        except ValueError as exc:
            raise InvalidCoordinatesError(
                "Koordynaty mogą zawierać tylko liczby."
            ) from exc

        return cls(galaxy=galaxy, system=system, position=position)

    def as_tuple(self) -> tuple[int, int, int]:
        return self.galaxy, self.system, self.position

    def __str__(self) -> str:
        return f"{self.galaxy}:{self.system}:{self.position}"


@dataclass(frozen=True, slots=True)
class UniverseRules:
    galaxy_count: int = 9
    systems_per_galaxy: int = 499
    positions_per_system: int = 15
    max_planets_per_player: int = 9

    def contains(self, coordinates: Coordinates) -> bool:
        return (
            1 <= coordinates.galaxy <= self.galaxy_count
            and 1 <= coordinates.system <= self.systems_per_galaxy
            and 1 <= coordinates.position <= self.positions_per_system
        )

    def validate_coordinates(self, coordinates: Coordinates) -> None:
        if not self.contains(coordinates):
            raise InvalidCoordinatesError(
                "Koordynaty znajdują się poza granicami uniwersum."
            )


DEFAULT_UNIVERSE_RULES = UniverseRules()
