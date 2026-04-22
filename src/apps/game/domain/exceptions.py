class DomainError(Exception):
    pass


class BuildingError(DomainError):
    pass


class BuildingAlreadyInProgressError(BuildingError):
    pass


class UnknownBuildingError(BuildingError):
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
