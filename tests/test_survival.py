"""Regression coverage for impact, pilot survival, and crash transition rules."""
import ast
import unittest
from pathlib import Path

from battlepy.survival import (evaluate_impact, collision_damage, damage_state,
                               smoke_rate, warning_altitude)

ROOT=Path(__file__).resolve().parents[1]


class ImpactTests(unittest.TestCase):
    def test_high_speed_land_hit_is_fatal(self):
        impact=evaluate_impact(airspeed=180,descent_rate=10,penetration=1,water=False)
        self.assertTrue(impact.catastrophic)
        self.assertEqual(impact.label,'TERRAIN COLLISION')

    def test_low_speed_shallow_scrape_can_be_recovered(self):
        impact=evaluate_impact(airspeed=50,descent_rate=0,penetration=1,water=False)
        self.assertFalse(impact.catastrophic)
        self.assertGreater(impact.damage,0)
        self.assertEqual(impact.label,'TERRAIN SCRAPE')

    def test_water_collision_crashes_even_at_90(self):
        impact=evaluate_impact(airspeed=90,descent_rate=5,penetration=1,water=True)
        self.assertTrue(impact.catastrophic)
        self.assertEqual(impact.label,'OCEAN IMPACT')

    def test_deep_hard_landing_always_crashes(self):
        self.assertTrue(evaluate_impact(airspeed=40,descent_rate=30,
                                        penetration=2,water=False).catastrophic)
        self.assertTrue(evaluate_impact(airspeed=40,descent_rate=0,
                                        penetration=12,water=False).catastrophic)

    def test_collision_damage_increases_with_relative_speed(self):
        self.assertLess(collision_damage(10),collision_damage(100))
        self.assertEqual(collision_damage(9999),100)

    def test_damage_visual_state(self):
        self.assertEqual(damage_state(100),'nominal')
        self.assertEqual(damage_state(60),'light')
        self.assertEqual(damage_state(50),'heavy')
        self.assertEqual(damage_state(22),'critical')
        self.assertEqual(damage_state(0),'destroyed')
        self.assertEqual(smoke_rate(90),0)
        self.assertGreater(smoke_rate(15),smoke_rate(50))

    def test_low_altitude_warning_without_auto_damage(self):
        self.assertTrue(warning_altitude(8,150))
        self.assertFalse(warning_altitude(200,150))

    def test_control_paths_and_crash_states_exist(self):
        tree=ast.parse((ROOT/'battlepy/game.py').read_text())
        klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BattlePy')
        methods={n.name for n in klass.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        needed={'deploy','_safe_tick','_start_crash','_finish_crash',
                '_update_crash','_update_wreckage','eject','go_to_menu'}
        self.assertFalse(needed-methods)


if __name__=='__main__':unittest.main()
