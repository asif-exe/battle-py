"""Generate original combat SFX using only Python's standard library.

Run: python tools/build_combat_audio.py
No licensed samples, downloaded audio, or synthesis dependency is required.
"""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
import wave

OUTPUT = Path(__file__).resolve().parents[1] / 'assets' / 'audio'
SAMPLE_RATE = 22050


def envelope(t, duration, attack=.008, decay=.24):
    return min(1., t/max(attack,1e-4)) * max(0., 1.-t/duration)**decay


def write(name, seconds, generate, volume=.82):
    randomizer=random.Random(sum(map(ord,name)) * 1471)
    stream=array('h')
    for i in range(int(seconds*SAMPLE_RATE)):
        t=i/SAMPLE_RATE
        n=randomizer.uniform(-1,1)
        v=generate(t, n, seconds)
        s=int(max(-1.,min(1.,v*volume))*32767)
        stream.append(s)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with wave.open(str(OUTPUT/f'{name}.wav'),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(SAMPLE_RATE)
        f.writeframes(stream.tobytes())


def flare(t,n,T):
    hiss=n*math.exp(-t*9)*.55
    sweep=math.sin(2*math.pi*(1600*t-670*t*t))*math.exp(-t*7)*.35
    sparkle=math.sin(2*math.pi*(2700*t+300*t*t))*math.exp(-t*10)*.25
    return (hiss+sweep+sparkle)*envelope(t,T,.002,.6)


def incoming(t,n,T):
    mod=1. if int(t*7)%2==0 else .30
    phase=2*math.pi*(620*t+180*t*t)
    return (math.sin(phase)*.62+math.sin(phase*.5)*.23+n*.055)*mod*envelope(t,T,.018,.30)


def hit(t,n,T):
    bang=(n*.48+math.sin(2*math.pi*(430*t-180*t*t))*.65)*math.exp(-t*30)
    tail=math.sin(2*math.pi*1200*t)*math.exp(-t*32)*.15
    return (bang+tail)*envelope(t,T,.001,1)


def boss(t,n,T):
    note=math.sin(2*math.pi*(92*t+16*t*t))
    harmonics=.53*math.sin(2*math.pi*(140*t+5*t*t))
    undertone=.2*math.sin(2*math.pi*53*t)
    brass=(note+harmonics+undertone)*(1.-.12*math.sin(t*28))
    return (brass*.6+n*.055)*envelope(t,T,.13,.9)


def combo(t,n,T):
    notes=(660,880,1174,1568)
    v=0.
    for j,frequency in enumerate(notes):
        local=t-j*.105
        if local>=0:
            v+=math.sin(2*math.pi*frequency*local)*math.exp(-local*16)*.63
            v+=math.sin(2*math.pi*frequency*2.01*local)*math.exp(-local*21)*.16
    return v*envelope(t,T,.006,.18)


if __name__=='__main__':
    for name,seconds,fn in [
        ('flare',.46,flare),('incoming',1.08,incoming),('hit',.22,hit),
        ('boss',1.73,boss),('combo',.76,combo)
    ]:
        write(name,seconds,fn)
        print(f'Created {name}.wav')
