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
