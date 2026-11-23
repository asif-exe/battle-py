"""Regenerate the shipped original art and synthesised audio.

Build-time requirements: numpy, pillow. Runtime game needs only Panda3D.
This script is deterministic. No downloaded sounds, music or art are used.
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
AUD=ROOT/'assets/audio'
TEX=ROOT/'assets/textures'
AUD.mkdir(parents=True,exist_ok=True)
TEX.mkdir(parents=True,exist_ok=True)
RNG=np.random.default_rng(97021)
SR=22050


def env(t,attack=.005,decay=.20):
    return (1.-np.exp(-t/max(attack,.0001)))*np.exp(-t/max(decay,.0001))


def sweep_noise(t,amount=1):
    w=RNG.standard_normal(len(t)).astype('float64')
    # Warm noise filtered by a modest one-pole average.
    w=np.convolve(w,np.ones(7)/7,mode='same')
    return w*amount


def write(name, x, loop=False):
    arr=np.asarray(x,dtype=np.float64)
    if loop:
        # Wrap a tapered head over the tail for click-free seamless PCM playback.
        n=min(int(.15*SR),len(arr)//8)
        w=np.linspace(0,1,n)
        head=arr[:n].copy();tail=arr[-n:].copy()
        arr[:n]=head*w+tail*(1-w)
        arr[-n:]=head*w+tail*(1-w)
        arr-=np.mean(arr)
    peak=max(float(np.max(np.abs(arr))),.001)
    arr=np.clip(arr*(.88/max(peak,.88)),-.98,.98)
    with wave.open(str(AUD/f'{name}.wav'),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(SR)
        f.writeframes((arr*32767.).astype('<i2').tobytes())
    print(name, len(arr)/SR)


def time(length):
    return np.arange(int(length*SR),dtype=np.float64)/SR

# Turbine drone: continuous nested frequencies and light subharmonic rumble.
t=time(2.)
engine=(.32*np.sin(math.tau*58*t)+.23*np.sin(math.tau*116*t)+
        .12*np.sin(math.tau*233*t)+.15*np.sin(math.tau*35*t)+
        .11*np.sin(math.tau*350*t)+sweep_noise(t,.42))
engine*=.82+.08*np.sin(math.tau*4*t)
write('engine',engine,True)

# Air rush becomes louder (Panda AudioSound volume) and higher pitched with velocity.
t=time(2.)
wind=(sweep_noise(t,.72)+.20*np.sin(math.tau*390*t)+.16*np.sin(math.tau*820*t))
wind*=.75+.14*np.sin(math.tau*3*t)
write('wind',wind,True)

# High pressure afterburner howl, with sawtooth-ish harmonic stacks.
t=time(2.)
boost=sum((.30/i)*np.sin(math.tau*(92*i)*t+.28*i) for i in range(1,10))
boost+=.31*sweep_noise(t,.8)+.18*np.sin(math.tau*630*t)
write('boost',boost,True)

t=time(.93)
roll=(sweep_noise(t,.75)+.24*np.sin(math.tau*(180+550*t)*t))*env(t,.05,.55)
write('roll',roll)

t=time(.18)
cannon=(.72*sweep_noise(t,1)+.55*np.sin(math.tau*(110-65*t)*t)+
        .25*np.sin(math.tau*950*t))*env(t,.002,.045)
write('cannon',cannon)

t=time(1.28)
rocket=(.43*sweep_noise(t,.9)+.48*np.sin(math.tau*(85+330*t)*t)+
        .27*np.sin(math.tau*(280+780*t)*t))*env(t,.01,.34)
write('missile',rocket)

t=time(1.58)
explosion=(.68*sweep_noise(t,1.)+.45*np.sin(math.tau*(73-32*t)*t)+
           .32*np.sin(math.tau*(127-55*t)*t))*env(t,.003,.40)
explosion*=1+.21*np.sin(math.tau*16*t)
write('explosion',explosion)

t=time(.70)
damage=(.65*sweep_noise(t,.8)+.44*np.sin(math.tau*(176-90*t)*t))*env(t,.004,.23)
write('damage',damage)

t=time(.46)
lock=(.24*np.sin(math.tau*770*t)+.18*np.sin(math.tau*1170*t))*env(t,.009,.22)
write('lock',lock)

t=time(.45)
warning=(.33*np.sin(math.tau*430*t)+.13*np.sin(math.tau*860*t))
warning*=(np.sin(math.tau*3*t)>0).astype(float)*env(t,.004,1.)
write('warning',warning)

t=time(.20)
ui=(.23*np.sin(math.tau*(660+280*t)*t))*env(t,.005,.08)
write('ui',ui)

t=time(1.8)
victory=np.zeros_like(t)
for note,start,dur in ((392.,0.,.35),(523.,.32,.38),(659.,.67,.45),(784.,1.02,.7)):
    idx=(t>=start)&(t<start+dur)
    sub=t[idx]-start
    victory[idx]+=(.18*np.sin(math.tau*note*sub)+.08*np.sin(math.tau*note*2*sub))*env(sub,.02,.40)
write('victory',victory)

# Pencil-cloud artwork as a noisy accumulation of semi-transparent masses.
w,h=512,256
Y,X=np.mgrid[0:h,0:w]
alpha=np.zeros((h,w),dtype='float64')
rng=np.random.default_rng(222)
for _ in range(29):
    cx=rng.uniform(60,450);cy=rng.uniform(90,169)
    sx=rng.uniform(20,78);sy=rng.uniform(14,35)
    alpha+=rng.uniform(.08,.22)*np.exp(-(((X-cx)/sx)**2+((Y-cy)/sy)**2)*1.4)
alpha*=np.exp(-((X-w/2)/(w*.53))**6)*np.exp(-((Y-h/2)/(h*.47))**6)
alpha=np.clip((alpha-.055)*255,0,210).astype('uint8')
rgba=np.empty((h,w,4),dtype='uint8');rgba[:,:,0]=230;rgba[:,:,1]=235;rgba[:,:,2]=225
rgba[:,:,3]=alpha
Image.fromarray(rgba,'RGBA').filter(ImageFilter.GaussianBlur(2)).save(TEX/'cloud.png')

# Circular warm sky halo and a white-hot solar core; no third-party artwork.
w=h=256
Y,X=np.mgrid[0:h,0:w]
r=np.sqrt((X-127.5)**2+(Y-127.5)**2)/128.
core=np.exp(-(r/.13)**3.)
glow=np.exp(-(r/.48)**2.5)
a=np.clip((core*.94+glow*.28)*255,0,255)
arr=np.empty((h,w,4),dtype='uint8')
arr[:,:,0]=255;arr[:,:,1]=np.clip(177+80*core,0,255);arr[:,:,2]=np.clip(98+157*core,0,255);arr[:,:,3]=a.astype('uint8')
Image.fromarray(arr,'RGBA').save(TEX/'sun.png')

# Original game icon: razor-wing strike jet on a dark navy field.
im=Image.new('RGBA',(256,256),(10,26,35,255))
d=ImageDraw.Draw(im)
d.rounded_rectangle((7,7,249,249),radius=43,outline=(57,105,111),width=5)
d.polygon([(128,22),(147,97),(213,153),(215,177),(164,166),(150,189),
           (132,185),(128,232),(124,185),(106,189),(92,166),(41,177),
           (43,153),(109,97)],fill=(202,219,212),outline=(59,85,86))
d.polygon([(128,39),(139,108),(150,126),(128,118),(106,126),(117,108)],fill=(32,76,84))
d.polygon([(128,69),(137,112),(128,139),(119,112)],fill=(255,153,93))
d.polygon([(55,159),(100,145),(95,157),(51,172)],fill=(251,105,66))
d.polygon([(201,159),(156,145),(161,157),(205,172)],fill=(251,105,66))
im.save(TEX/'icon.png')
print('Art and sound assets built successfully.')
