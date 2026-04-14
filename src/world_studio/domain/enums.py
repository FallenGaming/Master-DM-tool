from __future__ import annotations

from enum import Enum


class SettlementType(str, Enum):
    HAMLET = "hamlet"
    VILLAGE = "village"
    TOWN = "town"
    CITY = "city"
    METROPOLIS = "metropolis"


class NodeType(str, Enum):
    SETTLEMENT = "settlement"
    POINT_OF_INTEREST = "point_of_interest"
    NATURAL_FEATURE = "natural_feature"
    ROUTE_JUNCTION = "route_junction"


class EventScope(str, Enum):
    WORLD = "world"
    CONTINENT = "continent"
    EMPIRE = "empire"
    KINGDOM = "kingdom"
    REGION = "region"
    SETTLEMENT = "settlement"
    NPC = "npc"


class RelationshipType(str, Enum):
    FAMILY = "family"
    FRIEND = "friend"
    RIVAL = "rival"
    ROMANCE = "romance"
    ALLY = "ally"
    ENEMY = "enemy"


class SimulationStep(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    SEASON = "season"
    YEAR = "year"
    CUSTOM_DAYS = "custom_days"
