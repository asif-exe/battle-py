"""Small, deterministic helpers used by flight physics and landscape."""
from __future__ import annotations

import math


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b-a)*t


def smoothstep(x: float) -> float:
    t = clamp(x, 0., 1.)
    return t*t*(3.-2.*t)


def damp(current: float, target: float, rate: float, dt: float) -> float:
    return lerp(current, target, 1.-math.exp(-rate*dt))


def hash2(x: int, y: int, seed: int = 71) -> float:
    h = (x*374761393 + y*668265263 + seed*1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13))*1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFFFF) / 0xFFFFFFFF


def noise(x: float, y: float, seed: int = 71) -> float:
    ix = math.floor(x)
    iy = math.floor(y)
    fx = smoothstep(x-ix)
    fy = smoothstep(y-iy)
    a = lerp(hash2(ix, iy, seed), hash2(ix+1, iy, seed), fx)
    b = lerp(hash2(ix, iy+1, seed), hash2(ix+1, iy+1, seed), fx)
    return lerp(a, b, fy)*2.-1.


def fbm(x: float, y: float, seed: int = 71, octaves: int = 4) -> float:
    result = 0.
    amp = 0.5
    freq = 1.
    for _ in range(octaves):
        result += amp*noise(x*freq, y*freq, seed)
        freq *= 2.08
        amp *= 0.50
    return result


def terrain_height(x: float, y: float) -> float:
    """Continuous archipelago with shallow coast, coves and steep ridges.

    This function must be pure: streaming tiles, collisions and sea level all
    query the exact same surface, including at negative world coordinates.
    """
    # Broad island field: coherent at chunk boundaries and visually recognizable.
    warp = fbm(x*.00068+5.1, y*.00068-2.3, 19, 3)*155.
    w = x+warp
    q = y-warp*.55
    land = (0.59*math.sin(w*.00245+1.12)
            + 0.42*math.cos(q*.00213+.44)
            + 0.29*math.sin((w-q)*.00164+2.7)
            + 0.25*noise(w*.0015, q*.0015, 7))
    coastal = (land-0.31)*195.
    rough = fbm(x*.0078, y*.0078, 109)*19.
    ridge = abs(fbm(x*.00345, y*.00345, 231, 4))
    mountains = (max(0., land-.15)**1.5)*155.*ridge
    return coastal+mountains+rough


def dist_sq(a, b) -> float:
    return sum((x-y)**2 for x,y in zip(a,b))
