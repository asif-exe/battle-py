"""Tests that run without a display or Panda3D installed."""
from __future__ import annotations

import sys
import unittest
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from battlepy.mathx import clamp, fbm, noise, terrain_height


class ProceduralTests(unittest.TestCase):
    def test_height_is_repeatable(self):
        locations=[(-200.,20.),(0.,0.),(-620.,280.),(4112.27,-918.76)]
        for x,y in locations:
            self.assertAlmostEqual(terrain_height(x,y),terrain_height(x,y),places=12)

    def test_height_has_continuous_tile_edges(self):
        for x,y in [(280.,420.),(-280.,-840.),(1120.,0.)]:
            self.assertLess(abs(terrain_height(x-.0001,y)-terrain_height(x+.0001,y)),.02)

    def test_noise_bounds(self):
        for i in range(-100,100,17):
            self.assertTrue(-1.01<=noise(i*.219,i*.311)<=1.01)
            self.assertTrue(-1.01<=fbm(i*.219,i*.311)<=1.01)

    def test_spawn_is_safe(self):
        from battlepy.settings import START_POS
        self.assertGreater(START_POS[2]-max(terrain_height(START_POS[0],START_POS[1]),0),70)

    def test_audio_assets_are_valid_wav(self):
        names=('engine','wind','boost','roll','cannon','missile','explosion',
               'damage','lock','warning','ui','victory')
        for name in names:
            with self.subTest(name=name):
                p=ROOT/'assets'/'audio'/f'{name}.wav'
                self.assertTrue(p.is_file())
                with wave.open(str(p),'rb') as w:
                    self.assertEqual(w.getnchannels(),1)
                    self.assertEqual(w.getframerate(),22050)
                    self.assertGreater(w.getnframes(),2000)

    def test_textures_exist(self):
        for name in ['cloud.png','sun.png','icon.png']:
            self.assertTrue((ROOT/'assets'/'textures'/name).is_file())


if __name__=='__main__': unittest.main()
