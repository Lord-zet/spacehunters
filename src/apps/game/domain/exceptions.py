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
