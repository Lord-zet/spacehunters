class DomainError(Exception):
    pass


class BuildingError(DomainError):
    pass


class BuildingAlreadyInProgressError(BuildingError):
    pass


class UnknownBuildingError(BuildingError):
    pass


class NoFreePlanetFieldsError(DomainError):
    pass


class NotEnoughResourcesError(BuildingError):
    pass


class FleetError(DomainError):
    pass


class SamePlanetTransportError(FleetError):
    pass


class NotEnoughTransportersError(FleetError):
    pass


class CargoCapacityExceededError(FleetError):
    pass


class NotEnoughFuelError(DomainError):
    pass


class InvalidStationingTargetError(DomainError):
    pass


class UnknownShipError(DomainError):
    pass


class ShipyardRequiredError(DomainError):
    pass


class ShipConstructionAlreadyInProgressError(DomainError):
    pass


class InvalidShipQuantityError(DomainError):
    pass


class PlanetStateTimeRegressionError(DomainError):
    pass


class PlanetOwnershipError(DomainError):
    pass


class InvalidPlanetNameError(DomainError):
    pass


class PlanetNameAlreadyExistsError(DomainError):
    pass


class UnsupportedFleetMissionError(DomainError):
    pass


class NoBuildingInProgressError(DomainError):
    pass


class UnknownPlanetTypeError(ValueError):
    pass


class UnknownFleetSpeedProfileError(ValueError):
    pass


class InvalidResourceAmountError(DomainError):
    def __init__(self, *, resource, amount: int):
        self.resource = resource
        self.amount = amount

        super().__init__(f"Ilość zasobu {resource.value} nie może być ujemna: {amount}.")
