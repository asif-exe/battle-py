"""Movement-linked turbine, wind, and original BATTLE-PY combat/crash audio."""
from __future__ import annotations

from pathlib import Path
import math
from panda3d.core import AudioSound

ROOT=Path(__file__).resolve().parent.parent


class Soundscape:
    """Best-effort audio: losing an output device must never terminate gameplay."""
    LOOPED=('engine','wind','boost','fire')
    EFFECTS=('roll','cannon','missile','explosion','damage','lock','warning',
             'ui','victory','crash','splash','eject','alarm',
             'flare','incoming','hit','boss','combo')

    def __init__(self,app):
        self.app=app
        self.enabled=True
        self.crash_mode=False
        self.sfx={}
        self.pools={}
        self.pool_index={}
        for key in self.LOOPED+self.EFFECTS:
            self.sfx[key]=self._load(key)
        for key in self.LOOPED:
            self._invoke(self.sfx[key], 'setLoop',True)
            self._invoke(self.sfx[key], 'setVolume',0)
            self._invoke(self.sfx[key], 'play')
        for key in ('cannon','missile','explosion','damage','lock','roll','crash','splash','hit','flare','incoming'):
            self.pools[key]=[self.sfx[key]]+[self._load(key) for _ in range(2)]
            self.pools[key]=[s for s in self.pools[key] if s is not None]
            self.pool_index[key]=0
        self._warning_cooldown=0.

    def _load(self,key):
        try:
            sound=self.app.loader.loadSfx(str(ROOT/'assets/audio'/f'{key}.wav'))
            return sound if sound and sound.status()!=AudioSound.BAD else None
        except Exception:
            return None

    @staticmethod
    def _invoke(sound,method,*args):
        if sound is not None:
            try:
                getattr(sound,method)(*args)
                return True
            except Exception:
                # Drivers can disappear or refuse play-rate changes mid-session.
                return False
        return False

    def play(self,name,volume=1.,rate=1.):
        if not self.enabled:return
        pool=self.pools.get(name)
        if pool:
            idx=self.pool_index[name]%len(pool)
            self.pool_index[name]+=1
            sound=pool[idx]
        else:
            sound=self.sfx.get(name)
        if sound is None:return
        self._invoke(sound,'stop')
        self._invoke(sound,'setVolume',max(0.,min(1.,volume)))
        self._invoke(sound,'setPlayRate',max(.2,rate))
        self._invoke(sound,'play')

    def update(self,speed,is_boosting,roll_amount,near_surface,dt,damage=0.):
        q=max(0.,min(1.,speed/305.))
        live=self.enabled and not self.crash_mode
        engine=self.sfx.get('engine')
        self._invoke(engine,'setPlayRate',(.68+q*.82)*
                     (1-.045*damage*abs(math.sin(self.app.game_time*14))))
        self._invoke(engine,'setVolume',(.25+.41*q) if live else 0.)
        wind=self.sfx.get('wind')
        self._invoke(wind,'setPlayRate',.72+q*.87)
        self._invoke(wind,'setVolume',(.04+.31*q+.08*near_surface+
                     (.09 if roll_amount else 0.)) if live else 0.)
        boost=self.sfx.get('boost')
        self._invoke(boost,'setPlayRate',.88+q*.42)
        self._invoke(boost,'setVolume',.51 if live and is_boosting else 0.)
        self._invoke(self.sfx.get('fire'),'setVolume',.22 if self.enabled and self.crash_mode else 0.)
        self._warning_cooldown=max(0.,self._warning_cooldown-dt)
        if live and near_surface>.7 and self._warning_cooldown<=0:
            self.play('warning',.36)
            self._warning_cooldown=2.5

    def enter_crash(self,water=False):
        self.crash_mode=True
        for key in ('engine','wind','boost'):
            self._invoke(self.sfx.get(key),'setVolume',0)
        self.play('splash' if water else 'crash',.94)
        self.play('explosion',.82,.78 if not water else .93)
        if not water:self._invoke(self.sfx.get('fire'),'setVolume',.22 if self.enabled else 0.)

    def reset(self):
        self.crash_mode=False
        self._warning_cooldown=0.
        self._invoke(self.sfx.get('fire'),'setVolume',0.)
        for key in self.LOOPED:
            sound=self.sfx.get(key)
            # Restart loop in case the user's sound driver went away and returned.
            self._invoke(sound,'play')

    def toggle(self):
        self.enabled=not self.enabled
        if not self.enabled:
            for key in self.LOOPED:self._invoke(self.sfx.get(key),'setVolume',0)
        return self.enabled

    def shutdown(self):
        for sound in list(self.sfx.values()):self._invoke(sound,'stop')
        for sounds in self.pools.values():
            for sound in sounds:self._invoke(sound,'stop')
