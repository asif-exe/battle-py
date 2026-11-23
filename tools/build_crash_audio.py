"""Generate original BATTLE-PY rescue/impact/audio layers using Python stdlib only."""
from __future__ import annotations
import math
import random
import struct
import wave
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]/'assets'/'audio'
OUT.mkdir(parents=True,exist_ok=True)
RATE=22050


def write(name,seconds,fn):
    rng=random.Random(1017+len(name)*721)
    count=int(seconds*RATE)
    samples=[]
    last=0.
    for i in range(count):
        t=i/RATE
        noise=rng.uniform(-1,1)
        last=.92*last+.08*noise
        signal=fn(t,seconds,noise,last)
        # Hardware-friendly headroom and gentle clipping, no digital peaks.
        v=math.tanh(signal*1.16)*.76
        samples.append(int(max(-1,min(1,v))*32767))
    with wave.open(str(OUT/(name+'.wav')),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
        w.writeframes(struct.pack('<%dh'%len(samples),*samples))
    print(name, count)


def crash(t,T,n,l):
    env=min(1,t/.018)*math.exp(-t*1.25)
    sub=math.sin(2*math.pi*(96*t-24*t*t))*.6
    metal=math.sin(2*math.pi*(230*t-69*t*t))*.20
    rattle=n*.45*(.65+.35*math.sin(2*math.pi*17*t))
    return (sub+metal+rattle+l*.68)*env


def splash(t,T,n,l):
    swell=math.exp(-t*.9)*min(1,t*25)
    return (n*.55+l*.85+math.sin(2*math.pi*(53-14*t)*t)*.18)*swell


def fire(t,T,n,l):
    pop=(max(0.,math.sin(t*2*math.pi*8.1))**16)*n*.65
    return .16*n+.55*l+pop


def eject(t,T,n,l):
    env=math.exp(-t*2.8)*min(1,t*45)
    return (math.sin(2*math.pi*(170+600*t)*t)*.18+.42*n+.4*l)*env


def alarm(t,T,n,l):
    pulse=1 if (t%0.35)<.17 else 0.0
    env=min(1,t*25)*min(1,(T-t)*25)
    return pulse*env*(.30*math.sin(2*math.pi*760*t)+.16*math.sin(2*math.pi*380*t))


if __name__=='__main__':
    write('crash',2.8,crash)
    write('splash',1.8,splash)
    write('fire',1.4,fire)
    write('eject',1.05,eject)
    write('alarm',1.2,alarm)
