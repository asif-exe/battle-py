"""GPU-free regression suite for the expanded dogfighting mechanics."""
from __future__ import annotations

import ast
from dataclasses import dataclass
import math
from pathlib import Path
import random
import unittest

from battlepy.combat import (HOSTILES, aim_lead, missile_turn_rate, sam_count,
                             threat_level, wave_manifest)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'battlepy' / 'game.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf8'))
GAME = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == 'BattlePy')


def method(name, namespace=None):
    target=next(n for n in GAME.body if isinstance(n,ast.FunctionDef) and n.name==name)
    code=compile(ast.fix_missing_locations(ast.Module(body=[target],type_ignores=[])),str(SOURCE),'exec')
    scope=dict(namespace or {})
    exec(code,scope)
    return scope[name]


class CombatRulesTests(unittest.TestCase):
    def test_first_wave_is_accessible_and_second_introduces_missiles(self):
        self.assertEqual(wave_manifest(1),['scout','scout','interceptor'])
        self.assertIn('striker',wave_manifest(2))
        self.assertEqual(sam_count(1),0)

    def test_boss_every_fourth_wave_and_upper_bound(self):
        for wave in (4,8,12,16):
            self.assertIn('ace',wave_manifest(wave))
            self.assertLessEqual(len(wave_manifest(wave)),9)
        with self.assertRaises(ValueError):wave_manifest(0)

    def test_every_wave_uses_valid_enemy_types(self):
        for wave in range(1,55):
            for name in wave_manifest(wave):
                self.assertIn(name,HOSTILES)
                self.assertGreater(HOSTILES[name].hitpoints,0)
                self.assertGreater(HOSTILES[name].fire_max,HOSTILES[name].fire_min)
            self.assertLessEqual(sam_count(wave),2)

    def test_lead_solution_stationary_target(self):
        self.assertAlmostEqual(aim_lead((0,500,0),(0,0,0),250),2.0)

    def test_lead_solution_moving_target(self):
        # An aircraft moving away at 50m/s extends 500m intercept to 2.5s.
        self.assertAlmostEqual(aim_lead((0,500,0),(0,50,0),250),2.5)
        self.assertIsNone(aim_lead((0,500,0),(0,400,0),250))
        self.assertIsNone(aim_lead((0,10,0),(0,0,0),0))

    def test_guided_missiles_and_alerts(self):
        self.assertGreater(missile_turn_rate('missile',2),missile_turn_rate('missile',0))
        self.assertGreater(missile_turn_rate('enemy_missile',3),missile_turn_rate('enemy_missile',0))
        self.assertEqual(threat_level(900,1),'MISSILE INBOUND')
        self.assertEqual(threat_level(100,0),'BREAK CONTACT')
        self.assertEqual(threat_level(900,0),'SEARCHING')


class V:
    def __init__(self, x=0., y=0., z=0.):
        if isinstance(x,V):self.x,self.y,self.z=x.x,x.y,x.z
        else:self.x,self.y,self.z=float(x),float(y),float(z)
    def __add__(self,other):return V(self.x+other.x,self.y+other.y,self.z+other.z)
    def __sub__(self,other):return V(self.x-other.x,self.y-other.y,self.z-other.z)
    def lengthSquared(self):return self.x*self.x+self.y*self.y+self.z*self.z
    def length(self):return math.sqrt(self.lengthSquared())
    def normalized(self):
        n=self.length()
        return self*(1/n) if n else V()
    def normalize(self):
        n=self.length()
        if n:self.x/=n;self.y/=n;self.z/=n
    def dot(self,other):return self.x*other.x+self.y*other.y+self.z*other.z
    def __mul__(self,f):return V(self.x*f,self.y*f,self.z*f)
    def __neg__(self):return V(-self.x,-self.y,-self.z)
    __rmul__=__mul__
    def __iter__(self):return iter((self.x,self.y,self.z))
    def __repr__(self):return f'V({self.x},{self.y},{self.z})'


class Q:
    def xform(self,v):return v
    def getForward(self):return V(0,1,0)
    def getRight(self):return V(1,0,0)


class Jet:
    def getQuat(self,_):return Q()
    def getPos(self):return V(10,20,120)
    def getQuat(self,_):return Q()


class Node:
    def __init__(self):self.removed=False;self.pos=None;self.scale=None
    def setLightOff(self):pass
    def setH(self,*args):pass
    def setR(self,*args):pass
    def lookAt(self,*args):pass
    def getQuat(self,*args):return Q()
    def setPos(self,p):self.pos=p
    def setScale(self,p):self.scale=p
    def removeNode(self):self.removed=True


class Proto:
    def copyTo(self,_):return Node()


