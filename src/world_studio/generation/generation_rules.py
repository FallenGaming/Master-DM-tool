from __future__ import annotations

from collections.abc import Sequence
from random import Random

from world_studio.domain.enums import RelationshipType, SettlementType

CONTINENT_NAMES: tuple[str, ...] = (
    "Aurelia",
    "Nordreach",
    "Sunvale",
    "Duskmere",
    "Stormcrest",
    "Ivorywild",
)

EMPIRE_NAMES: tuple[str, ...] = (
    "Auric Imperium",
    "Vermillion Accord",
    "Silver Dominion",
    "Crown of Embers",
    "The Tidebound Throne",
)

KINGDOM_NAMES: tuple[str, ...] = (
    "Ravenhold",
    "Brightmere",
    "Stonewick",
    "Highgrove",
    "Moonreach",
    "Ironvale",
    "Goldmarsh",
)

REGION_NAMES: tuple[str, ...] = (
    "Whispering Vale",
    "Ashen Ridge",
    "Sable Fen",
    "Kingswood",
    "Frostmere",
    "Amber Plains",
    "Gilded Coast",
)

SETTLEMENT_NAMES: tuple[str, ...] = (
    "Ravenford",
    "Oakrest",
    "Brighthollow",
    "Mistwatch",
    "Ashbridge",
    "Goldrun",
    "Stoneharbor",
    "Larkspur",
)

POI_NAMES: tuple[str, ...] = (
    "Echo Obelisk",
    "Shattered Keep",
    "Moonwell Shrine",
    "Black Orchard",
    "Dawnfire Crater",
)

CLIMATES: tuple[str, ...] = ("temperate", "arid", "humid", "cold", "continental")
BIOMES: tuple[str, ...] = ("plains", "forest", "hills", "coast", "marsh", "tundra")
GOVERNING_STYLES: tuple[str, ...] = (
    "feudal monarchy",
    "merchant council",
    "theocratic rule",
    "ducal assembly",
)

RACE_TEMPLATES: tuple[tuple[str, int, bool], ...] = (
    ("Human", 80, True),
    ("Elf", 320, True),
    ("Dwarf", 250, True),
    ("Halfling", 140, True),
    ("Tiefling", 120, True),
)

OCCUPATION_TEMPLATES: tuple[tuple[str, str, float], ...] = (
    ("Farmer", "labor", 1.7),
    ("Guard", "security", 0.7),
    ("Blacksmith", "craft", 0.4),
    ("Carpenter", "craft", 0.5),
    ("Merchant", "trade", 0.6),
    ("Priest", "faith", 0.25),
    ("Innkeeper", "hospitality", 0.2),
    ("Scholar", "knowledge", 0.12),
    ("Hunter", "labor", 0.45),
)

FIRST_NAMES: tuple[str, ...] = (
    "Aelar",
    "Brynn",
    "Cedric",
    "Daria",
    "Elowen",
    "Fenric",
    "Galen",
    "Helena",
    "Ivar",
    "Junia",
    "Kael",
    "Liora",
    "Mira",
    "Noren",
    "Orin",
    "Petra",
    "Quinn",
    "Rowan",
    "Selene",
    "Tamsin",
)

SURNAME_ROOTS: tuple[str, ...] = (
    "Ash",
    "Stone",
    "Raven",
    "Gold",
    "Winter",
    "Moon",
    "Thorn",
    "River",
    "Dawn",
    "Cinder",
)

GOAL_FRAGMENTS: tuple[str, ...] = (
    "secure influence in local politics",
    "grow household prosperity",
    "protect loved ones from regional unrest",
    "discover forgotten lore",
    "gain recognition among guild peers",
)

FLAW_FRAGMENTS: tuple[str, ...] = (
    "quick to hold grudges",
    "overconfident in negotiations",
    "secretive about personal history",
    "risk-prone under pressure",
    "easily manipulated by status",
)

RELATION_WEIGHTS: tuple[tuple[RelationshipType, float], ...] = (
    (RelationshipType.FAMILY, 0.22),
    (RelationshipType.FRIEND, 0.43),
    (RelationshipType.ALLY, 0.19),
    (RelationshipType.RIVAL, 0.11),
    (RelationshipType.ENEMY, 0.05),
)

SETTLEMENT_SIZE_WEIGHTS: tuple[tuple[SettlementType, float], ...] = (
    (SettlementType.HAMLET, 0.18),
    (SettlementType.VILLAGE, 0.42),
    (SettlementType.TOWN, 0.29),
    (SettlementType.CITY, 0.09),
    (SettlementType.METROPOLIS, 0.02),
)


def weighted_choice[T](rng: Random, weighted_values: Sequence[tuple[T, float]]) -> T:
    total = sum(weight for _, weight in weighted_values)
    threshold = rng.uniform(0, total)
    acc = 0.0
    for value, weight in weighted_values:
        acc += weight
        if threshold <= acc:
            return value
    return weighted_values[-1][0]


def unique_name(
    rng: Random,
    used_names: set[str],
    label: str,
    index: int,
    pool: Sequence[str],
) -> str:
    for _ in range(20):
        candidate = rng.choice(tuple(pool))
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
    fallback = f"{label} {index + 1}"
    used_names.add(fallback)
    return fallback


def choose_population(rng: Random, settlement_kind: SettlementType) -> int:
    if settlement_kind == SettlementType.HAMLET:
        return rng.randint(80, 240)
    if settlement_kind == SettlementType.VILLAGE:
        return rng.randint(180, 900)
    if settlement_kind == SettlementType.TOWN:
        return rng.randint(800, 4500)
    if settlement_kind == SettlementType.CITY:
        return rng.randint(4000, 22000)
    return rng.randint(22000, 80000)


def pick_relation_type(rng: Random) -> RelationshipType:
    return weighted_choice(rng, RELATION_WEIGHTS)


def choose_climate(rng: Random) -> str:
    return rng.choice(CLIMATES)


def choose_biome(rng: Random) -> str:
    return rng.choice(BIOMES)


def choose_governing_style(rng: Random) -> str:
    return rng.choice(GOVERNING_STYLES)


def pick_settlement_type(rng: Random) -> SettlementType:
    return weighted_choice(rng, SETTLEMENT_SIZE_WEIGHTS)
