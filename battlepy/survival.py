"""Testable crash, impact, and damage mechanics (no Panda3D dependency).

Keeping the impact decisions here makes them easier to tune and regression test
without requiring a GPU or opening a game window.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from .mathx import clamp


@dataclass(frozen=True)
class Impact:
    catastrophic: bool
    damage: float
    water: bool
    severity: float
    label: str


def evaluate_impact(*, airspeed: float, descent_rate: float,
                    penetration: float, water: bool) -> Impact:
    """Classify an actual contact with the terrain / water surface.

    descent_rate is a *positive downward* velocity, while penetration is the
    depth in metres below the jet's collision clearance envelope.
    """
    speed = max(0.0, airspeed)
    descent = max(0.0, descent_rate)
    depth = max(0.0, penetration)
    energy = speed * 0.52 + descent * 1.38 + depth * 1.15
    catastrophic = speed >= (83.0 if water else 92.0) or descent >= 25.0 or depth >= 10
    damage = clamp(energy * (0.55 if water else 0.72), 10.0, 100.0)
    label = ('OCEAN IMPACT' if water else 'TERRAIN COLLISION') if catastrophic else \
        ('WATER STRIKE' if water else 'TERRAIN SCRAPE')
    return Impact(catastrophic, damage, water, clamp(energy / 165, 0, 1), label)


def damage_state(hull: float) -> str:
    if hull <= 0: return 'destroyed'
    if hull <= 25: return 'critical'
    if hull <= 55: return 'heavy'
    if hull <= 80: return 'light'
    return 'nominal'


def smoke_rate(hull: float) -> float:
    """Particles per second: light damage 0, heavy 12, critical 28."""
    return 0.0 if hull > 64 else 9.0 + (64.0 - clamp(hull, 0, 64)) * 0.32


def collision_damage(relative_speed: float) -> float:
    return clamp(34 + max(0., relative_speed) * .52, 34, 100)


def warning_altitude(clearance: float, speed: float) -> bool:
    return clearance < 30 + max(0, speed - 120) * .10
