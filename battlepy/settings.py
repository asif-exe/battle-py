"""Tuneable gameplay and presentation settings for battle-py."""
from __future__ import annotations

from dataclasses import dataclass

TITLE = 'BATTLE-PY'
VERSION = '1.3.0'

# All world units are metres, with +Y forward and +Z upward.
SEA_LEVEL = 0.0
CHUNK_SIZE = 280.0
GRID_CELLS = 25
LOAD_RADIUS = 3
START_POS = (-620.0, 280.0, 155.0)

JET_CRUISE_SPEED = 150.0
JET_MIN_SPEED = 63.0
JET_MAX_SPEED = 215.0
JET_BOOST_SPEED = 305.0
JET_MAX_HULL = 100.0
MISSILE_CAPACITY = 4
MISSILE_RECHARGE_SECONDS = 9.0
GUN_INTERVAL = 0.115
GUN_OVERHEAT_COOL_RATE = 0.27

COLOR_SKY = (0.15, 0.25, 0.33, 1)
COLOR_CYAN = (0.30, 0.89, 0.91, 1)
COLOR_GOLD = (1.0, 0.72, 0.40, 1)
COLOR_RED = (1.0, 0.33, 0.27, 1)
COLOR_ICE = (0.84, 0.93, 0.91, 1)


@dataclass
class RuntimeSettings:
    sound: bool = True
    music: bool = True
    camera_mode: int = 0
    mouse_sensitivity: float = 1.0
