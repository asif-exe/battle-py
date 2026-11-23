"""Original fighter avionics-inspired HUD and title/mission screens."""
from __future__ import annotations

import math

from direct.gui.DirectGui import DirectFrame
from direct.gui import DirectGuiGlobals as DGG
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import LineSegs, TextNode, Vec4

from .mathx import clamp
from .settings import COLOR_CYAN, COLOR_GOLD, COLOR_ICE, COLOR_RED

CYAN=Vec4(*COLOR_CYAN)
GOLD=Vec4(*COLOR_GOLD)
ICE=Vec4(*COLOR_ICE)
RED=Vec4(*COLOR_RED)
DARK=Vec4(.018,.057,.071,.87)
MUTED=Vec4(.45,.65,.65,1)


class HUD:
    def __init__(self, app):
        self.app=app
        self.ui=app.aspect2d
        self._text=[]
        self._panels=[]
        self._make_panels()
        self._make_labels()
        self._make_reticle()
        self._make_bars()
        self._make_title()
        self._make_pause()
        self._make_crash_and_damage()
        self.notice_until=0
        self.lock_was=False

    def label(self,text,pos,scale=.04,color=ICE,align=TextNode.ALeft,
              parent=None,may=True):
        p=OnscreenText(text=text,pos=pos,scale=scale,fg=color,align=align,
                       mayChange=may,parent=parent or self.ui,shadow=Vec4(0,.018,.026,.65),
                       shadowOffset=(.0025,.0025))
        self._text.append(p)
        return p

    def panel(self,rect,color=DARK,parent=None):
        p=DirectFrame(parent=parent or self.ui,frameColor=color,frameSize=rect,
                      relief=DGG.FLAT,sortOrder=-3)
        self._panels.append(p)
        return p

    def _make_panels(self):
        self.panel((-1.75,-.92,.73,.97),Vec4(.014,.058,.073,.77))
        self.panel((.92,1.75,.73,.97),Vec4(.014,.058,.073,.77))
        self.panel((-1.75,-1.03,-.96,-.72),Vec4(.014,.058,.073,.76))
        self.panel((1.05,1.75,-.96,-.72),Vec4(.014,.058,.073,.76))
        self.panel((-.34,.34,-.984,-.905),Vec4(.014,.058,.073,.68))

    def _make_labels(self):
        self.label('BATTLE-PY',(-1.71,.88),.066,CYAN)
        self.label('AX-9  /  WRAITH  //  FLIGHT SYSTEMS',(-1.70,.785),.028,MUTED)
        self.score=self.label('000000', (1.70,.884),.065,ICE,TextNode.ARight)
        self.wave=self.label('WAVE 01  /  00 HOSTILES',(1.70,.796),.029,CYAN,TextNode.ARight)
        self.best=self.label('BEST 000000',(1.70,.739),.025,MUTED,TextNode.ARight)
        self.health=self.label('HULL  100%',(-1.70,-.791),.036,ICE)
        self.fuel=self.label('AFTERBURNER',(-1.70,-.861),.027,CYAN)
        self.heat=self.label('CANNON  READY',(-1.70,-.929),.026,MUTED)
        self.speed=self.label('148 KT',(1.70,-.797),.048,ICE,TextNode.ARight)
        self.alt=self.label('ALT 0124 M',(1.70,-.856),.032,CYAN,TextNode.ARight)
        self.ammo=self.label('VIPER  04 / 04',(1.70,-.929),.031,GOLD,TextNode.ARight)
        self.tip=self.label('LMB/J GUN  |  RMB/K MISSILE  |  C FLARES  |  TAB TARGET  |  Q QUIT',
                            (0,-.958),.021,MUTED,TextNode.ACenter)
        self.notice=self.label('',(0,.69),.046,GOLD,TextNode.ACenter)
        self.target=self.label('',(0,-.265),.030,CYAN,TextNode.ACenter)
        self.radar=self.label('RADAR  //  SEARCHING',(-1.72,.66),.029,CYAN)
        self.status=self.label('SYSTEM: NOMINAL',(1.71,.65),.029,MUTED,TextNode.ARight)
        self.alt_warning=self.label('',(0,.58),.044,RED,TextNode.ACenter)
        self.lock_text=self.label('',(0,0),.027,RED,TextNode.ACenter)
        self.lock_text.hide()
        self.incoming=self.label('',(0,.48),.048,RED,TextNode.ACenter)
        self.flares=self.label('FLARES 03 / 03',(1.70,-.681),.028,GOLD,TextNode.ARight)
        self.chain=self.label('',(-1.72,.56),.034,GOLD)
        self.boss_label=self.label('',(0,.865),.034,RED,TextNode.ACenter)
        self.hit_marker=self.label('',(0,.120),.043,GOLD,TextNode.ACenter)

    def _make_bars(self):
        self.bar_nodes={}
        for key,x,y,w,h,col in [
            ('hull',-1.70,-.812,.49,.013,Vec4(.18,.86,.71,.98)),
            ('fuel',-1.70,-.880,.49,.013,CYAN),
            ('heat',-1.70,-.947,.49,.008,GOLD),
        ]:
            self.panel((x,x+w,y,y+h),Vec4(.17,.29,.31,.90))
            p=self.panel((0,w,0,h),col)
            p.setPos(x,0,y)
            self.bar_nodes[key]=p
        self.boss_back=self.panel((-.33,.33,.790,.804),Vec4(.2,.12,.11,.85))
        self.boss_bar=self.panel((0,.64,0,.014),RED)
        self.boss_bar.setPos(-.32,0,.790)
        self.boss_back.hide();self.boss_bar.hide()

    def _make_reticle(self):
        ls=LineSegs('flight-reticle')
        ls.setThickness(1.8)
        ls.setColor(CYAN)
        # Independent strokes form an uncluttered dogfighting reticle.
        for a,b in [
            ((-.084,0),(-.040,0)),((.040,0),(.084,0)),
            ((0,-.082),(0,-.041)),((0,.041),(0,.082)),
            ((-.028,.028),(-.016,.028)),((.016,.028),(.028,.028)),
            ((-.028,-.028),(-.016,-.028)),((.016,-.028),(.028,-.028))
        ]:
            ls.moveTo(a[0],0,a[1]);ls.drawTo(b[0],0,b[1])
        # Drop the interior cross, keeping an open centre for target visibility.
        self.reticle=self.ui.attachNewNode(ls.create())
        ls2=LineSegs('target-brackets')
        ls2.setColor(RED);ls2.setThickness(2.)
        h=.062;s=.022
        for signx in (-1,1):
            for signy in (-1,1):
                x=signx*h;z=signy*h
                ls2.moveTo(x,0,z-signy*s);ls2.drawTo(x,0,z)
                ls2.drawTo(x-signx*s,0,z)
        self.lock_box=self.ui.attachNewNode(ls2.create())
        self.lock_box.hide()
        ls3=LineSegs('lead-indicator')
        ls3.setThickness(2.0);ls3.setColor(GOLD)
        for a,b in (((-.026,0),(-.012,0)),((.012,0),(.026,0)),
                    ((0,-.026),(0,-.012)),((0,.012),(0,.026))):
            ls3.moveTo(a[0],0,a[1]);ls3.drawTo(b[0],0,b[1])
        self.lead_pip=self.ui.attachNewNode(ls3.create())
        self.lead_pip.hide()
        # Tactical compass gives off-screen threats a useful direction.
        centre=(-1.48,.37); radius=.167
        radar=LineSegs('combat-radar')
        radar.setThickness(1.2);radar.setColor(Vec4(.29,.72,.76,.55))
        for ring in (.5,1.):
            for i in range(32):
                a=math.tau*i/32;b=math.tau*(i+1)/32
                radar.moveTo(centre[0]+radius*ring*math.cos(a),0,
                             centre[1]+radius*ring*math.sin(a))
                radar.drawTo(centre[0]+radius*ring*math.cos(b),0,
                             centre[1]+radius*ring*math.sin(b))
        radar.moveTo(centre[0]-radius,0,centre[1]);radar.drawTo(centre[0]+radius,0,centre[1])
        radar.moveTo(centre[0],0,centre[1]-radius);radar.drawTo(centre[0],0,centre[1]+radius)
        self.radar_circle=self.ui.attachNewNode(radar.create())
        self.radar_dots=[self.label('',centre,.023,RED,TextNode.ACenter)
                         for _ in range(12)]

    def _make_title(self):
        self.title_layer=self.ui.attachNewNode('title-screen')
        self.panel((-1.8,1.8,-1.02,1.02),Vec4(.012,.037,.051,.65),self.title_layer)
        self.panel((-.92,.92,-.58,.74),Vec4(.023,.083,.102,.86),self.title_layer)
        self.label('BATTLE-PY',(0,.38),.127,ICE,TextNode.ACenter,self.title_layer)
        self.label('THE WRAITH PROTOCOL',(0,.22),.042,GOLD,TextNode.ACenter,self.title_layer)
        self.label('DOGFIGHT  /  DEFEND  /  DOMINATE',(0,.089),.037,CYAN,
                   TextNode.ACenter,self.title_layer)
        self.label('HOSTILE SQUADRONS  /  SAM BATTERIES  /  ACE ENCOUNTERS',
                   (0,-.027),.024,MUTED,TextNode.ACenter,self.title_layer)
        self.label('ENTER  TO DEPLOY',(0,-.193),.073,GOLD,TextNode.ACenter,self.title_layer)
        self.label('STEER  MOUSE / WASD       GUN  LMB / J       MISSILE  RMB / K',
                   (0,-.338),.027,ICE,TextNode.ACenter,self.title_layer)
        self.label('FLARES  C      TARGET  TAB      BOOST  SHIFT      ROLL  SPACE',
                   (0,-.402),.026,ICE,TextNode.ACenter,self.title_layer)
        self.label('E  EJECT      V  CAMERA      M  SOUND      Q  QUIT GAME',
                   (0,-.506),.023,MUTED,TextNode.ACenter,self.title_layer)

    def _make_pause(self):
        self.pause_layer=self.ui.attachNewNode('modal-layer')
        self.panel((-.70,.70,-.36,.36),Vec4(.012,.04,.052,.93),self.pause_layer)
        self.modal_title=self.label('PAUSED',(0,.155),.089,ICE,
                                    TextNode.ACenter,self.pause_layer)
        self.modal_body=self.label('P / ESC TO RESUME',(0,-.01),.045,GOLD,
                                   TextNode.ACenter,self.pause_layer)
        self.modal_hint=self.label('Q  QUIT GAME     M  SOUND     V  CAMERA',(0,-.163),.028,CYAN,
                                   TextNode.ACenter,self.pause_layer)
        self.pause_layer.hide()

    def _make_crash_and_damage(self):
        # The damage wash is intentionally thin; a solid overlay would conceal
        # navigation during high-pressure low-altitude combat.
        self.damage_panel=self.panel((-2.3,2.3,-1.25,1.25),Vec4(1.,.10,.06,0.))
        self.crash_layer=self.ui.attachNewNode('crash-warning')
        self.panel((-.98,.98,-.22,.22),Vec4(.12,.017,.017,.83),self.crash_layer)
        self.crash_title=self.label('MAYDAY  //  MAYDAY',(0,.065),.072,RED,
                                    TextNode.ACenter,self.crash_layer)
        self.crash_detail=self.label('AIRFRAME LOST',(0,-.10),.038,ICE,
                                     TextNode.ACenter,self.crash_layer)
        self.crash_layer.hide()
        self.modal_extra=self.label('',(0,-.263),.030,ICE,
                                    TextNode.ACenter,self.pause_layer)
        self.modal_extra2=self.label('',(0,-.320),.025,MUTED,
                                     TextNode.ACenter,self.pause_layer)

    def set_results(self,game):
        self.modal_title.setText('PILOT SAFE' if game.pilot_survived else 'AIRFRAME LOST')
        self.modal_title.setFg(CYAN if game.pilot_survived else RED)
        self.modal_body.setText(f'{game.death_cause.upper()}')
        self.modal_hint.setText('ENTER / R  REDEPLOY    ESC  MENU    Q  QUIT')
        self.modal_extra.setText(f'SCORE {game.score:06d}     KILLS {game.kills:03d}     WAVE {game.wave:02d}')
        self.modal_extra2.setText(f'BEST {max(game.best_score,game.score):06d}  //  WRAITH PROTOCOL')

    def set_error(self,summary,logfile):
        self.title_layer.hide();self.crash_layer.hide();self.pause_layer.show()
        self.modal_title.setText('GAMEPLAY ERROR')
        self.modal_title.setFg(RED)
        self.modal_body.setText(summary[:48])
        self.modal_hint.setText('ESC  MENU  /  ENTER  RETRY  /  Q  QUIT')
        self.modal_extra.setText('ERROR DETAILS SAVED TO:')
        self.modal_extra2.setText(logfile[-65:])

    def update_damage(self,amount,game_time):
        a=max(0.,min(.26,amount))
        self.damage_panel['frameColor']=(.94,.045,.025,a)

    def set_overlay(self,mode):
        if mode=='menu': self.title_layer.show();self.pause_layer.hide();self.crash_layer.hide()
        elif mode=='crashing':
            self.title_layer.hide();self.pause_layer.hide();self.crash_layer.show()
        elif mode in ('paused','dead','error'):
            self.title_layer.hide();self.pause_layer.show()
            if mode=='paused':
                self.modal_title.setText('FLIGHT PAUSED')
                self.modal_body.setText('P / ESC TO RESUME')
                self.modal_hint.setText('Q: QUIT   M: SOUND   V: CAMERA')
                self.modal_extra.setText('TAB: TARGET    C: FLARES    E: EJECT')
                self.modal_extra2.setText('ESC / P  TO RESUME FLIGHT')
            elif mode=='dead':
                self.modal_title.setText('AIRFRAME LOST')
                self.modal_body.setText('ENTER TO REDEPLOY')
                self.modal_hint.setText('THE MISSION IS NOT OVER')
        else:self.title_layer.hide();self.pause_layer.hide();self.crash_layer.hide()

    def notify(self,text,seconds=2.4,color=GOLD):
        self.notice.setText(text)
        self.notice.setFg(color)
        self.notice_until=self.app.game_time+seconds

    def update(self,game):
        self.score.setText(f'{game.score:06d}')
        self.best.setText(f'BEST {max(game.best_score,game.score):06d}')
        self.wave.setText(f'WAVE {game.wave:02d}  /  {len(game.enemies)+len(game.sites):02d} HOSTILES')
        self.health.setText(f'HULL  {int(game.hull):03d}%')
        self.fuel.setText('AFTERBURNER' if game.boost_energy>.1 else 'BOOST RECHARGING')
        self.heat.setText('CANNON  HOT' if game.gun_heat>.9 else 'CANNON  READY')
        self.speed.setText(f'{int(game.speed*1.95):03d} KT')
        altitude=max(0,game.jet.getZ()-max(game.world.height(game.jet.getX(),game.jet.getY()),0))
        self.alt.setText(f'AGL {int(altitude):04d} M')
        self.ammo.setText(f'VIPER  {game.ammo:02d} / 04')
        self.flares.setText(f'FLARES  {game.flare_ammo:02d} / 03  [C]')
        self.flares.setFg(RED if game.flare_ammo==0 else GOLD)
        self.chain.setText(f'{game.streak}X KILL CHAIN' if game.streak>=2 else '')
        boss=next((enemy for enemy in game.enemies if enemy.kind=='ace'),None)
        if boss:
            self.boss_label.setText('SPECTRE  //  HOSTILE ACE')
            self.boss_back.show();self.boss_bar.show()
            from .combat import HOSTILES
            max_hp=HOSTILES['ace'].hitpoints+min(45,game.wave*3)
            self.boss_bar.setSx(clamp(boss.hp/max_hp,0.,1.))
        else:
            self.boss_label.setText('')
            self.boss_back.hide();self.boss_bar.hide()
        inbound=game.incoming_count
        if inbound:
            self.incoming.setText(f'!  MISSILE INBOUND ({inbound})  //  C TO FLARE  !')
            self.incoming.setFg(RED if int(game.game_time*5)%2==0 else GOLD)
        else:
            self.incoming.setText('')
        self.hit_marker.setText('X' if game.hit_flash>0 else '')
        self.bar_nodes['hull'].setSx(clamp(game.hull/100,0.,1.))
        self.bar_nodes['fuel'].setSx(clamp(game.boost_energy,0.,1.))
        self.bar_nodes['heat'].setSx(clamp(game.gun_heat,0.,1.))
        self.status.setText('FIRE / EJECT: E' if game.hull<25 else
                            'SYSTEM: DAMAGED' if game.hull<55 else 'SYSTEM: NOMINAL')
        from .survival import warning_altitude
        self.alt_warning.setText('PULL UP  //  TERRAIN' if warning_altitude(altitude,game.speed) else '')
        self.status.setFg(RED if game.hull<25 else MUTED)
        threats=game.enemies+game.sites
        q=game.jet.getQuat(game.render)
        right=q.getRight(); forward=q.getForward()
        centre=(-1.48,.37); radius=.159
        for i,dot in enumerate(self.radar_dots):
            if i>=len(threats):dot.setText('');continue
            hostile=threats[i]
            offset=hostile.pos-game.jet.getPos()
            x=clamp(offset.dot(right)/1150.,-1.,1.)*radius
            y=clamp(offset.dot(forward)/1150.,-1.,1.)*radius
            dot.setPos(centre[0]+x,centre[1]+y)
            dot.setText('S' if hostile.kind=='sam' else '+' if hostile.kind=='scout' else 'X')
            dot.setFg(GOLD if hostile is game.target else RED)
        if self.app.game_time>self.notice_until:
            self.notice.setText('')
        enemy=game.target
        if enemy and enemy in game.enemies:
            self.radar.setText(f'RADAR // {enemy.kind.upper()}-{enemy.serial:03d}')
            self.target.setText(('LOCK CONFIRMED' if game.locked else 'TRACKING TARGET')+
                                f'  {int((enemy.pos-game.jet.getPos()).length())}M')
            projected=game.project_world(enemy.pos)
            if projected:
                x,y=projected
                self.lock_box.setPos(x,0,y)
                self.lock_box.setColorScale(1.,.52 if game.locked else 1.,
                                            .36 if game.locked else 1.,1.)
                self.lock_box.show()
                self.lock_text.setPos(x,y-.12)
                self.lock_text.setText('LOCK' if game.locked else enemy.kind.upper())
                self.lock_text.setFg(GOLD if game.locked else RED)
                self.lock_text.show()
                velocity=getattr(enemy,'velocity',None)
                if velocity is not None:
                    # Cannon lead marker; align jet nose with the gold pip.
                    flight_time=min(1.25,(enemy.pos-game.jet.getPos()).length()/590.)
                    predicted=enemy.pos+velocity*flight_time
                    lead=game.project_world(predicted)
                    if lead:
                        self.lead_pip.setPos(lead[0],0,lead[1])
                        self.lead_pip.show()
                    else:self.lead_pip.hide()
                else:self.lead_pip.hide()
            else:
                self.lock_box.hide();self.lock_text.hide();self.lead_pip.hide()
        else:
            self.radar.setText('RADAR  //  SEARCHING')
            self.target.setText('')
            self.lock_box.hide();self.lock_text.hide();self.lead_pip.hide()
