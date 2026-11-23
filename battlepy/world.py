"""Streamed archipelago, sea shader, atmospheric sky, cloud layers and beacons."""
from __future__ import annotations

import math
import random
from pathlib import Path

from panda3d.core import (
    AmbientLight, CardMaker, DirectionalLight, Fog, NodePath, Shader,
    TransparencyAttrib, Vec3, Vec4,
)

from .geometry import MeshBuilder, create_marker
from .mathx import clamp, hash2, noise, terrain_height
from .settings import CHUNK_SIZE, GRID_CELLS, LOAD_RADIUS

ROOT = Path(__file__).resolve().parent.parent

WATER_VERTEX = '''#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
out vec2 v_world;
void main() {
    vec4 w = p3d_ModelMatrix * p3d_Vertex;
    v_world = w.xy;
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}
'''

WATER_FRAGMENT = '''#version 130
uniform float u_time;
in vec2 v_world;
out vec4 fragColor;
void main() {
    vec2 p = v_world;
    float w1 = sin(p.x*.056 + p.y*.013 + u_time*1.10);
    float w2 = sin(p.y*.079 - p.x*.026 - u_time*1.45);
    float w3 = sin((p.x+p.y)*.127 + u_time*.86);
    float texture = w1*.38+w2*.37+w3*.25;
    float broad = sin(p.y*.003 + p.x*.0015 + u_time*.17)*.5+.5;
    vec3 deep = vec3(.023,.107,.155);
    vec3 shallow = vec3(.070,.239,.286);
    vec3 base = mix(deep,shallow,clamp(.37+.36*broad+.12*texture,0.,1.));
    float crest = smoothstep(.62,.94,texture);
    vec3 shine = vec3(.45,.67,.66)*crest*.14;
    float streak = pow(max(0.,sin((p.x*.12-p.y*.065)+u_time*.9)),22.);
    shine += vec3(.91,.63,.39)*streak*.075;
    fragColor = vec4(base+shine,1.);
}
'''


def _color(h, x, y, slope):
    """Landscape palette: dusty beaches, sea-pine forests, stone and pale peaks."""
    detail = noise(x*.015, y*.015, 52)*.06
    warm = max(0., noise(x*.0012+18., y*.0012, 47))
    if h < 3:
        base = (.43,.47,.42)
    elif h < 13:
        base = (.55,.49,.37)
    elif h < 85:
        base = ((.18+.11*warm),(.30+.09*warm),(.265-.04*warm))
    elif h < 180:
        base = (.26+.12*warm,.36+.07*warm,.31-.02*warm)
    elif h < 290:
        base = (.38,.43,.43)
    else:
        base = (.64,.67,.65)
    if slope>.48 and h>35:
        mix=clamp((slope-.42)*1.35,0.,.82)
        rock=(.34+.10*warm,.39+.05*warm,.40)
        base=tuple(base[i]*(1-mix)+rock[i]*mix for i in range(3))
    if h>360:
        mix=clamp((h-360)/80.,0.,1.)
        base=tuple(base[i]*(1-mix)+.78*mix for i in range(3))
    return (*(clamp(c+detail,.04,.95) for c in base),1.)


