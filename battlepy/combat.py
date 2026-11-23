"""Combat rules and wave planning for BATTLE-PY.

This module deliberately has no Panda3D imports. Wave balancing, guided-missile
steering decisions and countermeasures can be tested before opening a GPU window.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class HostileType:
    callsign: str
    hitpoints: float
    cruise_speed: float
    fire_min: float
    fire_max: float
    missile: bool
    ideal_distance: float
    score: int
    radius_sq: float
    scale: float = 1.0


HOSTILES: dict[str, HostileType] = {
    'scout': HostileType('TALON', 44, 94, 2.2, 3.7, False, 125, 140, 22, .94),
    'interceptor': HostileType('RAPTOR', 76, 124, 1.3, 2.4, False, 190, 215, 35, 1.1),
    'striker': HostileType('REAPER', 132, 76, 3.0, 4.6, True, 375, 325, 72, 1.5),
    'ace': HostileType('SPECTRE', 245, 164, 1.2, 2.0, True, 245, 850, 48, 1.37),
    'sam': HostileType('VIGIL-SAM', 160, 0, 3.7, 5.3, True, 580, 360, 80, 1.0),
}


def wave_manifest(number: int) -> list[str]:
    """Gradually introduces fighters, missile carriers, and elite encounters.

    Waves 4, 8, 12, ... contain a boss. A maximum of ten airborne hostiles is
    maintained for reasonable CPU load on lower-end gaming laptops.
    """
    if number < 1:
        raise ValueError('Wave numbers start at one')
    if number == 1:
        return ['scout', 'scout', 'interceptor']
    if number == 2:
        return ['scout', 'scout', 'interceptor', 'interceptor', 'striker']
    n = min(5 + number // 2, 9)
    wave = ['scout', 'interceptor', 'interceptor', 'striker']
    while len(wave) < n:
        wave.append('interceptor' if len(wave) % 2 else 'scout')
    if number % 4 == 0:
        wave[-1] = 'ace'
    elif number >= 5:
        wave[-1] = 'striker'
    return wave


def sam_count(wave: int) -> int:
    """Stationary anti-aircraft positions only appear after first dogfights."""
    return 0 if wave < 3 else min(1 + (wave - 3) // 3, 2)


def aim_lead(relative_pos, target_velocity, projectile_speed: float):
    """Return seconds to first possible intercept (None for no intercept).

    Inputs are float triples, so game AI and the HUD can use the same tested
    ballistic equation without relying on any particular 3D vector library.
    """
    if projectile_speed <= 0:
        return None
    px, py, pz = relative_pos
    vx, vy, vz = target_velocity
    a = vx*vx + vy*vy + vz*vz - projectile_speed*projectile_speed
    b = 2*(px*vx + py*vy + pz*vz)
    c = px*px + py*py + pz*pz
    if c < 1e-7:
        return 0.0
    if abs(a) < 1e-8:
        return (-c / b) if b < -1e-8 else None
    disc = b*b - 4*a*c
    if disc < 0:
        return None
    root = math.sqrt(disc)
    candidates = [t for t in ((-b-root)/(2*a), (-b+root)/(2*a)) if t > 0]
    return min(candidates) if candidates else None


def missile_turn_rate(kind: str, age: float) -> float:
    """Guided munitions accelerate into their turn after their motor lights."""
    if kind == 'enemy_missile':
        return min(2.25, .75 + age*.75)
    if kind == 'missile':
        return min(3.15, 1.9 + age*.85)
    return 0.0


def threat_level(distance: float, incoming_missiles: int) -> str:
    if incoming_missiles:
        return 'MISSILE INBOUND'
    if distance < 135:
        return 'BREAK CONTACT'
    if distance < 310:
        return 'HOSTILES CLOSE'
    return 'SEARCHING'
