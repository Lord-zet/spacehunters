from apps.game.domain.world import DEFAULT_UNIVERSE_RULES, UniverseRules


def get_universe_coordinate_hint(rules: UniverseRules = DEFAULT_UNIVERSE_RULES) -> str:
    return (
        f"Zakres: galaktyka 1-{rules.galaxy_count}, "
        f"system 1-{rules.systems_per_galaxy}, "
        f"pozycja 1-{rules.positions_per_system}."
    )
