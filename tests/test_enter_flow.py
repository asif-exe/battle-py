"""Dependency-free tests of ENTER deployment and guarded engine callbacks.

These execute the actual method bodies parsed from game.py; only Panda3D
rendering, audio, and the OS window are mocked. It is not a GPU gameplay test.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TREE=ast.parse((ROOT/'battlepy/game.py').read_text(encoding='utf8'))
CLASS=next(n for n in TREE.body if isinstance(n,ast.ClassDef) and n.name=='BattlePy')


def actual_method(name):
    method=next(n for n in CLASS.body if isinstance(n,ast.FunctionDef) and n.name==name)
    mod=ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[]))
    namespace={'CYAN':(0.3,0.9,0.9,1)}
    exec(compile(mod,str(ROOT/'battlepy/game.py'),'exec'),namespace)
    return namespace[name]


class FakeHUD:
    def __init__(self):
        self.overlays=[]
        self.notifications=[]
    def set_overlay(self,key):self.overlays.append(key)
    def notify(self,*args):self.notifications.append(args)


class FakeAudio:
    def __init__(self):self.events=[]
    def play(self,*args):self.events.append(args)


class FakeGame:
    state='menu'
    def __init__(self):
        self.hud=FakeHUD()
        self.audio=FakeAudio()
        self.reset_count=0
        self.errors=[]
    def _reset_flight(self):self.reset_count+=1
    def _report_error(self,exc):self.errors.append(str(exc))


class EnterFlowTests(unittest.TestCase):
    def test_real_deploy_body_switches_from_menu_to_playing(self):
        fake=FakeGame()
        actual_method('deploy')(fake)
        self.assertEqual(fake.state,'playing')
        self.assertEqual(fake.reset_count,1)
        self.assertIn('playing',fake.hud.overlays)
        self.assertTrue(fake.hud.notifications)

    def test_enter_failure_goes_to_error_handler_instead_of_escape(self):
        fake=FakeGame()
        def broken_start():raise RuntimeError('simulated driver error')
        callback=actual_method('_guard_event')(fake,broken_start)
        callback()  # would fail an unguarded Panda3D messenger callback
        self.assertEqual(fake.errors,['simulated driver error'])

    def test_successful_enter_event_reaches_real_deploy(self):
        fake=FakeGame()
        callback=actual_method('_guard_event')(fake,lambda:actual_method('deploy')(fake))
        callback()
        self.assertEqual(fake.errors,[])
        self.assertEqual(fake.state,'playing')

    def test_retry_from_error_state_reinitializes_flight(self):
        fake=FakeGame();fake.state='error'
        actual_method('deploy')(fake)
        self.assertEqual(fake.state,'playing')
        self.assertEqual(fake.reset_count,1)


if __name__=='__main__':unittest.main()