class World:
    def __init__(self, app):
        self.app = app
        self.render = app.render
        self.root = self.render.attachNewNode('Archipelago')
        self.tiles = {}
        self.pending = []
        self.center = (None,None)
        self.clouds = []
        self.time = 0.
        self._make_lighting()
        self._make_sky()
        self._make_water()
        self._make_clouds()
        self.tower_master = create_marker()
        self.tower_master.setScale(.75)
        self.tower_master.setP(90)

    @staticmethod
    def height(x, y):
        return terrain_height(x,y)

    def _make_lighting(self):
        a = AmbientLight('twilight-ambient')
        a.setColor(Vec4(.51,.59,.63,1))
        self.render.setLight(self.render.attachNewNode(a))
        sun = DirectionalLight('low-afternoon-sun')
        sun.setColor(Vec4(1.12,.87,.65,1))
        light = self.render.attachNewNode(sun)
        light.setHpr(-54,-36,0)
        self.render.setLight(light)
        fog = Fog('coastal-haze')
        fog.setColor(.43,.52,.55)
        fog.setLinearRange(840,3600)
        self.render.setFog(fog)
        self.app.setBackgroundColor(.15,.25,.34,1)

    def _make_sky(self):
        m=MeshBuilder('AtmosphericSky')
        r=3300
        rings=[]
        # Complete sphere below the horizon avoids exposing a hard seam during dives.
        for j in range(22):
            lat=-math.pi/2 + math.pi*j/21
            pts=[]
            for i in range(48):
                lon=math.tau*i/48
                pts.append((r*math.cos(lat)*math.sin(lon),
                            r*math.cos(lat)*math.cos(lon),r*math.sin(lat)))
            rings.append(pts)
        for j in range(len(rings)-1):
            elev=math.sin(-math.pi/2 + math.pi*(j+.5)/21)
            if elev<-.10: color=(.29,.39,.44,1)
            elif elev<.02: color=(.70,.49,.37,1)
            elif elev<.17: color=(.44,.51,.54,1)
            elif elev<.55: color=(.18,.31,.43,1)
            else: color=(.067,.15,.25,1)
            for i in range(48):
                k=(i+1)%48
                m.polygon((rings[j][i],rings[j][k],rings[j+1][k],rings[j+1][i]),color)
        self.sky=m.create()
        self.sky.reparentTo(self.render)
        self.sky.setLightOff();self.sky.setFogOff()
        self.sky.setDepthTest(False);self.sky.setDepthWrite(False)
        self.sky.setBin('background',0)
        # Sun as a soft baked corona sprite, not a primitive sphere.
        cm=CardMaker('solar-disc'); cm.setFrame(-1,1,-1,1)
        self.sun=self.render.attachNewNode(cm.generate())
        self.sun.setTexture(self.app.loader.loadTexture(str(ROOT/'assets/textures/sun.png')))
        self.sun.setTransparency(TransparencyAttrib.MAlpha)
        self.sun.setDepthTest(False);self.sun.setDepthWrite(False)
        self.sun.setLightOff();self.sun.setFogOff()
        self.sun.setBillboardPointEye()
        self.sun.setBin('background',1)
        self.sun.setScale(120)
        self.sun_direction=Vec3(-.77,.45,.46).normalized()

    def _make_water(self):
        m=MeshBuilder('EndlessSea')
        size=4900
        m.polygon([(-size,-size,0),(size,-size,0),(size,size,0),(-size,size,0)],
                  (.04,.24,.31,1))
        self.water=m.create()
        self.water.reparentTo(self.render)
        self.water.setLightOff();self.water.setTwoSided(True)
        self.water.setShaderInput('u_time',0.)
        try:
            self.water.setShader(Shader.make(Shader.SL_GLSL,WATER_VERTEX,WATER_FRAGMENT))
        except Exception as exc:
            print('Water shader unavailable; using flat-water fallback:',exc)
        self.water.setBin('background',2)

    def _make_clouds(self):
        cm=CardMaker('volumetric-cloud-sprite')
        cm.setFrame(-1,1,-.40,.40)
        tex=self.app.loader.loadTexture(str(ROOT/'assets/textures/cloud.png'))
        rng=random.Random(92844)
        for i in range(58):
            cloud=self.render.attachNewNode(cm.generate())
            cloud.setTexture(tex)
            cloud.setTransparency(TransparencyAttrib.MAlpha)
            cloud.setDepthWrite(False)
            cloud.setLightOff();cloud.setFogOff()
            cloud.setBillboardPointEye()
            cloud.setScale(rng.uniform(52,140))
            cloud.setColor(1.,rng.uniform(.79,.97),rng.uniform(.74,.90),rng.uniform(.24,.57))
            cloud.setPos(rng.uniform(-1500,1500),rng.uniform(-1500,1500),rng.uniform(240,415))
            self.clouds.append(cloud)

    def _make_tile(self,cx,cy):
        size=CHUNK_SIZE
        cell=GRID_CELLS
        step=size/cell
        xbase=cx*size
        ybase=cy*size
        heights=[]
        for j in range(cell+1):
            heights.append([terrain_height(xbase+i*step,ybase+j*step) for i in range(cell+1)])
        mesh=MeshBuilder('terrain-%d-%d'%(cx,cy))
        for j in range(cell):
            for i in range(cell):
                h00=heights[j][i]; h10=heights[j][i+1]
                h01=heights[j+1][i]; h11=heights[j+1][i+1]
                x=i*step; y=j*step
                slope=max(abs(h10-h00),abs(h01-h00),abs(h11-h10),abs(h11-h01))/step
                avg=(h00+h10+h01+h11)*.25
                c=_color(avg,xbase+x,ybase+y,slope)
                a=(x,y,h00);b=(x+step,y,h10)
                d=(x,y+step,h01);e=(x+step,y+step,h11)
                # Two triangular facets with one shared shade per terrain cell.
                mesh.triangle(a,b,d,c)
                mesh.triangle(b,e,d,c)
        tile=mesh.create()
        tile.reparentTo(self.root)
        tile.setPos(xbase,ybase,0)
        tile.setTwoSided(True)
        # Sparse navigation towers are consistent across rebuilds and never random at runtime.
        h=hash2(cx,cy,2002)
        if h>.83:
            px=xbase+size*(.2+.6*hash2(cx,cy,982))
            py=ybase+size*(.2+.6*hash2(cx,cy,231))
            pz=terrain_height(px,py)
            if pz>45:
                tower=self.tower_master.copyTo(tile)
                tower.setPos(px-xbase,py-ybase,pz+6)
                tower.setColorScale(1.15,1.,.91,1.)
        return tile

    def update(self, pos: Vec3, dt: float):
        self.time+=dt
        ix=math.floor(pos.x/CHUNK_SIZE)
        iy=math.floor(pos.y/CHUNK_SIZE)
        if (ix,iy)!=self.center:
            self.center=(ix,iy)
            needs=set((ix+dx,iy+dy) for dx in range(-LOAD_RADIUS,LOAD_RADIUS+1)
                      for dy in range(-LOAD_RADIUS,LOAD_RADIUS+1))
            for key in list(self.tiles):
                if key not in needs:
                    self.tiles.pop(key).removeNode()
            self.pending=sorted(needs-set(self.tiles),
                                key=lambda k:(k[0]-ix)**2+(k[1]-iy)**2)
        # Two new tiles per frame; animation stays responsive on low-end PCs.
        for _ in range(min(2,len(self.pending))):
            key=self.pending.pop(0)
            if key not in self.tiles:
                self.tiles[key]=self._make_tile(*key)
        self.sky.setPos(pos)
        self.sun.setPos(pos+self.sun_direction*2200)
        self.water.setPos(pos.x,pos.y,0)
        self.water.setShaderInput('u_time',self.time)
        for i,cloud in enumerate(self.clouds):
            cloud.setX(cloud.getX()+dt*(3.5+i%4))
            delta=cloud.getPos()-pos
            if delta.x>1680: cloud.setX(cloud.getX()-3300)
            if delta.x< -1680: cloud.setX(cloud.getX()+3300)
            if delta.y>1680: cloud.setY(cloud.getY()-3300)
            if delta.y< -1680: cloud.setY(cloud.getY()+3300)
