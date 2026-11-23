"""Hand-designed low-poly Wraith airframe and world props: no stock models."""
from __future__ import annotations

import math

from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, NodePath, Vec3, Vec4, TransparencyAttrib, LineSegs,
)

METAL = (0.17, 0.24, 0.28, 1)
METAL_DARK = (0.072, 0.112, 0.137, 1)
METAL_TOP = (0.31, 0.40, 0.43, 1)
STEEL = (0.41, 0.51, 0.53, 1)
PANEL = (0.10, 0.18, 0.21, 1)
CANOPY = (0.05, 0.29, 0.36, 1)
GLASS_LIGHT = (0.25, 0.65, 0.69, 1)
SIGNAL = (0.98, 0.38, 0.24, 1)
GOLD = (0.99, 0.70, 0.40, 1)


class MeshBuilder:
    def __init__(self, name='mesh'):
        self.name = name
        self.vertices = []
        self.normals = []
        self.colors = []
        self.indices = []

    def triangle(self, a, b, c, color):
        a, b, c = Vec3(*a), Vec3(*b), Vec3(*c)
        n = (b-a).cross(c-a)
        if n.lengthSquared() < 0.000001:
            return
        n.normalize()
        i = len(self.vertices)
        for p in (a,b,c):
            self.vertices.append(p)
            self.normals.append(n)
            self.colors.append(color)
        self.indices.extend((i, i+1, i+2))

    def polygon(self, pts, color):
        for i in range(1, len(pts)-1):
            self.triangle(pts[0],pts[i],pts[i+1],color)

    def slab(self, pts, thick, top, bottom=None, sides=None):
        bottom = bottom or METAL_DARK
        sides = sides or METAL
        u = [(x,y,z+thick*.5) for x,y,z in pts]
        d = [(x,y,z-thick*.5) for x,y,z in pts]
        self.polygon(u,top)
        self.polygon(list(reversed(d)),bottom)
        for i in range(len(pts)):
            j=(i+1)%len(pts)
            self.polygon((u[i],u[j],d[j],d[i]),sides)

    def tube(self, x, y1, y2, z, rx, rz, color, sides=12):
        rings=[]
        for y in (y1,y2):
            rings.append([(x+rx*math.cos(i*math.tau/sides), y,
                           z+rz*math.sin(i*math.tau/sides)) for i in range(sides)])
        for i in range(sides):
            j=(i+1)%sides
            shade = (0.75 + .23*max(0, math.sin(i*math.tau/sides)))
            c=tuple(v*shade for v in color[:3])+(color[3],)
            self.polygon((rings[0][i],rings[0][j],rings[1][j],rings[1][i]),c)
        return rings

    def cone(self, x, ybase, ytip, z, rx, rz, color, sides=12):
        p=(x,ytip,z)
        for i in range(sides):
            a=i*math.tau/sides
            b=(i+1)*math.tau/sides
            self.triangle(p,(x+rx*math.cos(a),ybase,z+rz*math.sin(a)),
                          (x+rx*math.cos(b),ybase,z+rz*math.sin(b)), color)

    def sphere(self, center, radius, color, slices=10, rings=6):
        cx,cy,cz=center
        for j in range(rings):
            a=-math.pi/2+j*math.pi/rings
            b=-math.pi/2+(j+1)*math.pi/rings
            for i in range(slices):
                c=i*math.tau/slices
                d=(i+1)*math.tau/slices
                def p(lat,lon):
                    return (cx+radius*math.cos(lat)*math.cos(lon),
                            cy+radius*math.cos(lat)*math.sin(lon),
                            cz+radius*math.sin(lat))
                self.triangle(p(a,c),p(a,d),p(b,d),color)
                self.triangle(p(a,c),p(b,d),p(b,c),color)

    def create(self):
        data=GeomVertexData(self.name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
        data.setNumRows(len(self.vertices))
        pw=GeomVertexWriter(data,'vertex')
        nw=GeomVertexWriter(data,'normal')
        cw=GeomVertexWriter(data,'color')
        for v,n,c in zip(self.vertices,self.normals,self.colors):
            pw.addData3f(v)
            nw.addData3f(n)
            cw.addData4f(*c)
        prim=GeomTriangles(Geom.UHStatic)
        for i in range(0,len(self.indices),3):
            prim.addVertices(*self.indices[i:i+3])
        prim.closePrimitive()
        geom=Geom(data); geom.addPrimitive(prim)
        node=GeomNode(self.name); node.addGeom(geom)
        path=NodePath(node)
        path.setTwoSided(True)
        return path


def create_jet():
    """AX-9 Wraith: faceted nose, cranked delta wings, twin ventral nacelles."""
    m=MeshBuilder('AX9-Wraith')
    sections=[
        (13.7,.04,.04), (11.4,.27,.19), (9.4,.62,.36),
        (7.2,.96,.49), (4.8,1.33,.65), (1.0,1.51,.74),
        (-3.0,1.53,.73), (-7.3,1.45,.65),(-10.1,.92,.42),
    ]
    rings=[]
    for y,w,h in sections:
        rings.append([
            (0,y,h*.95),(w*.53,y,h*.84),(w*.91,y,h*.36),
            (w,y,-.13),(w*.66,y,-h*.72),(0,y,-h),
            (-w*.66,y,-h*.72),(-w,y,-.13),(-w*.91,y,h*.36),
            (-w*.53,y,h*.84)
        ])
    for j in range(len(rings)-1):
        for k in range(10):
            n=(k+1)%10
            c = (METAL_TOP if k in (0,9) else
                 STEEL if k in (1,8) else
                 METAL if k in (2,7) else METAL_DARK)
            if j==0: c=METAL_DARK
            m.polygon((rings[j][k],rings[j][n],rings[j+1][n],rings[j+1][k]),c)
    m.polygon([(-.17,12.88,.07),(.17,12.88,.07),(.26,11.57,.19),(-.26,11.57,.19)],SIGNAL)
    # Armoured bubble canopy. Front diamond and longitudinal glass facets.
    m.polygon([(0,8.95,.53),(.64,7.45,.66),(.76,5.8,1.14),
               (0,5.52,1.48),(-.76,5.8,1.14),(-.64,7.45,.66)],CANOPY)
    m.polygon([(0,8.87,.55),(.52,7.34,.80),(.64,6.07,1.18),(0,5.58,1.52)],GLASS_LIGHT)
    m.polygon([(0,8.87,.55),(0,5.58,1.52),(-.64,6.07,1.18),(-.52,7.34,.80)],CANOPY)
    m.polygon([(-.078,5.57,1.57),(.078,5.57,1.57),(.12,4.15,1.10),(-.12,4.15,1.10)],STEEL)
    m.polygon([(-.61,5.81,1.1),(-.52,5.82,1.19),(-.51,5.93,1.2),(-.63,5.94,1.1)],GOLD)
    for s in (-1,1):
        def P(x,y,z): return (s*x,y,z)
        # Blended fuselage shoulders and deep air intakes.
        m.polygon([P(.86,6.32,.45),P(2.25,3.23,.12),P(2.20,-3.6,.36),P(1.2,-5.6,.68)],METAL_TOP)
        m.polygon([P(1.37,3.52,-.06),P(2.52,3.0,-.11),P(2.52,1.13,-.48),P(1.38,1.33,-.51)],METAL_DARK)
        m.polygon([P(1.52,3.34,-.01),P(2.47,2.84,-.03),P(2.40,2.60,-.02),P(1.51,3.1,.03)],GOLD)
        # Clipped and cranked diamond delta wing, thick enough to catch light.
        pts=[P(1.24,4.45,-.13),P(3.38,2.74,-.13),P(9.10,-2.15,-.13),
             P(9.22,-4.01,-.13),P(7.48,-4.76,-.13),P(6.72,-5.97,-.13),
             P(5.0,-6.42,-.13),P(1.26,-8.57,-.13)]
        m.slab(pts,.25,METAL_TOP,METAL_DARK,METAL)
        m.polygon([P(1.80,3.60,.015),P(3.53,2.23,.015),P(7.94,-2.17,.015),
                   P(6.03,-4.83,.015),P(2.15,-3.88,.015)],PANEL)
        m.polygon([P(2.26,-3.96,.027),P(6.02,-5.02,.027),P(6.71,-5.61,.027),
                   P(4.87,-6.24,.027),P(1.98,-7.27,.027)],METAL_DARK)
        m.polygon([P(7.52,-2.34,.041),P(8.85,-2.61,.041),
                   P(8.90,-3.44,.041),P(7.79,-3.64,.041)],SIGNAL)
        m.polygon([P(4.5,-4.9,.045),P(5.18,-5.10,.045),P(4.8,-5.37,.045)],GOLD)
        # Forward canards.
        m.slab([P(.92,7.24,.12),P(2.91,5.65,.12),P(3.56,4.78,.12),P(1.19,5.29,.12)],
               .13,STEEL,METAL_DARK,METAL)
        # Horizontal stabilizers.
        m.slab([P(1.25,-6.94,-.36),P(4.56,-9.06,-.36),P(5.04,-10.27,-.36),
                P(3.37,-10.67,-.36),P(1.13,-9.8,-.36)],.14,STEEL,METAL_DARK)
        # Large canted twin tail fins; markings and split metallic plating.
        m.polygon([P(1.06,-6.52,.50),P(2.12,-7.55,2.02),P(3.19,-9.22,3.75),
                   P(2.88,-10.45,3.58),P(1.08,-10.34,.49)],METAL_TOP)
        m.polygon([P(1.30,-7.07,.74),P(2.10,-8.21,2.18),P(2.84,-9.35,3.20),
                   P(1.88,-9.39,1.58)],PANEL)
        m.polygon([P(2.33,-8.83,2.28),P(2.77,-9.40,3.06),P(2.56,-9.61,2.78)],SIGNAL)
        # Engine nacelles, aft ring and internal afterburner opening.
        m.tube(s*1.13,-7.45,-10.2,-.22,.76,.69,METAL_DARK)
        m.tube(s*1.13,-10.1,-10.41,-.22,.69,.61,STEEL)
        m.tube(s*1.13,-10.40,-10.50,-.22,.47,.43,SIGNAL)
        m.cone(s*1.13,-10.48,-10.50,-.22,.43,.40,PANEL)
        m.polygon([P(.79,-6.23,.43),P(1.48,-6.23,.43),P(1.65,-8.52,.43),P(.67,-8.52,.43)],METAL_TOP)
        # Navigation lights.
        m.polygon([P(8.99,-3.23,-.005),P(9.12,-3.27,-.005),P(9.12,-3.57,-.005),P(8.99,-3.57,-.005)],
                  SIGNAL if s<0 else (0.24,.92,.71,1))
    model=m.create()
    root=NodePath('WRAITH-FIGHTER')
    model.reparentTo(root)
    root.setTwoSided(True)
    # The exhausts and attached rocket pods are independent, animated models.
    exhaust=[]
    for x in (-1.13,1.13):
        f=MeshBuilder('afterburner')
        f.cone(0,0,-3.1,0,.42,.39,(0.18,.80,1.,.75),12)
        f.cone(0,-.02,-2.05,0,.31,.28,(1.,.72,.35,.85),12)
        p=f.create(); p.reparentTo(root); p.setPos(x,-10.52,-.22)
        p.setLightOff(); p.setTransparency(TransparencyAttrib.MAlpha)
        p.setDepthWrite(False)
        exhaust.append(p)
    rack=[]
    for x,y in ((-5.6,-2.55),(5.6,-2.55),(-3.25,.10),(3.25,.10)):
        pod=create_missile();pod.reparentTo(root)
        pod.setPos(x,y,-.65)
        pod.setScale(.62)
        rack.append(pod)
    return root, exhaust, rack


def create_missile():
    m=MeshBuilder('Viper-Missile')
    m.cone(0,1.55,2.50,0,.21,.21,STEEL)
    m.tube(0,-1.33,1.55,0,.21,.21,(.75,.80,.76,1),10)
    m.cone(0,-1.29,-1.44,0,.21,.21,PANEL)
    for s in (-1,1):
        m.slab([(s*.11,-.50,0),(s*.78,-1.14,0),(s*.89,-1.45,0),(s*.11,-1.17,0)],
               .05,METAL_DARK)
        m.polygon([(s*.13,.95,.11),(s*.48,.52,.11),(s*.24,.48,.11)],SIGNAL)
    return m.create()


def create_drone():
    m=MeshBuilder('Talon-Drone')
    m.slab([(0,3.6,0),(-.87,.5,0),(-1.,-3.10,0),(0,-3.35,0),
            (1.,-3.10,0),(.87,.5,0)],.50,METAL_DARK)
    for s in (-1,1):
        def P(x,y,z): return (s*x,y,z)
        m.slab([P(.48,1.8,0),P(2.6,.3,0),P(5.10,-1.30,0),
                P(4.94,-2.18,0),P(2.72,-2.80,0),P(.66,-2.35,0)],
               .18,METAL_TOP,METAL_DARK,METAL)
        m.polygon([P(1.36,.86,.115),P(3.9,-1.3,.115),P(3.6,-1.82,.115),P(1.1,-1.44,.115)],PANEL)
        m.polygon([P(3.90,-1.55,.129),P(4.63,-1.67,.129),P(4.55,-1.99,.129)],SIGNAL)
        m.polygon([P(.8,-1.24,.18),P(1.35,-2.55,1.46),P(1.16,-3.07,1.34),P(.62,-2.45,.10)],METAL_TOP)
    m.polygon([(0,2.72,.28),(.46,1.0,.39),(0,.31,.76),(-.46,1.,.39)],SIGNAL)
    m.tube(0,-2.8,-3.3,-.12,.43,.35,PANEL)
    m.cone(0,-3.33,-4.0,-.12,.33,.25,(1.,.42,.19,1))
    return m.create()



def create_hostile_fighter(kind):
    """Distinct original silhouettes for the enemy classes; +Y is forward."""
    if kind == 'scout':
        return create_drone()
    m = MeshBuilder('hostile-' + kind)
    is_ace = kind == 'ace'
    is_striker = kind == 'striker'
    base = (0.26,.30,.31,1) if is_striker else (0.13,.15,.21,1)
    plate = (.42,.49,.46,1) if is_striker else (.29,.36,.42,1)
    red = (1.,.16,.12,1) if is_ace else (.97,.39,.24,1)
    span = 7.0 if is_striker else (6.5 if is_ace else 5.6)
    nose = 6.6 if is_ace else (5.6 if is_striker else 5.2)
    aft = -5.5 if is_striker else -4.4
    m.slab([(0,nose,0),(.85,3.1,0),(1.15,-2.3,0),(.75,aft,0),
            (-.75,aft,0),(-1.15,-2.3,0),(-.85,3.1,0)],.72,base,METAL_DARK)
    for side in (-1,1):
        def P(x,y,z):return (side*x,y,z)
        if is_striker:
            points=[P(.8,2.2,0),P(3.1,1.2,0),P(span,-.9,0),P(span,-2.85,0),
                    P(5.5,-3.55,0),P(1.0,-3.9,0)]
        else:
            points=[P(.74,2.45,0),P(2.0,1.8,0),P(span,-2.85,0),
                    P(span-.9,-3.48,0),P(4.2,-3.6,0),P(1.03,-4.0,0)]
        m.slab(points,.24,plate,base)
        m.polygon([P(1.5,.84,.17),P(2.7,-.33,.17),P(span-1,-2.64,.17),
                   P(2.15,-2.40,.17)],METAL_DARK)
        m.polygon([P(span-.90,-2.49,.18),P(span-.40,-2.82,.18),
                   P(span-1.04,-3.12,.18)],red)
        # Double vertical rudders give a recognizably predatory silhouette.
        m.polygon([P(.75,-2.25,.36),P(1.30,-3.0,1.20),P(2.34,-4.25,2.6),
                   P(2.13,aft,2.5),P(.72,aft,.36)],base)
        m.polygon([P(1.41,-3.2,1.37),P(2.04,-4.1,2.27),
                   P(1.78,-4.20,2.03)],red)
        if is_striker:
            # Heavy external pods make the bomber immediately recognizable.
            m.tube(side*3.5,-3.0,.7,-.46,.35,.37,METAL_DARK,10)
            m.cone(side*3.5,.7,1.40,-.46,.30,.29,STEEL,10)
        if is_ace:
            m.slab([P(.95,4.2,.12),P(2.2,3.5,.12),P(2.6,2.9,.12),
                    P(.98,3.0,.12)],.10,red,base)
    m.polygon([(-.36,2.94,.39),(.36,2.94,.39),(.68,1.38,.82),
               (0,.87,1.00),(-.68,1.38,.82)],red)
    for x in (-.65,.65):
        m.tube(x,aft-.25,aft-.92,-.20,.31,.31,METAL_DARK,10)
        m.cone(x,aft-1.,aft-1.42,-.20,.20,.20,red,10)
    result=m.create()
    result.setTwoSided(True)
    return result


def create_sam_site():
    """Ground-based anti-aircraft missile emplacement with rotating radar fin."""
    m=MeshBuilder('VIGIL-SAM-battery')
    m.slab([(-6,-5,.50),(6,-5,.50),(7,4,.50),(-7,4,.50)],1.0,
           (.22,.28,.23,1),METAL_DARK)
    m.slab([(-5,-3,1.18),(5,-3,1.18),(4.8,3,1.18),(-4.8,3,1.18)],.48,
           (.34,.39,.32,1),METAL_DARK)
    m.sphere((0,0,2.0),1.72,METAL_DARK,12,7)
    for side in (-1,1):
        x=side*2.25
        m.tube(x,-2,2.7,2.55,.52,.45,STEEL,10)
        m.cone(x,2.7,4.2,2.55,.38,.32,(.96,.31,.16,1),10)
        m.slab([(side*2,0,2.9),(side*4.2,0,3.55),
                (side*4.7,-.5,3.55),(side*2,-.5,2.9)],.22,STEEL,METAL_DARK)
    m.polygon([(-.9,-1,3.40),(.9,-1,3.40),(1.45,-1.2,4.45),
               (-1.45,-1.2,4.45)],(0.10,.26,.26,1))
    m.sphere((0,-.8,4.1),.40,(.96,.28,.14,1),10,5)
    return m.create()


def create_marker():
    m=MeshBuilder('beacon-tower')
    m.tube(0,-4.0,4.0,0,.24,.24,STEEL,6)  # forward along Y, rotate when placed
    m.sphere((0,4.25,0),.58,SIGNAL,8,5)
    return m.create()


def create_tracer(length=4.0, color=GOLD):
    m=MeshBuilder('tracer')
    m.slab([(-.075,-length,0),(.075,-length,0),(.075,0,0),(-.075,0,0)],.075,color)
    p=m.create();p.setLightOff();p.setTwoSided(True)
    return p


def create_explosion_core(color=(1.0,.51,.20,1)):
    m=MeshBuilder('blast')
    m.sphere((0,0,0),1.0,color,10,6)
    p=m.create();p.setLightOff();p.setTransparency(TransparencyAttrib.MAlpha)
    return p


def create_smoke():
    """Soft, low-poly black-grey smoke puffs; transparency fades in flight."""
    m=MeshBuilder('soot-and-vapour')
    m.sphere((0,0,0),1.0,(.17,.22,.24,.65),9,5)
    p=m.create();p.setLightOff();p.setTransparency(TransparencyAttrib.MAlpha)
    p.setDepthWrite(False)
    return p


def create_splash():
    """Untextured expanding foam ring for an impact with sea level."""
    m=MeshBuilder('sea-foam-ring')
    n=22
    for i in range(n):
        a=i*math.tau/n; b=(i+1)*math.tau/n
        inner=math.cos(a),math.sin(a); outer=math.cos(b),math.sin(b)
        m.polygon([(inner[0]*.74,inner[1]*.74,0),
                   (inner[0]*1.32,inner[1]*1.32,0),
                   (outer[0]*1.32,outer[1]*1.32,0),
                   (outer[0]*.74,outer[1]*.74,0)],
                  (.72,.92,.95,.74))
    p=m.create();p.setLightOff();p.setTransparency(TransparencyAttrib.MAlpha)
    p.setDepthWrite(False)
    return p


def create_wreckage():
    """Individual breakaway sections; not a whole-jet recolour."""
    debris=[]
    for side in (-1,1):
        m=MeshBuilder('severed-wing')
        def p(x,y,z): return (side*x,y,z)
        m.slab([p(.3,2.3,0),p(2.0,1.1,0),p(6.,-2.1,0),
                p(5.8,-3.6,0),p(2.4,-4.7,0),p(.15,-4.1,0)],.28,
               METAL_TOP,METAL_DARK,METAL)
        m.polygon([p(1.1,.9,.16),p(3.0,-.85,.16),p(4.8,-2.85,.16),p(2.5,-3.5,.16)],PANEL)
        debris.append((m.create(),Vec3(side*5.6,-2.0,0.)))
    for side in (-1,1):
        m=MeshBuilder('tail-shard')
        def p(x,y,z):return (side*x,y,z)
        m.slab([p(0,-1,0),p(1.2,-.4,.3),p(2.,-1.,2.7),p(1.7,-2.,2.5),p(.2,-2.,0)],
               .20,METAL_TOP,METAL_DARK)
        debris.append((m.create(),Vec3(side*1.4,-8.8,.8)))
    m=MeshBuilder('fractured-nose')
    m.cone(0,0,6.6,0,1.0,.63,STEEL,10)
    m.tube(0,-1.0,0.0,0,1.,.6,METAL_DARK,10)
    debris.append((m.create(),Vec3(0,8.,.2)))
    for side in (-1,1):
        m=MeshBuilder('engine-casing')
        m.tube(0,-2.6,1.2,0,.73,.68,METAL_DARK)
        m.tube(0,-2.7,-2.95,0,.52,.50,SIGNAL)
        debris.append((m.create(),Vec3(side*1.1,-8.,-.25)))
    return debris


def create_ejection_seat():
    """Rescue seat with an attached, separately deployable parachute canopy."""
    root=NodePath('ejection-seat')
    m=MeshBuilder('pilot-seat')
    m.slab([(-.43,-.4,-.48),(.43,-.4,-.48),(.43,.48,-.48),(-.43,.48,-.48)],
           .28,METAL_DARK)
    m.sphere((0,.10,.27),.42,STEEL,9,6)
    m.sphere((0,.05,.9),.27,(.91,.64,.37,1),9,6)
    m.polygon([(-.46,-.4,-.35),(-.46,-.4,1.15),(-.46,-.12,1.15),(-.46,-.12,-.35)],PANEL)
    m.create().reparentTo(root)
    chute=MeshBuilder('rescue-parachute')
    canopy_z=3.85; radius=2.65
    for j in range(6):
        a=j*math.tau/6; b=(j+1)*math.tau/6
        c=(.94,.39,.23,1) if j%2 else (.85,.83,.66,1)
        chute.triangle((0,0,canopy_z+1.2),
                       (radius*math.cos(a),radius*math.sin(a),canopy_z),
                       (radius*math.cos(b),radius*math.sin(b),canopy_z),c)
    ch=chute.create();ch.reparentTo(root);ch.setTwoSided(True)
    ls=LineSegs('parachute-lines');ls.setThickness(1.4);ls.setColor(.81,.82,.74,1)
    for j in range(6):
        a=j*math.tau/6
        ls.moveTo(0,0,.2);ls.drawTo(radius*math.cos(a),radius*math.sin(a),canopy_z)
    strings=root.attachNewNode(ls.create())
    ch.hide();strings.hide()
    return root,ch,strings
