"""BATTLE / PY — a complete, original 3D arcade jet-combat game.

The code is intentionally organized around simple, inspectable systems rather
than a large engine abstraction: flight, environment, combat, audio, and HUD.
"""
from __future__ import annotations

import json
import math
import random
import traceback
from pathlib import Path
from dataclasses import dataclass, field

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    AntialiasAttrib, ClockObject, Filename, LineSegs, PerspectiveLens,
    Point2, Vec3, Vec4, WindowProperties,
)

from .audio import Soundscape
from .geometry import (
    create_drone, create_explosion_core, create_jet, create_missile, create_tracer,
    create_smoke, create_splash, create_wreckage, create_ejection_seat,
    create_hostile_fighter, create_sam_site,
)
from .hud import HUD, CYAN, GOLD, RED
from .combat import HOSTILES, wave_manifest, sam_count, aim_lead, missile_turn_rate, threat_level
from .mathx import clamp, damp, lerp
from .survival import (evaluate_impact, collision_damage, damage_state, smoke_rate)
from .settings import (
    GUN_INTERVAL, JET_BOOST_SPEED, JET_CRUISE_SPEED, JET_MAX_HULL,
    JET_MAX_SPEED, JET_MIN_SPEED, MISSILE_CAPACITY, MISSILE_RECHARGE_SECONDS,
    START_POS, TITLE, VERSION,
)
from .world import World


@dataclass
class Enemy:
    node: object
    pos: Vec3
    velocity: Vec3
    hp: float
    serial: int
    phase: float
    fire_timer: float
    age: float = 0.
    kind: str = 'scout'
    evasion: float = 0.


@dataclass
class GroundSite:
    node: object
    pos: Vec3
    hp: float
    serial: int
    fire_timer: float
    kind: str = 'sam'


@dataclass
class Flare:
    node: object
    pos: Vec3
    vel: Vec3
    ttl: float
    start_ttl: float


@dataclass
class Projectile:
    node: object
    pos: Vec3
    vel: Vec3
    age: float
    ttl: float
    kind: str
    target: object | None = None
    damage: float = 0.
    smoke_timer: float = 0.


@dataclass
class Particle:
    node: object
    pos: Vec3
    vel: Vec3
    life: float
    ttl: float
    initial_scale: float
    fades: bool = True
    kind: str = 'spark'


@dataclass
class Wreck:
    node: object
    pos: Vec3
    velocity: Vec3
    spin: Vec3
    ttl: float
    bounced: bool = False


def segment_dist_sq(a: Vec3,b: Vec3,c: Vec3) -> float:
    v=b-a
    length=v.lengthSquared()
    if length<.00001:return (c-a).lengthSquared()
    q=clamp((c-a).dot(v)/length,0.,1.)
    return (c-(a+v*q)).lengthSquared()


