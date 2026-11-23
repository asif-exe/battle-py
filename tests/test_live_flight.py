"""Exercise the real flight-update method without requiring a GPU or Panda3D.

The v1.2 build accidentally referred to 'key_y' instead of 'key_yaw'. Syntax-only
checks missed that error; executing the method against small fake engine objects
catches the actual first-flight-frame NameError and protects future control edits.
"""
from __future__ import annotations

import ast
import math
import unittest
from pathlib import Path

from battlepy.mathx import clamp, damp, lerp
from battlepy.settings import (
    JET_BOOST_SPEED, JET_CRUISE_SPEED, JET_MAX_SPEED, JET_MIN_SPEED,
    MISSILE_CAPACITY, MISSILE_RECHARGE_SECONDS,
)
from battlepy.survival import evaluate_impact

SOURCE = Path(__file__).resolve().parents[1] / 'battlepy' / 'game.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))
GAME = next(node for node in TREE.body if isinstance(node, ast.ClassDef) and node.name == 'BattlePy')
METHOD = next(node for node in GAME.body if isinstance(node, ast.FunctionDef) and node.name == '_update_flight')


class V:
    """Minimal simulation of the Panda3D Vec3 operations used during flight."""
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def __add__(self, other):
        return V(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, n):
        return V(self.x * n, self.y * n, self.z * n)

    __rmul__ = __mul__

    def __repr__(self):
        return f'V({self.x}, {self.y}, {self.z})'


class DummyQuat:
    def getForward(self):
        return V(0, 1, 0)


class DummyJet:
    def __init__(self, altitude=155):
        self.pos = V(-620, 280, altitude)
        self.hpr = (0, 0, 0)

    def getQuat(self, render):
        return DummyQuat()

    def getPos(self):
        return self.pos

    def setPos(self, *pos):
        self.pos = pos[0] if len(pos) == 1 else V(*pos)

    def setHpr(self, *hpr):
        self.hpr = hpr


class DummyMouse:
    def __init__(self, x, y):
        self.x, self.y = x, y


class DummyWatcher:
    def __init__(self):
        self.x, self.y, self.present = 0, 0, False

    def hasMouse(self):
        return self.present

    def getMouse(self):
        return DummyMouse(self.x, self.y)


class DummyWorld:
    def __init__(self, elevation=0):
        self.elevation = elevation

    def height(self, x, y):
        return self.elevation


class DummyAudio:
    def __init__(self):
        self.calls = []

    def update(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class DummyGame:
    def __init__(self, altitude=155):
        self.keys = {k: False for k in (
            'w', 's', 'a', 'd', 'up', 'down', 'left', 'right',
            'shift', 'lshift', 'rshift', 'mouse1',
        )}
        self.throttle = .60
        self.boosting = False
        self.boost_energy = 1.
        self.speed = JET_CRUISE_SPEED
        self.gun_heat = 0.
        self.gun_clock = 0.
        self.damage_cooldown = 0.
        self.reload_clock = 0.
        self.ammo = MISSILE_CAPACITY
        self.mouseWatcherNode = DummyWatcher()
        self.yaw_rate = 0.
        self.pitch_rate = 0.
        self.heading = 0.
        self.pitch = 0.
        self.roll = 0.
        self.barrel_timer = 0.
        self.render = object()
        self.jet = DummyJet(altitude)
        self.world = DummyWorld()
        self.audio = DummyAudio()
        self.hull = 100.
        self.state = 'playing'
        self.crash_event = None

    def _start_crash(self, label, position, water=False):
        self.state = 'crashing'
        self.crash_event = (label, water)

    def _take_damage(self, amount, cause):
        self.hull -= amount


def real_flight_update():
    namespace = {
        'Vec3': V,
        'clamp': clamp, 'damp': damp, 'lerp': lerp,
        'evaluate_impact': evaluate_impact,
        'JET_BOOST_SPEED': JET_BOOST_SPEED,
        'JET_CRUISE_SPEED': JET_CRUISE_SPEED,
        'JET_MAX_SPEED': JET_MAX_SPEED,
        'JET_MIN_SPEED': JET_MIN_SPEED,
        'MISSILE_CAPACITY': MISSILE_CAPACITY,
        'MISSILE_RECHARGE_SECONDS': MISSILE_RECHARGE_SECONDS,
    }
    source = ast.fix_missing_locations(ast.Module(body=[METHOD], type_ignores=[]))
    exec(compile(source, str(SOURCE), 'exec'), namespace)
    return namespace['_update_flight']


UPDATE = real_flight_update()


class LiveFlightTests(unittest.TestCase):
    def test_enter_first_frame_runs_without_nameerror(self):
        game = DummyGame()
        old_y = game.jet.getPos().y
        UPDATE(game, 1/60)
        self.assertEqual(game.state, 'playing')
        self.assertGreater(game.jet.getPos().y, old_y)
        self.assertEqual(len(game.audio.calls), 1)

    def test_d_key_turns_right(self):
        game = DummyGame()
        game.keys['d'] = True
        UPDATE(game, .05)
        self.assertGreater(game.yaw_rate, 0)
        self.assertGreater(game.heading, 0)

    def test_a_key_turns_left(self):
        game = DummyGame()
        game.keys['a'] = True
        UPDATE(game, .05)
        self.assertLess(game.yaw_rate, 0)
        self.assertGreater(game.heading, 350)  # wraps into [0, 360)

    def test_mouse_x_steers_without_keys(self):
        game = DummyGame()
        game.mouseWatcherNode.present = True
        game.mouseWatcherNode.x = .75
        UPDATE(game, .05)
        self.assertGreater(game.yaw_rate, 0)

    def test_arrow_up_commands_climb(self):
        game = DummyGame()
        game.keys['up'] = True
        UPDATE(game, .05)
        self.assertGreater(game.pitch_rate, 0)

    def test_shift_drives_afterburner_and_exhaust_sound(self):
        game = DummyGame()
        game.keys['shift'] = True
        initial = game.boost_energy
        UPDATE(game, .05)
        self.assertTrue(game.boosting)
        self.assertLess(game.boost_energy, initial)
        self.assertTrue(game.audio.calls[-1][0][1])

    def test_fast_water_strike_enters_crash_mode(self):
        game = DummyGame(altitude=3.0)
        UPDATE(game, .05)
        self.assertEqual(game.state, 'crashing')
        self.assertEqual(game.crash_event, ('OCEAN IMPACT', True))
        self.assertFalse(game.audio.calls)


if __name__ == '__main__':
    unittest.main()