@dataclass
class FakeFlare:
    node: object
    pos: V
    vel: V
    ttl: float
    start_ttl: float


class Audio:
    def __init__(self):self.events=[]
    def play(self,*args):self.events.append(args)


class HUD:
    def __init__(self):self.notices=[]
    def notify(self,*args):self.notices.append(args)


class FakeGame:
    def __init__(self):
        self.state='playing'
        self.flare_ammo=3
        self.flare_cooldown=0.
        self.flare_reload=0.
        self.flares=[]
        self.jet=Jet()
        self.render=object()
        self.flare_prototype=Proto()
        self.random=random.Random(123)
        self.audio=Audio()
        self.hud=HUD()
        self.camera_shake=0.
        self.smoke_count=0
        self.exit_calls=0
    def _smoke(self,*args,**kwargs):self.smoke_count+=1
    def userExit(self):self.exit_calls+=1


class GameActionTests(unittest.TestCase):
    def test_q_key_is_bound_to_actual_quit_method(self):
        controls=next(n for n in GAME.body if isinstance(n,ast.FunctionDef) and n.name=='_bind_controls')
        keys={n.value for n in ast.walk(controls) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
        self.assertIn('q',keys)
        self.assertIn('shift-q',keys)
        fake=FakeGame()
        method('quit_game')(fake)
        self.assertEqual(fake.exit_calls,1)

    def test_flares_are_spawned_from_real_event_handler(self):
        fake=FakeGame()
        fn=method('deploy_flares',{'Vec3':V,'Flare':FakeFlare,
                                  'CYAN':'cyan','RED':'red'})
        fn(fake)
        self.assertEqual(len(fake.flares),6)
        self.assertEqual(fake.flare_ammo,2)
        self.assertEqual(fake.smoke_count,6)
        self.assertGreater(fake.flare_cooldown,0)
        self.assertTrue(all(f.ttl==3.1 for f in fake.flares))
        self.assertTrue(any(e[0]=='flare' for e in fake.audio.events))
        fn(fake)
        self.assertEqual(fake.flare_ammo,2)  # blocked during cooldown
        fake.flare_cooldown=0
        fn(fake)
        self.assertEqual(fake.flare_ammo,1)

    def test_flare_action_cannot_run_from_pause_or_title(self):
        fake=FakeGame();fake.state='paused'
        method('deploy_flares',{'Vec3':V,'Flare':FakeFlare})(fake)
        self.assertEqual(fake.flare_ammo,3)
        self.assertFalse(fake.flares)

    def test_waves_resets_flares_uses_new_projectile_types(self):
        source=SOURCE.read_text(encoding='utf8')
        for mark in ("'enemy_missile'", "'c':self.deploy_flares", "'tab':self.cycle_target",
                     "'q':self.quit_game", "'k':self.launch_missile",
                     "'j'", 'self._update_sites(dt)', 'self._update_flares(dt)'):
            self.assertIn(mark,source)

    def test_added_audio_assets_exist_and_are_wav(self):
        for name in ('flare','incoming','hit','boss','combo'):
            file=ROOT/'assets'/'audio'/f'{name}.wav'
            self.assertTrue(file.is_file())
            self.assertEqual(file.read_bytes()[:4],b'RIFF')



class BindingDispatchTests(unittest.TestCase):
    def test_q_dispatch_quits_in_menu_pause_flight_and_dead_states(self):
        # Use the real _bind_controls and _guard_event method bodies with a
        # messenger-like fake, not merely an AST string comparison.
        for game_state in ('menu','playing','paused','crashing','dead','error'):
            class Messenger:
                def __init__(self):
                    self.state=game_state
                    self.keys={'j':False,'mouse1':False}
                    self.events={}
                    self.quit_count=0
                    self.errors=[]
                def accept(self,key,callback,extraArgs=None):
                    def fire():
                        if extraArgs is None:return callback()
                        return callback(*extraArgs)
                    self.events[key]=fire
                def quit_game(self):self.quit_count+=1
                def _set_key(self,*args):pass
                def _report_error(self,exception):self.errors.append(str(exception))
            game=Messenger()
            for name in ('launch_missile','deploy_flares','cycle_target','barrel_roll',
                         'cycle_camera','toggle_audio','deploy','eject','go_to_menu',
                         'toggle_pause','on_escape','toggle_fullscreen','demo_crash',
                         'demo_damage'):
                setattr(game,name,lambda:None)
            # Manual binding of the actual flight-key callback guard.
            game._guard_event=lambda action:method('_guard_event')(game,action)
            method('_bind_controls')(game)
            self.assertIn('q',game.events)
            game.events['q']()
            self.assertEqual(game.quit_count,1)
            self.assertFalse(game.errors)
            game.events['shift-q']()
            self.assertEqual(game.quit_count,2)

class SpawnIntegrationTests(unittest.TestCase):
    def test_real_spawn_wave_creates_variety_and_ground_sams(self):
        from battlepy.mathx import terrain_height
        from types import SimpleNamespace

        class MockWorld:
            height=staticmethod(terrain_height)
        class RealSpawnGame(FakeGame):
            def __init__(self):
                super().__init__()
                self.jet=Jet()
                self.wave=0
                self.enemy_serial=0
                self.enemies=[]
                self.sites=[]
                self.hull=82
                self.boost_energy=.5
                self.flare_ammo=1
                self.world=MockWorld()
                self.enemy_prototypes={n:Proto() for n in
                                       ('scout','interceptor','striker','ace')}
                self.sam_prototype=Proto()
                self.spawned=[]

        game=RealSpawnGame()
        names={'Vec3':V, 'math':math, 'HOSTILES':HOSTILES, 'wave_manifest':wave_manifest,
               'sam_count':sam_count, 'Enemy':lambda *a,**kw:SimpleNamespace(
                   node=a[0],pos=a[1],velocity=a[2],hp=a[3],serial=a[4],
                   phase=a[5],fire_timer=a[6],age=0,kind=kw.get('kind','scout')),
               'GroundSite':lambda *a,**kw:SimpleNamespace(
                   node=a[0],pos=a[1],hp=a[2],serial=a[3],fire_timer=a[4],kind='sam'),
               'RED':'red'}
        spawner=method('_spawn_wave',names)
        sam_spawner=method('_spawn_sam_sites',names)
        game._spawn_sam_sites=lambda n:sam_spawner(game,n)
        spawner(game)
        self.assertEqual(game.wave,1)
        self.assertEqual(len(game.enemies),3)
        self.assertEqual(len(game.sites),0)
        self.assertEqual({e.kind for e in game.enemies},{'scout','interceptor'})
        self.assertGreaterEqual(game.hull,82)
        game.enemies.clear()
        spawner(game)
        self.assertEqual(game.wave,2)
        self.assertEqual(len(game.enemies),5)
        self.assertIn('striker',{e.kind for e in game.enemies})
        game.enemies.clear()
        spawner(game)
        self.assertEqual(game.wave,3)
        self.assertGreaterEqual(len(game.sites),1)
        self.assertTrue(all(site.pos.z>12 for site in game.sites))
        game.enemies.clear();game.sites.clear()
        spawner(game)
        self.assertEqual(game.wave,4)
        self.assertIn('ace',{e.kind for e in game.enemies})
        self.assertTrue(any('boss' in event for event in game.audio.events))

class ProjectileIntegrationTests(unittest.TestCase):
    def test_live_enemy_missile_is_drawn_away_by_flare(self):
        from types import SimpleNamespace
        from battlepy.mathx import clamp
        def seg_dist(a,b,c):
            v=b-a
            length=v.lengthSquared()
            if length<.00001:return (c-a).lengthSquared()
            q=clamp((c-a).dot(v)/length,0.,1.)
            return (c-(a+v*q)).lengthSquared()
        class EmptyWorld:
            def height(self,x,y):return -100
        class ProjectileGame(FakeGame):
            def __init__(self):
                super().__init__()
                self.projectiles=[]
                self.enemies=[]
                self.sites=[]
                self.world=EmptyWorld()
                self.red_blast=Proto();self.blue_blast=Proto()
                self.particles=[]
                self.impacts=[]
                self.damage=[]
            def _explode(self,*args):self.impacts.append(args)
            def _take_damage(self,*args):self.damage.append(args)
        game=ProjectileGame()
        shot=SimpleNamespace(node=Node(),pos=V(10,100,120),vel=V(0,-200,0),
                             age=0.,ttl=6.1,kind='enemy_missile',target=None,
                             damage=24.,smoke_timer=-100.)
        game.projectiles=[shot]
        flare=FakeFlare(Node(),V(10,58,120),V(),3.1,3.1)
        game.flares=[flare]
        fn=method('_update_projectiles',{
            'Vec3':V,'segment_dist_sq':seg_dist,'clamp':clamp,
            'missile_turn_rate':missile_turn_rate,
            'CYAN':'cyan','GroundSite':type('DummySite',(),{})})
        for i in range(25):
            if not game.projectiles:break
            fn(game,.08)
        self.assertFalse(game.projectiles,'the guided missile should strike the decoy')
        self.assertFalse(game.flares)
        self.assertEqual(game.damage,[], 'the decoyed missile must not harm the player')
        self.assertTrue(game.impacts)

if __name__ == '__main__':
    unittest.main()