class BattlePy(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setFrameRateMeter(False)
        self.render.setAntialias(AntialiasAttrib.MAuto)
        self.win.setClearColor(Vec4(.10,.18,.25,1))
        props=WindowProperties()
        props.setTitle(f'{TITLE}  —  THE WRAITH PROTOCOL')
        props.setIconFilename(Filename.fromOsSpecific(str(Path(__file__).resolve().parent.parent/'assets/textures/icon.png')))
        self.win.requestProperties(props)
        lens=PerspectiveLens()
        lens.setFov(78)
        lens.setNear(0.12)
        lens.setFar(12000)
        self.cam.node().setLens(lens)
        self.camLens=lens
        self.camera.reparentTo(self.render)
        self.game_time=0.
        self.highscore_path=Path.home()/'.battle_py_highscore.json'
        self.best_score=self._read_highscore()
        self.random=random.Random(94034)
        self.world=World(self)
        self.jet,self.exhausts,self.racks=create_jet()
        self.jet.reparentTo(self.render)
        self.jet.setPos(*START_POS)
        self.jet.setHpr(17,-1.5,0)
        self.drone_prototype=create_drone()
        self.enemy_prototypes={kind:create_hostile_fighter(kind)
                               for kind in ('scout','interceptor','striker','ace')}
        self.sam_prototype=create_sam_site()
        self.hostile_missile_prototype=create_missile()
        self.hostile_missile_prototype.setColorScale(1.,.45,.35,1.)
        self.missile_prototype=create_missile()
        self.cannon_prototype=create_tracer(4.8)
        self.laser_prototype=create_tracer(2.6,(1.,.30,.22,1))
        self.blast_prototype=create_explosion_core()
        self.red_blast=create_explosion_core((1.,.24,.12,1))
        self.blue_blast=create_explosion_core((.24,.8,1.,1))
        self.flare_prototype=create_explosion_core((1.,.81,.27,1))
        self.smoke_prototype=create_smoke()
        self.splash_prototype=create_splash()
        self.wreckage_prototypes=create_wreckage()
        self.audio=Soundscape(self)
        self.hud=HUD(self)
        self.keys={k:False for k in
                   ('w','s','a','d','up','down','left','right','shift','lshift','rshift','mouse1','j')}
        self._bind_controls()
        self._fullscreen=False
        self.cam_mode=0
        self.menu_angle=0.
        self.state='menu'
        self._reset_flight()
        self.state='menu'
        self.hud.set_overlay('menu')
        self.taskMgr.add(self._safe_tick,'battle-py-game-loop',sort=10)
        self.accept('window-event',self._on_window_event)
        print('BATTLE-PY',VERSION,'| controls: see README / title screen')

    def _report_error(self,exc):
        """Keep the window alive and show where the error log was saved."""
        signature=(type(exc).__name__,str(exc))
        if self.state=='error' and getattr(self,'_last_error_signature',None)==signature:
            return  # Do not spam identical errors every frame while the error screen is open.
        self._last_error_signature=signature
        trace=traceback.format_exc()
        print('\n[BATTLE-PY] ERROR\n'+trace,flush=True)
        log=Path(__file__).resolve().parent.parent/'battle-py-error.log'
        try:
            log.write_text(trace,encoding='utf8')
        except OSError:
            log=Path.home()/'battle-py-error.log'
            try:log.write_text(trace,encoding='utf8')
            except OSError:pass
        self.state='error'
        try:
            self.audio.enter_crash(False)
            self.hud.set_error(f'{type(exc).__name__}: {str(exc)}',str(log))
        except Exception:
            # The console and error log are still available if the HUD fails.
            pass

    def _guard_event(self,action):
        """Panda3D messenger callbacks run outside of the frame-task guard."""
        def safe_callback(*args):
            try:
                action(*args)
            except Exception as exc:
                self._report_error(exc)
        return safe_callback

    def _safe_tick(self,task):
        """A failed gameplay frame changes to an error screen, not an exit."""
        try:
            if self.state=='error':return Task.cont
            return self._tick(task)
        except Exception as exc:
            self._report_error(exc)
            return Task.cont

    def on_escape(self):
        if self.state in ('dead','error'):
            self.go_to_menu()
        elif self.state=='crashing':
            self._finish_crash()
        else:
            self.toggle_pause()

    def go_to_menu(self):
        if self.state not in ('dead','error','paused','crashing'):return
        self._reset_flight()
        self.state='menu'
        self.hud.set_overlay('menu')

    def _read_highscore(self):
        try:
            return int(json.loads(self.highscore_path.read_text()).get('best',0))
        except (OSError,ValueError,TypeError):
            return 0

    def _save_highscore(self):
        self.best_score=max(self.best_score,self.score)
        try:
            self.highscore_path.write_text(json.dumps({'best':self.best_score}))
        except OSError:
            # No save permission is not a reason to interrupt gameplay.
            pass

    def _bind_controls(self):
        for key in self.keys:
            self.accept(key,self._guard_event(self._set_key),[key,True])
            self.accept(key+'-up',self._guard_event(self._set_key),[key,False])
        actions={
            'mouse3':self.launch_missile,
            'f':self.launch_missile,
            'k':self.launch_missile,
            'c':self.deploy_flares,
            'tab':self.cycle_target,
            'q':self.quit_game,
            'shift-q':self.quit_game,
            'space':self.barrel_roll,
            'v':self.cycle_camera,
            'm':self.toggle_audio,
            'enter':self.deploy,
            'r':self.deploy,
            'e':self.eject,
            'backspace':self.go_to_menu,
            'p':self.toggle_pause,
            'escape':self.on_escape,
            'f11':self.toggle_fullscreen,
            'f8':self.demo_crash,
            'f9':self.demo_damage,
        }
        for key,action in actions.items():
            self.accept(key,self._guard_event(action))

    def quit_game(self):
        """Dedicated Q key: exit from menu, flying, paused, crash or results."""
        self.userExit()

    def _set_key(self,key,value):
        self.keys[key]=value

    def _reset_flight(self):
        self._last_error_signature=None
        for enemy in getattr(self,'enemies',[]): enemy.node.removeNode()
        for site in getattr(self,'sites',[]): site.node.removeNode()
        for flare in getattr(self,'flares',[]): flare.node.removeNode()
        for projectile in getattr(self,'projectiles',[]): projectile.node.removeNode()
        for particle in getattr(self,'particles',[]): particle.node.removeNode()
        for piece in getattr(self,'wreckage',[]): piece.node.removeNode()
        if getattr(self,'eject_node',None) is not None:
            self.eject_node.removeNode()
        self.eject_node=None
        if hasattr(self,'contrail_path'):self.contrail_path.removeNode()
        self.contrail_path=self.render.attachNewNode('WingtipVortices')
        self.contrails=[[],[]]
        self.contrail_clock=0.
        self.enemies=[]
        self.sites=[]
        self.flares=[]
        self.projectiles=[]
        self.particles=[]
        self.wreckage=[]
        self.game_time=0.
        self.crash_clock=0.
        self.crash_anchor=Vec3(*START_POS)
        self.death_cause=''
        self.pilot_survived=False
        self.crash_water=False
        self.damage_flash=0.
        self.camera_shake=0.
        self.ship_smoke_timer=0.
        self.critical_alarm_timer=0.
        self.crash_smoke_timer=0.
        self.eject_velocity=Vec3(0,0,0)
        self.eject_chute=None
        self.eject_lines=None
        self.cam_mode=0
        self.jet.show()
        self.wave=0
        self.wave_delay=1.0
        self.enemy_serial=0
        self.score=0
        self.kills=0
        self.streak=0
        self.multikill_timer=0.
        self.gun_hits=0
        self.missile_kills=0
        self.shots_fired=0
        self.incoming_warning=0.
        self.last_threat_notice=-10.
        self.incoming_count=0
        self.target_override=None
        self.target_override_timer=0.
        self.flare_ammo=3
        self.flare_reload=0.
        self.flare_cooldown=0.
        self.flare_flash=0.
        self.hit_flash=0.
        self.hull=JET_MAX_HULL
        self.ammo=MISSILE_CAPACITY
        self.reload_clock=0.
        self.boost_energy=1.0
        self.gun_heat=0.
        self.gun_clock=0.
        self.damage_cooldown=0.
        self.speed=JET_CRUISE_SPEED
        self.throttle=.60
        self.heading=16.
        self.pitch=-1.5
        self.roll=0.
        self.yaw_rate=0.
        self.pitch_rate=0.
        self.barrel_timer=0.
        self.boosting=False
        self.locked=False
        self.target=None
        self.camera_distance=37.
        self.camera_height=11.
        self.jet.setPos(*START_POS)
        self.jet.setHpr(self.heading,self.pitch,self.roll)
        self.camera.setPos(self.jet.getPos()+Vec3(-30,-52,22))
        self.camera.lookAt(self.jet.getPos()+Vec3(0,0,4))
        for pod in self.racks:pod.show()
        self.hud.notice.setText('')
        self.hud.update_damage(0.,self.game_time)
        self.audio.reset()

    def deploy(self):
        if self.state in ('menu','dead','error'):
            self._reset_flight()
            self.state='playing'
            self.hud.set_overlay('playing')
            self.audio.play('ui',.55)
            self.hud.notify('WEAPONS HOT  //  CLEAR THE SECTOR',3.1,CYAN)
            self.wave_delay=1.8
        elif self.state=='paused':
            self.toggle_pause()

    def toggle_pause(self):
        if self.state=='playing':
            self.state='paused';self.hud.set_overlay('paused')
            self.audio.play('ui',.4)
        elif self.state=='paused':
            self.state='playing';self.hud.set_overlay('playing')
            self.audio.play('ui',.4)

    def toggle_audio(self):
        enabled=self.audio.toggle()
        self.hud.notify('AUDIO ONLINE' if enabled else 'AUDIO MUTED',1.8,CYAN)

    def cycle_camera(self):
        self.cam_mode=(self.cam_mode+1)%3
        self.audio.play('ui',.28)
        self.hud.notify(('CHASE CAM','COCKPIT CAM','ORBIT CAM')[self.cam_mode],1.3,CYAN)
        self.jet.show() if self.cam_mode!=1 else self.jet.hide()
        # A hidden model is still moved and used for physics; only the camera changes.

    def toggle_fullscreen(self):
        self._fullscreen=not self._fullscreen
        props=WindowProperties();props.setFullscreen(self._fullscreen)
        self.win.requestProperties(props)

    def _on_window_event(self,window):
        if window and window.hasSize():
            # HUD is scaled by aspect2d automatically; the targeting projection below
            # consults the same aspect ratio and stays aligned after a resize.
            pass

    def barrel_roll(self):
        if self.state!='playing' or self.barrel_timer>0:return
        self.barrel_timer=.86
        self.audio.play('roll',.63,1.02+self.speed/800.)
        self.hud.notify('HIGH-G MANOEUVRE',1.0,CYAN)

    def launch_missile(self):
        if self.state!='playing' or self.ammo<=0:
            if self.state=='playing' and self.ammo<=0:self.hud.notify('VIPER PODS RELOADING',1.2,RED)
            return
        which=MISSILE_CAPACITY-self.ammo
        rack=self.racks[which]
        source=rack.getPos(self.render)
        self.ammo-=1
        rack.hide()
        direction=self.jet.getQuat(self.render).getForward()
        velocity=direction*240+Vec3(0,0,-7)
        node=self.missile_prototype.copyTo(self.render)
        node.setPos(source)
        node.setQuat(self.jet.getQuat(self.render))
        self.projectiles.append(Projectile(node,Vec3(source),velocity,0.,4.3,'missile',
                                           self.target if self.locked else None,68.,0.))
        self.audio.play('missile',.82,.90+self.random.random()*.16)
        self._flash(source,(.30,.86,1.,1),1.7)
        self.hud.notify('VIPER AWAY  //  '+('FOX 3' if self.locked else 'UNGUIDED'),1.2,GOLD)

    def _fire_cannon(self):
        if self.gun_clock>0 or self.gun_heat>.99:return
        self.gun_clock=GUN_INTERVAL
        self.gun_heat=clamp(self.gun_heat+.087,0.,1.2)
        self.shots_fired+=2
        direction=self.jet.getQuat(self.render).getForward()
        for x in (-1.55,1.55):
            local=Vec3(x,7.2,-.15)
            source=self.jet.getPos()+self.jet.getQuat(self.render).xform(local)
            jitter=Vec3(self.random.uniform(-.011,.011),self.random.uniform(-.006,.006),
                        self.random.uniform(-.009,.009))
            velocity=(direction+jitter).normalized()*590
            node=self.cannon_prototype.copyTo(self.render)
            node.setPos(source);node.setQuat(self.jet.getQuat(self.render))
            self.projectiles.append(Projectile(node,Vec3(source),velocity,0.,1.20,
                                               'cannon',None,15.))
            if self.random.random()>.7:self._flash(source,(1.,.75,.32,1),.55)
        self.audio.play('cannon',.55,.90+self.random.uniform(-.07,.07))

    def deploy_flares(self):
        """C: eject hot decoys to divert actively tracking enemy missiles."""
        if self.state!='playing':return
        if self.flare_ammo<1 or self.flare_cooldown>0:
            self.hud.notify('COUNTERMEASURES NOT READY',.85,RED)
            return
        self.flare_ammo-=1
        self.flare_cooldown=1.1
        q=self.jet.getQuat(self.render)
        pos=self.jet.getPos()
        for side in (-1,1):
            for j in range(3):
                offset=q.xform(Vec3(side*(2.9+j*.65),-7.5-j*1.1,-.7))
                origin=Vec3(pos)+offset
                node=self.flare_prototype.copyTo(self.render)
                node.setLightOff();node.setPos(origin)
                node.setScale(.70+j*.16)
                v=(-q.getForward()*(27+j*8)+q.getRight()*side*(22+j*9)+
                   Vec3(0,0,-22-self.random.uniform(2,18)))
                self.flares.append(Flare(node,origin,v,3.1,3.1))
                self._smoke(origin,.5)
        self.audio.play('flare',.76)
        self.hud.notify('CHAFF / FLARES  //  DISPENSED',1.1,CYAN)
        self.camera_shake=max(self.camera_shake,.35)

    def cycle_target(self):
        """TAB manually selects an enemy or anti-aircraft emplacement."""
        if self.state!='playing':return
        targets=[x for x in self.enemies+self.sites
                 if (x.pos-self.jet.getPos()).length()<1200]
        if not targets:
            self.target_override=None
            self.hud.notify('NO HOSTILE TRACKS',.95,CYAN)
            return
        targets.sort(key=lambda x:((x.pos-self.jet.getPos()).length(), x.serial))
        if self.target_override in targets:
            idx=(targets.index(self.target_override)+1)%len(targets)
        else: idx=0
        self.target_override=targets[idx]
        self.target_override_timer=12.
        name=HOSTILES[self.target_override.kind].callsign
        self.audio.play('lock',.40)
        self.hud.notify(f'MANUAL TRACK  //  {name}-{self.target_override.serial:03d}',1.2,GOLD)

    def _combat_hit(self,damage,kind):
        """Visible hit confirmation (not just invisible changes to enemy HP)."""
        self.hit_flash=.26
        self.gun_hits+=1 if kind=='cannon' else 0
        self.audio.play('hit',.27 if kind=='cannon' else .52)

    def _fire_hostile_missile(self,position,velocity,source='AIR'):
        if self.state!='playing':return
        # Cap heavy projectiles so late waves never saturate the game loop.
        if sum(p.kind=='enemy_missile' for p in self.projectiles)>=8:return
        origin=Vec3(position)
        vec=Vec3(velocity)
        if vec.lengthSquared()<1:vec=Vec3(0,1,0)
        node=self.hostile_missile_prototype.copyTo(self.render)
        node.setScale(.85)
        node.setPos(origin)
        node.lookAt(origin+vec)
        self.projectiles.append(Projectile(node,origin,vec,0.,6.1,
                                           'enemy_missile',None,24.,0.))
        self.audio.play('incoming',.54)
        self.incoming_warning=1.8
        if self.game_time-self.last_threat_notice>1.8:
            self.hud.notify('MISSILE INBOUND  //  PRESS C FOR FLARES',1.8,RED)
            self.last_threat_notice=self.game_time

    def _update_flares(self,dt):
        self.flare_cooldown=max(0.,self.flare_cooldown-dt)
        if self.flare_ammo<3:
            self.flare_reload+=dt
            if self.flare_reload>=12:
                self.flare_reload=0.
                self.flare_ammo+=1
                self.audio.play('ui',.23,1.4)
        self.flare_flash=max(0.,self.flare_flash-dt)
        for flare in list(self.flares):
            flare.ttl-=dt
            if flare.ttl<=0:
                flare.node.removeNode();self.flares.remove(flare)
                continue
            flare.vel.z-=8*dt
            flare.pos+=flare.vel*dt
            flare.node.setPos(flare.pos)
            f=flare.ttl/flare.start_ttl
            flare.node.setScale((.6+.5*abs(math.sin(self.game_time*31)))*f+.12)
            if self.random.random()<.25:
                self._smoke(flare.pos,.28)

    def _flash(self,position,color,size):
        node=self.blast_prototype.copyTo(self.render)
        node.setColorScale(*color)
        node.setPos(position)
        node.setScale(size)
        self.particles.append(Particle(node,Vec3(position),Vec3(0,0,0),.11,.11,size))

    def _explode(self,position,magnitude=1.,friendly=False):
        self.audio.play('explosion',clamp(.36+magnitude*.28,0.,.96),
                        self.random.uniform(.84,1.10))
        # An expanding flash followed by a constellation of steel-orange embers.
        core=(self.blue_blast if friendly else self.blast_prototype).copyTo(self.render)
        core.setPos(position);core.setScale(2.*magnitude)
        self.particles.append(Particle(core,Vec3(position),Vec3(0,0,0),.43,.43,2.*magnitude))
        for i in range(int(12*magnitude)):
            a=self.random.random()*math.tau
            z=self.random.uniform(-.8,.8)
            speed=self.random.uniform(19,85)*magnitude
            vel=Vec3(math.cos(a)*speed,math.sin(a)*speed,z*speed)
            node=(self.red_blast if i%3 else self.blast_prototype).copyTo(self.render)
            p=Vec3(position)
            node.setPos(p)
            scale=self.random.uniform(.25,.85)*magnitude
            node.setScale(scale)
            life=self.random.uniform(.32,.88)
            self.particles.append(Particle(node,p,vel,life,life,scale))

    def _spawn_wave(self):
        self.wave+=1
        lineup=wave_manifest(self.wave)
        ahead=self.jet.getQuat(self.render).getForward()
        right=self.jet.getQuat(self.render).getRight()
        self.hull=min(100.,self.hull+(14 if self.wave>1 else 0))
        self.boost_energy=min(1.,self.boost_energy+.24)
        self.flare_ammo=min(3,self.flare_ammo+1)
        for i,kind in enumerate(lineup):
            spec=HOSTILES[kind]
            dist=340+self.random.uniform(55,350)
            lateral=(i-(len(lineup)-1)*.5)*85 + self.random.uniform(-75,75)
            pos=(self.jet.getPos()+ahead*dist+right*lateral+
                 Vec3(0,0,self.random.uniform(-65,105)))
            pos.z=max(pos.z,self.world.height(pos.x,pos.y)+95.,95.)
            node=self.enemy_prototypes[kind].copyTo(self.render)
            node.setPos(pos);node.setScale(spec.scale)
            node.lookAt(self.jet.getPos())
            self.enemy_serial+=1
            phase=self.random.uniform(0,math.tau)
            velocity=(self.jet.getPos()-pos).normalized()*self.random.uniform(50,85)
            self.enemies.append(Enemy(node,Vec3(pos),velocity,
                                      spec.hitpoints+min(45,self.wave*3),
                                      self.enemy_serial,phase,
                                      self.random.uniform(1.1,3.4),
                                      kind=kind))
        self._spawn_sam_sites(sam_count(self.wave))
        if 'ace' in lineup:
            self.hud.notify(f'WAVE {self.wave:02d}  //  SPECTRE ACE ENTERING AIRSPACE',3.4,RED)
            self.audio.play('boss',.76)
        else:
            count=len(lineup)+len(self.sites)
            self.hud.notify(f'WAVE {self.wave:02d}  //  {count} HOSTILE TARGETS',3.1,RED)
            self.audio.play('lock',.47,.84)

    def _spawn_sam_sites(self,count):
        """Pick real terrain, avoiding underwater or steep cliff placements."""
        q=self.jet.getQuat(self.render)
        forward=q.getForward()
        right=q.getRight()
        home=self.jet.getPos()
        for index in range(count):
            chosen=None
            for attempt in range(60):
                dist=self.random.uniform(330,830)
                lateral=self.random.uniform(-660,660)
                candidate=home+forward*dist+right*lateral
                ground=self.world.height(candidate.x,candidate.y)
                if 12 < ground < 245:
                    chosen=Vec3(candidate.x,candidate.y,ground+1.0)
                    break
            if chosen is None:
                # No suitably dry island in the current sector; skip gracefully.
                continue
            node=self.sam_prototype.copyTo(self.render)
            node.setPos(chosen)
            node.setH(self.random.uniform(0,360))
            self.enemy_serial+=1
            self.sites.append(GroundSite(node,chosen,HOSTILES['sam'].hitpoints,
                                         self.enemy_serial,self.random.uniform(2.8,5.1)))

    def _award_kill(self,kind):
        spec=HOSTILES[kind]
        self.kills+=1
        self.streak+=1
        self.multikill_timer=4.5
        points=(spec.score+self.wave*18)*min(self.streak,5)
        self.score+=points
        self.boost_energy=clamp(self.boost_energy+.05,0,1)
        self.audio.play('victory',.15,1.15 if kind!='ace' else .83)
        label='ACE ELIMINATED' if kind=='ace' else (
            'SAM NEUTRALIZED' if kind=='sam' else f'{spec.callsign} DOWN')
        self.hud.notify(f'{label}  //  +{points}',1.4,GOLD)
        if self.streak>=3 and self.streak%3==0:
            self.audio.play('combo',.65)
            self.hud.notify(f'{self.streak}X KILL CHAIN  //  NO MERCY',1.6,GOLD)
        self._check_wave_clear()

    def _check_wave_clear(self):
        if self.enemies or self.sites:return
        self.target=None
        self.target_override=None
        self.wave_delay=3.6
        bonus=max(250,self.streak*110)
        self.score+=bonus
        self.hud.notify(f'SECTOR SECURED  //  +{bonus} CLEAR BONUS',2.7,CYAN)
        self.streak=0

    def _destroy_enemy(self,enemy):
        if enemy not in self.enemies:return
        self.enemies.remove(enemy)
        self._explode(enemy.pos,2.7 if enemy.kind=='ace' else
                      2.1 if enemy.kind=='striker' else 1.4)
        enemy.node.removeNode()
        if self.target is enemy:self.target=None
        if self.target_override is enemy:self.target_override=None
        self._award_kill(enemy.kind)

    def _destroy_site(self,site):
        if site not in self.sites:return
        self.sites.remove(site)
        self._explode(site.pos+Vec3(0,0,3),2.5)
        site.node.removeNode()
        if self.target is site:self.target=None
        if self.target_override is site:self.target_override=None
        self._award_kill('sam')


    def _take_damage(self,value,origin='HOSTILE FIRE'):
        if self.damage_cooldown>0 or self.state!='playing':return
        self.hull=max(0.,self.hull-value)
        self.damage_cooldown=.37
        self.damage_flash=.30+min(.43,value*.012)
        self.camera_shake=max(self.camera_shake,min(3.2,value*.042))
        self.audio.play('damage',.72)
        self.hud.notify(origin+f'  //  HULL {int(self.hull)}%',1.4,RED)
        if self.hull<=0:
            self._start_crash(origin,self.jet.getPos(),False)
        elif self.hull<=25:
            self.audio.play('alarm',.34)

    def demo_crash(self):
        """Optional cinematic demo, useful for checking crashes without a long flight."""
        if self.state=='playing':
            self._start_crash('ENGINE FAILURE',self.jet.getPos())

    def demo_damage(self):
        """Optional damage demo: make the aircraft smoke and sound an alarm."""
        if self.state=='playing':
            self.damage_cooldown=0
            self._take_damage(42,'ENGINE FIRE')

    def eject(self):
        """Abort the mission and save the pilot; the aircraft still crashes."""
        if self.state!='playing':return
        pos=Vec3(self.jet.getPos())
        self._start_crash('EMERGENCY EJECTION',pos,False,eject=True)
        self.audio.play('eject',.93)
        self.hud.crash_title.setText('PILOT EJECTED')
        self.hud.crash_detail.setText('PARACHUTE DEPLOYING')

    def _start_crash(self,cause,position,water=False,eject=False):
        if self.state!='playing':return
        self.death_cause=cause
        self.pilot_survived=eject
        self.crash_water=water
        self.hull=0.
        self.crash_clock=0.
        self.crash_smoke_timer=0.
        self.crash_anchor=Vec3(position)
        self.state='crashing'
        self.target=None
        self.locked=False
        self.boosting=False
        self.jet.hide()
        self._save_highscore()
        self.audio.enter_crash(water)
        self.hud.set_overlay('crashing')
        self.hud.crash_title.setText('PILOT EJECTED' if eject else 'MAYDAY  //  MAYDAY')
        self.hud.crash_detail.setText('PILOT SAFE  /  JET LOST' if eject else
                                      ('WATER IMPACT' if water else 'AIRFRAME DISINTEGRATION'))
        self.hud.alt_warning.setText('')
        self.damage_flash=.60
        self.camera_shake=6.3
        self._explode(position,3.3,True)
        if water:
            ring=self.splash_prototype.copyTo(self.render)
            ring.setPos(position.x,position.y,.45)
            ring.setScale(4.8)
            self.particles.append(Particle(ring,Vec3(position.x,position.y,.45),
                                           Vec3(0,0,0),1.8,1.8,4.8,True,'splash'))
        q=self.jet.getQuat(self.render)
        forward=q.getForward()
        for prototype,local in self.wreckage_prototypes:
            node=prototype.copyTo(self.render)
            origin=Vec3(position)+q.xform(local)
            node.setPos(origin);node.setQuat(q)
            debris_velocity=(forward*self.speed*.28 +
                             Vec3(self.random.uniform(-55,55),self.random.uniform(-35,35),
                                  self.random.uniform(13,61)))
            if water: debris_velocity.z+=12
            self.wreckage.append(Wreck(node,origin,debris_velocity,
                                  Vec3(self.random.uniform(-300,300),self.random.uniform(-250,250),
                                       self.random.uniform(-500,500)),
                                  self.random.uniform(5.,9.)))
        if eject:
            self.eject_node,self.eject_chute,self.eject_lines=create_ejection_seat()
            self.eject_node.reparentTo(self.render)
            self.eject_node.setPos(Vec3(position)+Vec3(0,0,6))
            self.eject_velocity=forward*self.speed*.25+Vec3(0,0,52)

    def _finish_crash(self):
        if self.state!='crashing':return
        self.state='dead'
        self.audio.update(0,False,0,0,.03)
        self.hud.crash_layer.hide()
        self.hud.set_overlay('dead')
        self.hud.set_results(self)

    def _update_wreckage(self,dt):
        for piece in list(self.wreckage):
            piece.ttl-=dt
            if piece.ttl<=0:
                piece.node.removeNode()
                self.wreckage.remove(piece)
                continue
            piece.velocity.z-=37*dt
            piece.pos+=piece.velocity*dt
            ground=max(0,self.world.height(piece.pos.x,piece.pos.y))
            if piece.pos.z<ground+.5:
                piece.pos.z=ground+.5
                if not piece.bounced and piece.velocity.z < -8:
                    piece.velocity.z=-piece.velocity.z*.24
                    piece.velocity.x*=.63
                    piece.velocity.y*=.63
                    piece.bounced=True
                else:
                    piece.velocity=Vec3(0,0,0)
                    piece.spin*=.40
            piece.node.setPos(piece.pos)
            piece.node.setHpr(piece.node.getH()+piece.spin.x*dt,
                              piece.node.getP()+piece.spin.y*dt,
                              piece.node.getR()+piece.spin.z*dt)

    def _smoke(self,position,size=1.,fire=False):
        if len(self.particles)>280:return
        node=(self.red_blast if fire else self.smoke_prototype).copyTo(self.render)
        p=Vec3(position)
        p+=Vec3(self.random.uniform(-1.8,1.8),self.random.uniform(-1.8,1.8),
                self.random.uniform(-1,1))
        node.setPos(p)
        scale=size*self.random.uniform(.72,1.25)
        node.setScale(scale)
        vel=Vec3(self.random.uniform(-3,3),self.random.uniform(-3,3),
                 self.random.uniform(4,15))
        lifetime=self.random.uniform(.70,1.65) if not fire else self.random.uniform(.15,.32)
        self.particles.append(Particle(node,p,vel,lifetime,lifetime,scale,True,
                                       'smoke' if not fire else 'flame'))

    def _update_aircraft_damage(self,dt):
        self.critical_alarm_timer=max(0.,self.critical_alarm_timer-dt)
        if self.hull<25 and self.critical_alarm_timer<=0.:
            self.audio.play('alarm',.27)
            self.critical_alarm_timer=3.2
        rate=smoke_rate(self.hull)
        if not rate:return
        self.ship_smoke_timer+=dt*rate
        q=self.jet.getQuat(self.render)
        pos=self.jet.getPos()+q.xform(Vec3(0,-8.5,-.75))
        while self.ship_smoke_timer>=1.:
            self.ship_smoke_timer-=1.
            self._smoke(pos,1.3 if self.hull<25 else .75,fire=self.hull<25 and
                        self.random.random()<.18)

    def _update_ejection(self,dt):
        if self.eject_node is None:return
        p=self.eject_node.getPos()
        if self.crash_clock>.85:
            self.eject_chute.show();self.eject_lines.show()
            self.eject_velocity.z=damp(self.eject_velocity.z,-6,2.8,dt)
            self.eject_velocity.x*=max(0,1-dt*.40)
            self.eject_velocity.y*=max(0,1-dt*.40)
        else:self.eject_velocity.z-=19*dt
        p+=self.eject_velocity*dt
        ground=max(0,self.world.height(p.x,p.y))+3
        if p.z<ground:
            p.z=ground
            self.eject_velocity=Vec3(0,0,0)
        self.eject_node.setPos(p)
        self.eject_node.setH(self.eject_node.getH()+dt*36)

    def _update_crash(self,dt):
        self.crash_clock+=dt
        self._update_particles(dt)
        self._update_wreckage(dt)
        self._update_ejection(dt)
        self.crash_smoke_timer+=dt
        if self.crash_smoke_timer>.075 and self.crash_clock<3.4:
            self.crash_smoke_timer=0
            anchor=self.crash_anchor+Vec3(0,0,2)
            self._smoke(anchor,2.0+self.crash_clock*.55)
            if self.crash_clock<1.5 and not self.crash_water:
                self._smoke(anchor,.9,True)
        self.camera_shake=max(0.,self.camera_shake-dt*5.)
        anchor=self.eject_node.getPos() if self.eject_node is not None else self.crash_anchor
        az=.52*self.crash_clock + self.menu_angle
        desired=anchor+Vec3(math.cos(az)*46,-math.sin(az)*51,19+self.crash_clock*2)
        self.camera.setPos(self.camera.getPos()+(desired-self.camera.getPos())*
                           clamp(dt*2.1,0,1))
        shake=min(3.8,self.camera_shake)
        self.camera.setPos(self.camera.getPos()+Vec3(self.random.uniform(-shake,shake),
                          self.random.uniform(-shake,shake),self.random.uniform(-shake,shake)))
        self.camera.lookAt(anchor)
        self.hud.update_damage(max(0.,.25-self.crash_clock*.06)+
                               .07*abs(math.sin(self.crash_clock*11)),self.game_time)
        self.audio.update(0,False,0,0,dt)
        if self.crash_clock>=4.0:self._finish_crash()

    def project_world(self,p):
        relative=self.cam.getRelativePoint(self.render,p)
        film=Point2()
        if not self.cam.node().getLens().project(relative,film):return None
        aspect=self.getAspectRatio()
        x=film.x*aspect
        y=film.y
        if abs(x)>aspect*1.05 or abs(y)>1.05:return None
        return x,y

    def _acquire_target(self):
        candidates=self.enemies+self.sites
        target=None
        best=1000000.
        if self.target_override not in candidates:
            self.target_override=None
            self.target_override_timer=0.
        if self.target_override_timer>0 and self.target_override is not None:
            target=self.target_override
        else:
            for enemy in candidates:
                offset=enemy.pos-self.jet.getPos()
                distance=offset.length()
                if distance>1050:continue
                projected=self.project_world(enemy.pos)
                if projected:
                    sx,sy=projected
                    # Screen centre is the natural dogfighting aperture.
                    metric=(sx*.77)**2+sy**2+distance*.00009
                    if metric<best:best=metric;target=enemy
        self.target=target
        if not target:
            self.locked=False
        else:
            screen=self.project_world(target.pos)
            max_error=.31 if self.target_override is target else .055
            self.locked=bool(screen and
                             (screen[0]**2+screen[1]**2)<max_error and
                             (target.pos-self.jet.getPos()).length()<1050)
            if self.locked and not self.hud.lock_was:
                self.audio.play('lock',.33,1.2)
        self.hud.lock_was=self.locked


    def _tick(self,task):
        dt=clamp(ClockObject.getGlobalClock().getDt(),0.0001,.05)
        self.game_time+=dt
        self.world.update(self.jet.getPos() if self.state!='crashing' else self.crash_anchor,dt)
        self._animate_exhaust(dt)
        if self.state=='playing':
            self._update_flight(dt)
            if self.state=='playing':self._update_enemies(dt)
            if self.state=='playing':self._update_sites(dt)
            if self.state=='playing':self._update_flares(dt)
            if self.state=='playing':self._update_projectiles(dt)
            if self.state=='playing':
                self._update_aircraft_damage(dt)
                self._update_particles(dt)
                self._update_contrails(dt)
                self._update_waves(dt)
                self.target_override_timer=max(0.,self.target_override_timer-dt)
                self.hit_flash=max(0.,self.hit_flash-dt)
                self.multikill_timer=max(0.,self.multikill_timer-dt)
                if self.multikill_timer<=0 and self.streak>1:
                    self.streak=0
                self.incoming_warning=max(0.,self.incoming_warning-dt)
                self.incoming_count=sum(1 for p in self.projectiles
                                        if p.kind=='enemy_missile')
                self._update_camera(dt)
                self._acquire_target()
                if (self.keys['mouse1'] or self.keys['j']) and self.gun_heat<1.:
                    self._fire_cannon()
                self.hud.update(self)
        elif self.state=='menu':
            self._menu_camera(dt)
            self._update_particles(dt)
            self.hud.update_damage(0.,self.game_time)
        elif self.state=='paused':
            self.audio.update(self.speed,False,0,0,dt)
        elif self.state=='crashing':
            self._update_crash(dt)
        elif self.state=='dead':
            self._update_particles(dt)
            self._update_wreckage(dt)
            self._update_ejection(dt)
            self.audio.update(0,False,0,0,dt)
        return Task.cont

    def _animate_exhaust(self,dt):
        pulse=math.sin(self.game_time*26)*.13+math.sin(self.game_time*41)*.05
        power=(1.35 if self.boosting and self.state=='playing' else .58)
        for j,node in enumerate(self.exhausts):
            node.setScale(1.+pulse*.6,(1.5+power*1.2+pulse)*power,1.+pulse*.6)
            if self.state=='dead':node.hide()
            else:node.show()

    def _update_flight(self,dt):
        if self.keys['w']: self.throttle+=dt*.35
        if self.keys['s']: self.throttle-=dt*.39
        self.throttle=clamp(self.throttle,.10,1.)
        boost_held=any(self.keys[k] for k in ('shift','lshift','rshift'))
        self.boosting=boost_held and self.boost_energy>.025
        if self.boosting:
            self.boost_energy=max(0.,self.boost_energy-dt*.24)
        else:
            self.boost_energy=min(1.,self.boost_energy+dt*.12)
        cruise=lerp(JET_MIN_SPEED,JET_MAX_SPEED,self.throttle)
        if self.boosting: cruise=JET_BOOST_SPEED
        self.speed=damp(self.speed,cruise,2.3 if self.boosting else .8,dt)
        self.gun_heat=clamp(self.gun_heat-dt*.20,0,1.2)
        self.gun_clock=max(0.,self.gun_clock-dt)
        self.damage_cooldown=max(0.,self.damage_cooldown-dt)
        self.reload_clock+=dt
        if self.ammo<MISSILE_CAPACITY and self.reload_clock>MISSILE_RECHARGE_SECONDS:
            self.reload_clock=0.
            self.ammo+=1
            self.racks[MISSILE_CAPACITY-self.ammo].show()
            self.audio.play('ui',.30,1.5)
            self.hud.notify('VIPER POD REARMED',1.25,CYAN)
        mouse_x=0.;mouse_y=0.
        if self.mouseWatcherNode.hasMouse():
            mouse=self.mouseWatcherNode.getMouse()
            mouse_x=mouse.x;mouse_y=mouse.y
        key_yaw=(1 if self.keys['d'] or self.keys['right'] else 0)-(
            1 if self.keys['a'] or self.keys['left'] else 0)
        key_pitch=(1 if self.keys['up'] else 0)-(1 if self.keys['down'] else 0)
        steer_x=clamp(mouse_x*.90+key_yaw*.90,-1.,1.)
        steer_y=clamp(mouse_y*.85+key_pitch*.90,-1.,1.)
        turn_rate=56.*(0.78+JET_CRUISE_SPEED/max(self.speed,80)*.27)
        self.yaw_rate=damp(self.yaw_rate,steer_x*turn_rate,3.6,dt)
        self.pitch_rate=damp(self.pitch_rate,steer_y*29,3.1,dt)
        self.heading=(self.heading+self.yaw_rate*dt)%360.
        self.pitch=clamp(self.pitch+self.pitch_rate*dt,-65.,65.)
        # Light fly-by-wire auto-levelling keeps neutral mouse flight comfortable.
        if abs(steer_y)<.08:
            self.pitch=damp(self.pitch,0.,.38,dt)
        bank_target=-steer_x*52.
        if self.barrel_timer>0:
            self.barrel_timer=max(0.,self.barrel_timer-dt)
            f=1-self.barrel_timer/.86
            f=f*f*(3-2*f)
            bank_target+=360*f
        self.roll=damp(self.roll,bank_target,7.0,dt) if self.barrel_timer<=0 else bank_target
        self.jet.setHpr(self.heading,self.pitch,self.roll)
        forward=self.jet.getQuat(self.render).getForward()
        delta=forward*self.speed*dt
        # Lift from airspeed, moderate gravity while slowing and realistic steep dives.
        delta.z+=(self.speed-135.)*.008*dt
        newpos=self.jet.getPos()+delta
        surface=max(0,self.world.height(newpos.x,newpos.y))
        altitude=newpos.z-surface
        if altitude<5.5:
            contact=evaluate_impact(airspeed=self.speed,
                    descent_rate=max(0.,-delta.z/max(dt,.001)),
                    penetration=5.5-altitude,water=surface<1.0)
            if contact.catastrophic:
                self.jet.setPos(newpos.x,newpos.y,surface+2.0)
                self._start_crash(contact.label,Vec3(newpos.x,newpos.y,
                                  0 if contact.water else surface),contact.water)
                return
            newpos.z=surface+7.5
            self.pitch=max(self.pitch,12)
            self._take_damage(contact.damage,contact.label)
            if self.state!='playing':return
        self.jet.setPos(newpos)
        self.audio.update(self.speed,self.boosting,self.barrel_timer>0,
                          clamp((72-altitude)/68,0.,1.),dt,
                          damage=1-self.hull/100.)

    def _update_camera(self,dt):
        pos=self.jet.getPos()
        q=self.jet.getQuat(self.render)
        forward=q.getForward()
        right=q.getRight()
        up=Vec3(0,0,1)
        if self.cam_mode==1:
            desired=pos+forward*6.2+Vec3(0,0,1.36)
            look=pos+forward*220.+Vec3(0,0,4.0)
            speed=12.0
        elif self.cam_mode==2:
            desired=pos-forward*10+right*31+Vec3(0,0,12)
            look=pos+forward*30.+Vec3(0,0,1)
            speed=2.7
        else:
            desired=pos-forward*(35.+self.speed*.023)+up*11.+right*1.25
            look=pos+forward*155+Vec3(0,0,2)
            speed=4.8
        t=1-math.exp(-speed*dt)
        self.camera.setPos(self.camera.getPos()+(desired-self.camera.getPos())*t)
        shake=min(2.2,self.camera_shake)
        if shake>.015:
            self.camera.setPos(self.camera.getPos()+Vec3(
                self.random.uniform(-shake,shake),self.random.uniform(-shake,shake),
                self.random.uniform(-shake,shake)))
        self.camera_shake=max(0.,self.camera_shake-dt*8.)
        self.damage_flash=max(0.,self.damage_flash-dt*.85)
        self.hud.update_damage(self.damage_flash,self.game_time)
        self.camera.lookAt(look)
        self.camLens.setFov(78 if self.cam_mode!=1 else 85)

    def _menu_camera(self,dt):
        self.menu_angle+=dt*.17
        pos=self.jet.getPos()
        desired=pos+Vec3(math.sin(self.menu_angle)*45,
                         -math.cos(self.menu_angle)*60,19+math.sin(self.menu_angle*.7)*7)
        self.camera.setPos(self.camera.getPos()+(desired-self.camera.getPos())*
                           clamp(dt*2.7,0.,1.))
        self.camera.lookAt(pos+Vec3(0,2,1))
        self.audio.update(90,False,0,0,dt)

    def _update_waves(self,dt):
        if not self.enemies and not self.sites:
            self.wave_delay-=dt
            if self.wave_delay<=0:self._spawn_wave()

    def _update_enemies(self,dt):
        pos=self.jet.getPos()
        for enemy in list(self.enemies):
            enemy.age+=dt
            toward=pos-enemy.pos
            distance=toward.length()
            if distance>1950:
                self.enemies.remove(enemy);enemy.node.removeNode()
                self._check_wave_clear()
                continue
            spec=HOSTILES[enemy.kind]
            phase=enemy.phase+enemy.age*(.62 if enemy.kind=='ace' else .31)
            flank=Vec3(spec.ideal_distance*math.sin(phase),
                       spec.ideal_distance*math.cos(phase),
                       (58 if enemy.kind=='ace' else 24)*math.sin(phase*.8))
            if enemy.kind=='striker':flank.z+=60
            desired=pos+flank-enemy.pos
            # Missiles carriers back away at short range; interceptors press in.
            if distance<spec.ideal_distance*.68 and enemy.kind in ('striker','ace'):
                desired=enemy.pos-pos+Vec3(0,0,24)
            if desired.lengthSquared()>.0001:
                desired.normalize()
                desired*=min(spec.cruise_speed+self.wave*3.1,183.)
                # Heavy striker turns slower, the ace changes course aggressively.
                agility=1.55 if enemy.kind=='ace' else (.58 if enemy.kind=='striker' else 1.1)
                enemy.velocity+=(desired-enemy.velocity)*clamp(dt*agility,0,1)
            if enemy.evasion>0:
                enemy.evasion=max(0.,enemy.evasion-dt)
                enemy.velocity+=Vec3(math.sin(phase*6)*16,
                                    math.cos(phase*7)*16,
                                    math.sin(phase*4)*10)*dt
            enemy.pos+=enemy.velocity*dt
            bottom=max(0,self.world.height(enemy.pos.x,enemy.pos.y))+31
            if enemy.pos.z<bottom:
                enemy.pos.z=bottom
                enemy.velocity.z=max(0,enemy.velocity.z)
            enemy.node.setPos(enemy.pos)
            if enemy.velocity.lengthSquared()>.0001:
                enemy.node.lookAt(enemy.pos+enemy.velocity)
                enemy.node.setR(math.sin(enemy.age*2.3+enemy.phase)*
                                (33 if enemy.kind=='ace' else 19))
            enemy.fire_timer-=dt
            if enemy.fire_timer<=0 and distance<820:
                enemy.fire_timer=self.random.uniform(spec.fire_min,spec.fire_max)*(
                    1.-min(.24,self.wave*.025))
                if spec.missile and distance>145 and (
                    enemy.kind=='striker' or self.random.random()<.55):
                    start=enemy.pos+enemy.node.getQuat(self.render).getForward()*5
                    direction=(pos+Vec3(0,0,-2)-start)
                    if direction.lengthSquared()>.001:
                        self._fire_hostile_missile(start,direction.normalized()*200,'AIR')
                elif 60<distance<520:
                    self._enemy_shoot(enemy,pos)
            if distance<14 and self.damage_cooldown<=0:
                relative=(enemy.velocity-
                          self.jet.getQuat(self.render).getForward()*self.speed).length()
                impact=collision_damage(relative)
                self._destroy_enemy(enemy)
                if impact>=70:
                    self._start_crash('MID-AIR COLLISION',self.jet.getPos())
                else:
                    self._take_damage(impact,'MID-AIR COLLISION')

    def _update_sites(self,dt):
        for site in list(self.sites):
            delta=self.jet.getPos()-site.pos
            distance=delta.length()
            if distance>1950:
                site.node.removeNode();self.sites.remove(site)
                self._check_wave_clear()
                continue
            # The radar/launcher array follows the aircraft's bearing.
            site.node.setH(math.degrees(math.atan2(delta.x,delta.y)))
            site.fire_timer-=dt
            if 230<distance<1000 and site.fire_timer<=0:
                site.fire_timer=self.random.uniform(3.2,5.4)
                origin=site.pos+Vec3(0,0,5.8)
                direction=(self.jet.getPos()-origin)
                if direction.lengthSquared()>.001:
                    self._fire_hostile_missile(origin,direction.normalized()*180,'SAM')

    def _enemy_shoot(self,enemy,player_pos):
        start=enemy.pos+enemy.node.getQuat(self.render).getForward()*3.
        relative=player_pos-start
        player_velocity=self.jet.getQuat(self.render).getForward()*self.speed
        seconds=aim_lead((relative.x,relative.y,relative.z),
                         (player_velocity.x,player_velocity.y,player_velocity.z),255.)
        if seconds is not None:
            relative+=player_velocity*min(seconds,.9)
        spread=5.5 if enemy.kind=='scout' else 2.1 if enemy.kind=='ace' else 3.7
        relative+=Vec3(self.random.uniform(-spread,spread),
                       self.random.uniform(-spread,spread),
                       self.random.uniform(-spread,spread))
        heading=relative.normalized()
        node=self.laser_prototype.copyTo(self.render)
        node.setPos(start);node.lookAt(start+heading)
        dmg=15. if enemy.kind=='ace' else 11.
        self.projectiles.append(Projectile(node,Vec3(start),heading*255,0.,3.0,
                                           'enemy',None,dmg))


    def _update_projectiles(self,dt):
        for shot in list(self.projectiles):
            old=Vec3(shot.pos)
            shot.age+=dt
            decoy=None
            if shot.kind=='enemy_missile':
                closest=240.*240.
                for flare in self.flares:
                    d=(flare.pos-shot.pos).lengthSquared()
                    if d<closest:
                        decoy=flare;closest=d
                destination=(decoy.pos if decoy is not None else
                             self.jet.getPos()+Vec3(0,0,1))
                delta=destination-shot.pos
                if delta.lengthSquared()>.01:
                    target_velocity=delta.normalized()*280
                    shot.vel+=(target_velocity-shot.vel)*clamp(
                        dt*missile_turn_rate('enemy_missile',shot.age),0,1)
            elif shot.kind=='missile' and shot.target in self.enemies+self.sites:
                target_pos=shot.target.pos
                if isinstance(shot.target,GroundSite):target_pos=target_pos+Vec3(0,0,4)
                delta=target_pos-shot.pos
                if delta.lengthSquared()>.02:
                    desired=delta.normalized()*370
                    shot.vel+=(desired-shot.vel)*clamp(
                        dt*missile_turn_rate('missile',shot.age),0,1)
            shot.pos+=shot.vel*dt
            shot.node.setPos(shot.pos)
            if shot.vel.lengthSquared()>.001:shot.node.lookAt(shot.pos+shot.vel)
            hit=False
            if shot.kind in ('enemy','enemy_missile'):
                if decoy is not None and shot.kind=='enemy_missile':
                    if segment_dist_sq(old,shot.pos,decoy.pos)<65.:
                        self._explode(decoy.pos,.65)
                        decoy.node.removeNode()
                        if decoy in self.flares:self.flares.remove(decoy)
                        self.audio.play('flare',.36,.8)
                        self.hud.notify('MISSILE DECOYED',1.1,CYAN)
                        hit=True
                if not hit and segment_dist_sq(old,shot.pos,self.jet.getPos()) < (
                    102. if shot.kind=='enemy_missile' else 62.):
                    self._take_damage(shot.damage,
                                      'MISSILE HIT' if shot.kind=='enemy_missile'
                                      else 'INCOMING FIRE')
                    self._flash(shot.pos,(1.,.4,.27,1),1.4)
                    if shot.kind=='enemy_missile':self._explode(shot.pos,1.2)
                    hit=True
            else:
                for enemy in list(self.enemies):
                    radius=HOSTILES[enemy.kind].radius_sq
                    if segment_dist_sq(old,shot.pos,enemy.pos)<(
                        radius*1.65 if shot.kind=='missile' else radius):
                        enemy.hp-=shot.damage
                        if enemy.hp<=0:
                            if shot.kind=='missile':self.missile_kills+=1
                            self._destroy_enemy(enemy)
                        else:
                            if enemy.kind in ('interceptor','ace'):
                                enemy.evasion=self.random.uniform(.55,1.5)
                            self._combat_hit(shot.damage,shot.kind)
                            self._flash(shot.pos,(1.,.68,.42,1),.9)
                        if shot.kind=='missile':self._explode(shot.pos,1.15)
                        hit=True;break
                if not hit:
                    for site in list(self.sites):
                        centre=site.pos+Vec3(0,0,3.6)
                        if segment_dist_sq(old,shot.pos,centre) < (
                            210. if shot.kind=='missile' else 78.):
                            site.hp-=shot.damage
                            if site.hp<=0:
                                self._destroy_site(site)
                            else:
                                self._combat_hit(shot.damage,shot.kind)
                                self._flash(shot.pos,(1.,.72,.40,1),1.)
                            if shot.kind=='missile':self._explode(shot.pos,1.45)
                            hit=True;break
            if shot.kind in ('missile','enemy_missile') and not hit:
                shot.smoke_timer+=dt
                if shot.smoke_timer>.065:
                    shot.smoke_timer=0.
                    node=(self.blue_blast if shot.kind=='missile' else
                          self.red_blast).copyTo(self.render)
                    node.setPos(old);node.setScale(.34)
                    self.particles.append(Particle(node,Vec3(old),Vec3(0,0,-.8),
                                                   .35,.35,.34))
            ground=max(0,self.world.height(shot.pos.x,shot.pos.y))
            if not hit and shot.pos.z<ground+1:
                if shot.kind in ('missile','enemy_missile'):
                    self._explode(shot.pos,1.15)
                    if shot.kind=='missile':
                        # Ground-impact blast can still disable a nearby SAM.
                        for site in list(self.sites):
                            if (site.pos-shot.pos).lengthSquared()<1600:
                                site.hp-=shot.damage*.58
                                if site.hp<=0:self._destroy_site(site)
                hit=True
            if shot.age>shot.ttl or hit:
                if shot.kind=='missile' and not hit:self._explode(shot.pos,.85)
                if shot in self.projectiles:self.projectiles.remove(shot)
                shot.node.removeNode()


    def _update_particles(self,dt):
        for p in list(self.particles):
            p.life-=dt
            if p.life<=0:
                self.particles.remove(p)
                p.node.removeNode()
                continue
            p.vel*=max(.0,1-dt*.9)
            p.pos+=p.vel*dt
            p.node.setPos(p.pos)
            f=clamp(p.life/p.ttl,0.,1.)
            if p.kind=='smoke':
                p.node.setScale(p.initial_scale*(1+.9*(1-f)))
            elif p.kind=='splash':
                p.node.setScale(p.initial_scale*(1.+2.0*(1-f)))
            elif p.kind=='flame':
                p.node.setScale(max(.03,p.initial_scale*f))
            elif p.initial_scale>1.4:
                p.node.setScale(p.initial_scale*(1.5-.72*f))
            else:
                p.node.setScale(max(.01,p.initial_scale*f))
            if p.fades:p.node.setColorScale(1,1,1,f)

    def _update_contrails(self,dt):
        self.contrail_clock+=dt
        if self.contrail_clock<.075:return
        self.contrail_clock=0.
        q=self.jet.getQuat(self.render)
        for i,x in enumerate((-8.1,8.1)):
            pos=self.jet.getPos()+q.xform(Vec3(x,-3.5,-.17))
            self.contrails[i].insert(0,Vec3(pos))
            del self.contrails[i][48:]
        self.contrail_path.node().removeAllChildren()
        lines=LineSegs('contrails')
        lines.setThickness(1.25)
        for track in self.contrails:
            for i in range(len(track)-1):
                q=1-i/max(1,len(track))
                lines.setColor(Vec4(.68,.88,.9,.58*q) if self.boosting else
                               Vec4(.63,.74,.78,.16*q))
                lines.moveTo(track[i]);lines.drawTo(track[i+1])
        self.contrail_path.attachNewNode(lines.create())

    def userExit(self):
        self._save_highscore()
        self.audio.shutdown()
        super().userExit()
