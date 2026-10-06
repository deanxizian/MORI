#!/usr/bin/env python3
"""Schematic-only functional layout. NEVER writes PCB, project, or contracts.

The reviewed connectivity.json supplies every pin number, electrical type,
component UUID, value and footprint. Block-internal nets are real orthogonal
wires; named ports are used only for nets shared between functional blocks.
The router prohibits coincident wires of different nets and emits junctions
only at branches of the same net. KiCad netlist comparison remains mandatory.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import heapq
import json
import math
import re
import uuid
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]
G = 2.54
q = lambda s: json.dumps(str(s), ensure_ascii=False)
num = lambda x: f'{x:.4f}'.rstrip('0').rstrip('.') or '0'
mm = lambda x: num(x * G)


def sexpr(text):
    stack=[];root=None
    for t in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',text):
        if t=='(':
            node=[]
            if stack:stack[-1].append(node)
            else:root=node
            stack.append(node)
        elif t==')':stack.pop()
        else:stack[-1].append(t)
    return root


def encode(node):
    return '('+' '.join(encode(x) if isinstance(x,list) else x for x in node)+')'


@lru_cache(None)
def transistor_graphics(kind):
    """Use KiCad's standard transistor graphics, retaining reviewed pad mapping.

    Library art is CC-BY-SA-4.0 with the KiCad exception; no library electrical
    types or pad numbering are substituted for the reviewed MORI definitions.
    """
    lib='Transistor_BJT' if kind=='npn' else 'Transistor_FET'
    name={'pmos':'Q_PMOS_GSD','nmos':'Q_NMOS_GSD','npn':'Q_NPN_BEC'}[kind]
    root=sexpr((Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols')/(lib+'.kicad_sym')).read_text())
    symbol=next(x for x in root if isinstance(x,list) and x[:2]==['symbol',q(name)])
    graphics=[g for unit in symbol if isinstance(unit,list) and unit[0]=='symbol' for g in unit if isinstance(g,list) and g[0] in ['polyline','circle','arc']]
    def transform(n):
        if n[0] in ['xy','center','start','end','mid'] and len(n)==3:
            x,y=float(n[1])*2/G,-float(n[2])*2/G
            if kind=='pmos':x,y=-y,-x+2
            return [n[0],mm(x),mm(-y)]
        if n[0]=='radius':return ['radius',num(float(n[1])*2)]
        return [transform(x) if isinstance(x,list) else x for x in n]
    return [encode(transform(g)) for g in graphics]


def effects(size=1, justify=None, hide=False):
    size=round(size*1.27,4)
    return f'(effects (font (size {size} {size}))' + (f' (justify {justify})' if justify else '') + (' (hide yes)' if hide else '') + ')'


def prop(name, value, x, y, hide=False, size=1, justify=None):
    return f'(property {q(name)} {q(value)} (at {mm(x)} {mm(y)} 0) {effects(size, justify, hide=hide)})'


class Drawing:
    def __init__(self, name):
        self.name = name
        self.folder = ROOT / 'kicad' / name
        self.data = json.loads((self.folder / 'connectivity.json').read_text())
        self.parts = {c['ref']: c for c in self.data['components']}
        # Earlier connectivity metadata used an over-strong PWR_FLAG caption.
        # Retain the UNVALIDATED wording already present in the original CAD;
        # this symbol represents a supply boundary, never a qualification.
        for ref,c in self.parts.items():
            if ref.startswith('#FLG') and not c.get('internal_power_declaration'):c['value']='External supply boundary (UNVALIDATED)'
        old = (self.folder / (name + '.kicad_sch')).read_text()
        self.root = re.search(r'\(uuid ([^)]+)\)', old).group(1)
        original=sexpr(old)
        self.original_properties={};self.original_pin_uuids={}
        for symbol in original:
            if isinstance(symbol,list) and symbol[0]=='symbol' and any(isinstance(x,list) and x[0]=='lib_id' for x in symbol):
                fields={json.loads(p[1]):json.loads(p[2]) for p in symbol if isinstance(p,list) and p[0]=='property'}
                self.original_properties[fields['Reference']]=fields
                self.original_pin_uuids[fields['Reference']]={json.loads(p[1]):next(x[1] for x in p if isinstance(x,list) and x[0]=='uuid') for p in symbol if isinstance(p,list) and p[0]=='pin'}
        self.objects, self.libs, self.local_libs = [], [], []
        self.placed, self.blocks, self.stats = {}, [], []
        self.serial = 0
        self.paper = 'A1'

    def uid(self, key):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, 'mori-functional-P1/' + self.name + '/' + key))

    def add(self, text):
        self.serial += 1
        self.objects.append(text.replace('@UUID@', self.uid(str(self.serial))))

    def text(self, text, x, y, size=1.2):
        self.add(f'(text {q(text)} (at {mm(x)} {mm(y)} 0) {effects(size, "left")} (uuid @UUID@))')

    def line(self, points, graphic=False):
        pts = ' '.join(f'(xy {mm(x)} {mm(y)})' for x, y in points)
        if graphic:
            self.add(f'(polyline (pts {pts}) (stroke (width 0.254) (type default)) (fill (type none)) (uuid @UUID@))')
        else:
            self.add(f'(wire (pts {pts}) (stroke (width 0.254) (type default)) (uuid @UUID@))')

    def block(self, title, x, y, w, h, note=''):
        b = Block(self, title, x, y, w, h, note)
        self.blocks.append(b)
        return b

    def finish(self):
        missing = set(self.parts) - set(self.placed)
        assert not missing, ('Unplaced components', missing)
        net_blocks = defaultdict(set)
        for b in self.blocks:
            for ref in b.refs:
                for p in self.parts[ref]['pins'].values():
                    if p['net']:
                        net_blocks[p['net']].add(b.title)
        for b in self.blocks:
            b.route(net_blocks)
        for b,stats in zip(self.blocks,self.stats):stats['bounds_mm']=[round(v*G,4) for v in [b.x,b.y,b.w,b.h]]
        title = self.name.replace('MORI_', 'MORI / ').replace('_P1', ' / P1').replace('_P2', ' / P2')
        paper=f'(paper "User" {self.paper[0]} {self.paper[1]})' if isinstance(self.paper,tuple) else f'(paper {q(self.paper)})'
        sch = f'(kicad_sch (version 20250114) (generator "mori_functional") (uuid {self.root}) {paper}\n'
        sch += f'(title_block (title {q(title + " - FUNCTIONAL SCHEMATIC")}) (date "2026-09-22") (rev "S2 drawing layout") (comment 1 "PROTOTYPE / UNVALIDATED - electrical design unchanged"))\n'
        sch += '(lib_symbols\n' + '\n'.join(self.libs) + ')\n'
        sch += '\n'.join(self.objects) + '\n(sheet_instances (path "/" (page "1"))))\n'
        dest = self.folder / (self.name + '.kicad_sch')
        dest.write_text(sch)
        (self.folder / 'MORI.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "mori_functional")\n' + '\n'.join(self.local_libs) + ')\n')
        return dict(project=self.name, paper=self.paper, components=len(self.placed), blocks=self.stats,
                    schematic_sha256=hashlib.sha256(dest.read_bytes()).hexdigest())


class Block:
    def __init__(self, drawing, title, x, y, w, h, note):
        self.d, self.title = drawing, title
        self.x, self.y, self.w, self.h = x, y, w, h
        self.refs, self.pins, self.obstacles = [], {}, set()
        self.rects = []
        drawing.line([(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)], True)
        drawing.text(title, x+2, y+3, 1.8)
        if note:
            drawing.text(note, x+2, y+h-2, 1)

    def box_obstacle(self, x1, y1, x2, y2):
        self.rects.append((x1,y1,x2,y2))
        for x in range(math.floor(x1*2), math.ceil(x2*2)+1):
            for y in range(math.floor(y1*2), math.ceil(y2*2)+1):
                self.obstacles.add((x,y))

    def place(self, ref, x, y, kind=None, pins=None, w=16, h=14, orient='h', short=None, caption_at=None,pitch=2):
        """Coordinates are local 100-mil units. Pin table uses screen coordinates."""
        d, c = self.d, self.d.parts[ref]
        assert ref not in d.placed, ref
        d.placed[ref] = self.title
        self.refs.append(ref)
        x += self.x
        y += self.y
        if kind is None:
            kind = 'r' if ref.startswith('R') else 'c' if ref.startswith('C') else 'conn' if ref.startswith('J') else 'flag' if ref.startswith('#') else 'hole' if ref.startswith('H') else 'ic'
        libname = ref.replace('#','')
        hide_names = kind in ['r','l','fuse','c','cp','diode','zener','schottky','pmos','nmos','npn','hole','flag','dualcmp']
        hide_numbers = kind in ['r','l','fuse','c','cp','flag']
        graphics = []

        def path(points, width=.254, fill='none'):
            pts=' '.join(f'(xy {mm(a)} {mm(-b)})' for a,b in points)
            graphics.append(f'(polyline (pts {pts}) (stroke (width {width}) (type default)) (fill (type {fill})))')

        def rect(x1,y1,x2,y2):
            graphics.append(f'(rectangle (start {mm(x1)} {mm(-y1)}) (end {mm(x2)} {mm(-y2)}) (stroke (width 0.254) (type default)) (fill (type background)))')

        def circle(cx,cy,r):
            graphics.append(f'(circle (center {mm(cx)} {mm(-cy)}) (radius {mm(r)}) (stroke (width 0.254) (type default)) (fill (type none)))')

        def internal(text,a,b,size=1):
            graphics.append(f'(text {q(text)} (at {mm(a)} {mm(-b)} 0) {effects(size)})')

        if kind in ['r','l','fuse','c','cp','diode','zener','schottky']:
            vertical = orient in ['v','vu']
            reverse = orient in ['hr','vu']
            def trans(a,b):
                if reverse: a=-a
                return (b,a) if vertical else (a,b)
            pins={'1':(*trans(-3,0),'T' if vertical and not reverse else 'B' if vertical else 'R' if reverse else 'L'),
                  '2':(*trans(3,0),'B' if vertical and not reverse else 'T' if vertical else 'L' if reverse else 'R')}
            def pp(seq):path([trans(*v) for v in seq])
            if kind in ['r','fuse']:
                pp([(-2,-.65),(2,-.65),(2,.65),(-2,.65),(-2,-.65)])
                if kind=='fuse':pp([(-2,0),(2,0)])
                body=(-2,-.8,2,.8)
            elif kind=='l':
                points=[(-2,0)]
                for i in range(4):
                    for j in range(1,13):
                        theta=math.pi-math.pi*j/12
                        points.append((-1.5+i+.5*math.cos(theta),-.65*math.sin(theta)))
                pp(points);pp([(-2,.8),(2,.8)])
                body=(-2,-.8,2,1)
            elif kind in ['c','cp']:
                pp([(-.4,-1.2),(-.4,1.2)]); pp([(.4,-1.2),(.4,1.2)])
                pp([(-2,0),(-.4,0)]); pp([(.4,0),(2,0)])
                if kind=='cp':pp([(-1.5,-2),(-1.5,-1)]);pp([(-2,-1.5),(-1,-1.5)])
                body=(-2,-1.5,2,1.5)
            else:
                pp([(-1, -1.2),(-1,1.2)])
                pp([(-1,0),(1,-1.2),(1,1.2),(-1,0)])
                pp([(-2,0),(-1,0)]); pp([(1,0),(2,0)])
                if kind=='zener':pp([(-1,-1.2),(-.5,-1.6)]);pp([(-1,1.2),(-1.5,1.6)])
                if kind=='schottky':pp([(-1,-1.2),(-.4,-1.2),(-.4,-.6)]);pp([(-1,1.2),(-1.6,1.2),(-1.6,.6)])
                body=(-2,-1.7,2,1.7)
            if vertical:body=(body[1],body[0],body[3],body[2])
            plen=1
        elif kind=='conn':
            n=len(c['pins'])
            if pins is None:
                side='R' if orient=='r' else 'L'
                pins={pn:((-3 if side=='L' else 3),(i-(n-1)/2)*pitch,side) for i,pn in enumerate(c['pins'])}
                rect(-1,-n*pitch/2,1,n*pitch/2)
                for i in range(n):rect(-.45,(i-(n-1)/2)*pitch-.35,.45,(i-(n-1)/2)*pitch+.35)
                body=(-1,-n*pitch/2,1,n*pitch/2)
            else:
                rect(-w/2,-h/2,w/2,h/2);body=(-w/2,-h/2,w/2,h/2)
            plen=2
            hide_names=True
        elif kind in ['pmos','nmos','npn']:
            graphics.extend(transistor_graphics(kind))
            if kind=='pmos':
                pins={str(i):(-6,0,'L') for i in [1,2,3]}
                pins.update({str(i):(6,0,'R') for i in [5,6,7,8]});pins['4']=(0,6,'B')
                path([(-4,0),(-2,0)]);path([(4,0),(2,0)])
                body=(-4,-2.5,4,4);plen=2
                if orient=='hr':
                    def mirror(n):
                        if n[0] in ['xy','center','start','end','mid'] and len(n)==3:return [n[0],num(-float(n[1])),n[2]]
                        return [mirror(v) if isinstance(v,list) else v for v in n]
                    graphics=[encode(mirror(sexpr(g))) for g in graphics]
                    pins={pn:(-px,py,{'L':'R','R':'L'}.get(side,side)) for pn,(px,py,side) in pins.items()}
            else:
                pins={'1':(-5,0,'L'),'2':(2,5,'B'),'3':(2,-5,'T')}
                path([(-3,0),(-2,0)]);path([(2,-3),(2,-2)]);path([(2,3),(2,2)])
                body=(-3,-3,4,3);plen=2
        elif kind=='dualcmp':
            assert pins
            for cy in [-13,18]:
                path([(-11,cy-10),(-11,cy+10),(11,cy),(-11,cy-10)])
                internal('+',-9,cy-3);internal('-',-9,cy+3)
            path([(0,-23),(0,-18)]);path([(0,26),(0,23)])
            internal('A',-3,-13);internal('B',-3,18)
            body=(-11,-23,11,28);plen=2
        elif kind=='flag':
            pins={'1':(0,2,'B')};path([(0,1),(0,-1),(-1,-1.6),(0,-2.2),(1,-1.6),(0,-1)])
            body=(-1,-2.2,1,1);plen=1
            short='PWR boundary'
        elif kind=='hole':
            pins={};circle(0,0,1);circle(0,0,.4);body=(-1,-1,1,1);plen=1
        else:
            assert pins, ('IC pin positions required',ref)
            rect(-w/2,-h/2,w/2,h/2);body=(-w/2,-h/2,w/2,h/2);plen=2
        assert set(pins)==set(c['pins']), (ref,set(pins)^set(c['pins']))
        # Repeated power pins on a single MOSFET stay electrically explicit,
        # with hidden duplicate graphics at their common terminal.
        seen=set();pinsexpr=[]
        for pn,(px,py,side) in pins.items():
            p=c['pins'][pn];duplicate=(px,py) in seen;seen.add((px,py))
            angle={'L':0,'R':180,'T':270,'B':90}[side]
            pinsexpr.append(f'(pin {p["type"]} line (at {mm(px)} {mm(-py)} {angle}) (length {mm(plen)})'+(' (hide yes)' if duplicate else '')+
                           f' (name {q(p["name"])} {effects(.95)}) (number {q(pn)} {effects(.85)}))')
            xy=(round((x+px)*2),round((y+py)*2))
            self.pins[(ref,pn)]=(xy,p['net'],side)
        sx=f'(symbol {q("MORI:"+libname)}'+(' (pin_numbers hide)' if hide_numbers else '')+f' (pin_names (offset 0.5){" (hide yes)" if hide_names else ""}) (exclude_from_sim no) (in_bom yes) (on_board yes)'
        sx+=prop('Reference',ref,0,body[1]-2)+prop('Value',c['value'],0,body[1]-1)+prop('Footprint',c['footprint'],0,0,True)
        sx+=f'(symbol {q(libname+"_0_1")}'+''.join(graphics)+')'
        sx+=f'(symbol {q(libname+"_1_1")}'+''.join(pinsexpr)+'))'
        d.libs.append(sx);d.local_libs.append(sx.replace(q('MORI:'+libname),q(libname),1))
        sid=c.get('uuid') or str(uuid.uuid5(uuid.NAMESPACE_URL,'mori-v12-P1/'+d.name+'/'+ref))
        on='yes' if c['footprint'] else 'no'
        sy=f'(symbol (lib_id {q("MORI:"+libname)}) (at {mm(x)} {mm(y)} 0) (unit 1) (exclude_from_sim no) (in_bom {on}) (on_board {on}) (dnp {"yes" if c.get("dnp") else "no"}) (uuid {sid})'
        # Values remain exact in properties, even when a shorter visible legend
        # is needed for long manufacturer strings.
        if short is None:short=c['value']
        if kind=='flag':short=c.get('flag_caption','Supply boundary')
        if kind in ['r','l','fuse','c','cp','diode','zener','schottky'] and orient in ['v','vu']:
            tx=x+3;ty=y-1
            sy+=prop('Reference',ref,tx,ty,size=.95,justify='left')+prop('Value',c['value'],tx,y+.3,hide=short!=c['value'],size=.95,justify='left')
            if short!=c['value']:d.text(short,tx-1,y+.3,.95)
            self.box_obstacle(x+2,y-1.7,x+max(4,len(short)*.25)+3,y+.7)
        else:
            tx,ty=(self.x+caption_at[0],self.y+caption_at[1]) if caption_at else (x-w/2 if kind=='ic' else x,y+body[1]-(5 if kind=='ic' else 2))
            sy+=prop('Reference',ref,tx,ty,size=1)+prop('Value',c['value'],tx,ty+1.2,hide=short!=c['value'],size=.95)
            if short!=c['value']:d.text(short,tx-len(short)*.095,ty+1.2,.95)
            width=max(len(ref)*.27,len(short)*.25)/2
            self.box_obstacle(tx-width,ty-.5,tx+width,ty+1.6)
        sy+=prop('Footprint',c['footprint'],x,y,True)+prop('Datasheet',d.original_properties.get(ref,{}).get('Datasheet',c.get('source','')),x,y,True)
        for pn in c['pins']:
            puid=d.original_pin_uuids.get(ref,{}).get(pn) or str(uuid.uuid5(uuid.NAMESPACE_URL,'mori-v12-P1/'+d.name+'/'+ref+'p'+pn))
            sy+=f'(pin {q(pn)} (uuid {puid}))'
        sy+=f'(instances (project {q(d.name)} (path {q("/"+d.root)} (reference {q(ref)}) (unit 1)))))'
        d.add(sy)
        self.box_obstacle(x+body[0]-.2,y+body[1]-.2,x+body[2]+.2,y+body[3]+.2)
        return ref

    def route(self, net_blocks):
        endpoints=defaultdict(set);all_pin_nets=defaultdict(set);stubs=defaultdict(set)
        for key,(xy,net,side) in self.pins.items():
            if net is None:
                self.d.add(f'(no_connect (at {mm(xy[0]/2)} {mm(xy[1]/2)}) (uuid @UUID@))')
            else:
                dx,dy={'L':(-1,0),'R':(1,0),'T':(0,-1),'B':(0,1)}[side]
                end=(xy[0]+2*dx,xy[1]+2*dy)
                endpoints[net].add(end)
                for i in range(3):all_pin_nets[(xy[0]+i*dx,xy[1]+i*dy)].add(net)
                for i in range(2):stubs[net].add(tuple(sorted(((xy[0]+i*dx,xy[1]+i*dy),(xy[0]+(i+1)*dx,xy[1]+(i+1)*dy)))))
            all_pin_nets[xy].add(net)
        # Power/signal ports on the block edges. The net name stays identical to
        # the original local label, so the PCB's /NET names do not change.
        shared=[n for n in endpoints if len(net_blocks[n])>1]
        ports=defaultdict(set)
        sides={'L':[],'R':[]}
        mid=(self.x+self.w/2)*2
        for net in shared:
            mean=sum(p[0] for p in endpoints[net])/len(endpoints[net])
            sides['L' if mean<mid else 'R'].append(net)
        for side,ns in sides.items():
            ns.sort(key=lambda n:sum(p[1] for p in endpoints[n])/len(endpoints[n]))
            previous=(self.y+6)*2
            for i,net in enumerate(ns):
                target=round(sum(p[1] for p in endpoints[net])/len(endpoints[net]))
                target=min(target,round((self.y+self.h-5)*2)-(len(ns)-1-i)*5)
                py=max(previous+5,target);previous=py
                px=round((self.x+2 if side=='L' else self.x+self.w-2)*2)
                xy=(px,py);endpoints[net].add(xy);all_pin_nets[xy].add(net)
                ports[net].add(xy)
                justify='left bottom' if side=='L' else 'right bottom'
                self.d.add(f'(label {q(net)} (at {mm(px/2)} {mm(py/2)} 0) {effects(1,justify)} (uuid @UUID@))')
                # Keep other nets clear of printed names. The label's own wire
                # runs below its baseline.
                width=len(net)*.26
                self.box_obstacle(px/2 if side=='L' else px/2-width,py/2-.9,
                                  px/2+width if side=='L' else px/2,py/2-.3)
        occupied=defaultdict(dict);edges=defaultdict(set)
        for net,es in stubs.items():
            edges[net].update(es)
            for a,b in es:
                axis=0 if a[1]==b[1] else 1
                occupied[a].setdefault(net,set()).add(axis);occupied[b].setdefault(net,set()).add(axis)
        bounds=(round((self.x+1)*2),round((self.y+5)*2),round((self.x+self.w-1)*2),round((self.y+self.h-4)*2))
        # Pin-to-symbol leads are already part of the symbol. Reserve those
        # leads against unrelated wires, and force route departure outward.
        pin_dirs={}
        for (ref,pn),(xy,net,side) in self.pins.items():
            pin_dirs[xy]={'L':(-1,0),'R':(1,0),'T':(0,-1),'B':(0,1)}[side]

        def search(start, targets, net):
            tx1=min(x for x,y in targets);tx2=max(x for x,y in targets)
            ty1=min(y for x,y in targets);ty2=max(y for x,y in targets)
            def heuristic(p):return max(tx1-p[0],0,p[0]-tx2)+max(ty1-p[1],0,p[1]-ty2)
            initial=(start[0],start[1],-1)
            queue=[(heuristic(start),0,initial)];dist={initial:0};prev={};goal=None
            while queue:
                _,cost,state=heapq.heappop(queue)
                if cost!=dist[state]:continue
                x,y,old=state;here=(x,y)
                if here in targets:
                    goal=state;break
                for direction,(dx,dy) in enumerate([(1,0),(0,1),(-1,0),(0,-1)]):
                    p=(x+dx,y+dy);axis=direction%2
                    if not(bounds[0]<=p[0]<=bounds[2] and bounds[1]<=p[1]<=bounds[3]):continue
                    if p in self.obstacles and p not in targets and p!=start:continue
                    if p in all_pin_nets and all_pin_nets[p]!={net}:continue
                    if here==start and here in pin_dirs and (dx,dy)!=pin_dirs[here]:continue
                    if p in targets and p in pin_dirs and (-dx,-dy)!=pin_dirs[p] and not occupied[p].get(net):continue
                    # No turning at a crossing, and no endpoint/T contact to
                    # another net. Straight orthogonal crossings have no dot.
                    foreign_here={k:v for k,v in occupied[here].items() if k!=net}
                    if foreign_here and old!=-1 and direction!=old:continue
                    foreign={k:v for k,v in occupied[p].items() if k!=net}
                    if foreign and (p in targets or any(axis in axes or len(axes)>1 for axes in foreign.values())):continue
                    extra=1+(0 if old in [-1,direction] else 2)+(7 if foreign else 0)
                    if net in occupied[p]:extra=.2
                    newcost=cost+extra;s=(p[0],p[1],direction)
                    if newcost<dist.get(s,1e99):
                        dist[s]=newcost;prev[s]=state;heapq.heappush(queue,(newcost+heuristic(p)*.2,newcost,s))
            if goal is None:
                detail={str(p):dict(obstacle=p in self.obstacles,pins=list(all_pin_nets.get(p,[])),wire={k:list(v) for k,v in occupied[p].items()}) for p in [(start[0]+dx,start[1]+dy) for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]]}
                raise RuntimeError(('Unroutable block',self.d.name,self.title,net,start,sorted(targets)[:8],detail))
            path=[]
            while goal!=initial:path.append((goal[0],goal[1]));goal=prev[goal]
            path.append(start);return path[::-1]

        # Small local nets first, ground last. Very large power trees otherwise
        # surround IC inputs and make signal paths unnecessarily long.
        order=sorted(endpoints,key=lambda n:(n in ['GND','+3V3','+5V_MOTION'],len(endpoints[n]),n))
        if hasattr(self,'manual_paths'):
            # The small IMU circuit has a hand-composed connector-to-sensor
            # signal flow. The same graph emitter supplies real T junctions.
            edges=defaultdict(set)
            endpoints=defaultdict(set)
            for xy,net,side in self.pins.values():
                if net is not None:endpoints[net].add(xy)
            assert set(self.manual_paths)==set(endpoints)
            for net,paths in self.manual_paths.items():
                for path in paths:
                    for a,b in zip(path,path[1:]):
                        a=tuple(round(v*2) for v in a);b=tuple(round(v*2) for v in b)
                        assert a[0]==b[0] or a[1]==b[1]
                        dx=0 if a[0]==b[0] else 1 if b[0]>a[0] else -1
                        dy=0 if a[1]==b[1] else 1 if b[1]>a[1] else -1
                        while a!=b:
                            nxt=(a[0]+dx,a[1]+dy);edges[net].add(tuple(sorted((a,nxt))));a=nxt
            order=[]
        for net in order:
            pts=set(endpoints[net])
            if len(pts)==1:
                # Single local flag-only net cannot happen in reviewed design.
                raise RuntimeError(('Unconnected block net',self.title,net,pts))
            tree={min(pts)};todo=pts-tree
            while todo:
                start=min(todo,key=lambda p:min(abs(p[0]-t[0])+abs(p[1]-t[1]) for t in tree))
                path=search(start,tree,net)
                for a,b in zip(path,path[1:]):
                    edges[net].add(tuple(sorted((a,b))))
                    axis=0 if a[1]==b[1] else 1
                    occupied[a].setdefault(net,set()).add(axis);occupied[b].setdefault(net,set()).add(axis)
                tree.update(path);todo-=tree
        segments=0;junctions=0
        for net,es in edges.items():
            graph=defaultdict(set)
            for a,b in es:graph[a].add(b);graph[b].add(a)
            actual_pins={xy for xy,pn,side in self.pins.values() if pn==net}
            protected=actual_pins|ports[net]
            # An already joined pin may leave an unused escape stub. Prune
            # only nonterminal leaves; never remove a pin or a named port.
            leaves=[p for p,adj in graph.items() if len(adj)==1 and p not in protected]
            while leaves:
                p=leaves.pop()
                if len(graph[p])!=1 or p in protected:continue
                other=next(iter(graph[p]));graph[p].clear();graph[other].remove(p)
                es.remove(tuple(sorted((p,other))))
                if len(graph[other])==1 and other not in protected:leaves.append(other)
            significant={p for p,adj in graph.items() if len(adj)!=2 or len({0 if n[1]==p[1] else 1 for n in adj})>1}
            # Each pin/port lies at a wire endpoint even when it taps a trunk.
            significant.update(endpoints[net])
            significant.update(actual_pins)
            remaining=set(es);net_segments=[]
            for p in sorted(significant):
                for nxt in sorted(graph[p]):
                    e=tuple(sorted((p,nxt)))
                    if e not in remaining:continue
                    remaining.remove(e);last=p;cur=nxt
                    while cur not in significant:
                        forward=next(n for n in graph[cur] if n!=last)
                        remaining.remove(tuple(sorted((cur,forward))));last,cur=cur,forward
                    self.d.line([(p[0]/2,p[1]/2),(cur[0]/2,cur[1]/2)]);segments+=1
                    net_segments.append((p,cur))
            assert not remaining, (net,len(remaining))
            for p,adj in graph.items():
                if len(adj)>=3 or (len(adj)==2 and p in actual_pins):
                    self.d.add(f'(junction (at {mm(p[0]/2)} {mm(p[1]/2)}) (diameter 1.016) (color 0 0 0 0) (uuid @UUID@))');junctions+=1
            if net not in shared:
                # One annotation on an existing wire preserves the established
                # PCB net name; it never replaces the local physical wiring.
                horizontal=[(a,b) for a,b in net_segments if a[1]==b[1]]
                candidates=horizontal or net_segments
                a,b=max(candidates,key=lambda ab:abs(ab[0][0]-ab[1][0])+abs(ab[0][1]-ab[1][1]))
                px,py=min(a,b)
                self.d.add(f'(label {q(net)} (at {mm(px/2)} {mm(py/2)} 0) {effects(.9,"left bottom")} (uuid @UUID@))')
        self.d.stats.append(dict(title=self.title,references=self.refs,wires=segments,junctions=junctions,inter_block_labels=len(shared),local_nets=len(endpoints)-len(shared)))


def icpins(left=(), right=(), top=(), bottom=(), w=16,h=14):
    p={}
    for side,items in [('L',left),('R',right),('T',top),('B',bottom)]:
        for i,pn in enumerate(items):
            if pn is None:continue
            offset=(i-(len(items)-1)/2)*2
            p[str(pn)]=(-w/2-2,offset,side) if side=='L' else (w/2+2,offset,side) if side=='R' else (offset,-h/2-2,side) if side=='T' else (offset,h/2+2,side)
    return p


def imu(d):
    d.paper='A4'
    d.text('MORI BODY IMU | FUNCTIONAL CIRCUIT',6,7,2)
    d.text('S2 drawing | same pin map and PCB | PROTOTYPE / UNVALIDATED',6,11,1.1)
    b=d.block('01  SPI connector / sensor / local decoupling',5,16,105,49,'Body-fixed IMU. Axis transform and assembled pin-1 orientation still require verification.')
    b.place('J1',17,25,orient='r')
    pins=icpins(left=[13,14,1,12,4],right=[],top=[5,8],bottom=[2,3,6,7,9,10,11],w=20,h=16)
    b.place('U1',58,26,pins=pins,w=20,h=16,caption_at=(68,14))
    b.place('R1',30,26,orient='hr')
    b.place('R2',42,17,orient='vu')
    for ref,x in [('C1',80),('C2',89),('C3',98)]:b.place(ref,x,22,orient='v')
    # These are real PWR_FLAG boundary declarations, not extra supplies.
    b.place('#FLG1',30,10);b.place('#FLG2',92,34)
    b.manual_paths={
        '+3V3': [[(25,34),(27,34),(27,28),(103,28)],[(62,32),(62,28)],[(64,32),(64,28)],[(47,30),(47,28)]]+[[ (x,35),(x,28)] for x in [85,94,103]],
        'GND': [[(25,36),(26,36),(26,56),(103,56)],[(25,48),(26,48)],[(97,52),(97,56)]]+[[ (x,52),(x,56)] for x in [57,59,61,63,65,67,69]]+[[ (x,41),(x,56)] for x in [85,94,103]],
        'SCK': [[(25,38),(51,38)]],
        'MOSI': [[(25,40),(51,40)]],
        'MISO': [[(25,42),(32,42)]],
        'MISO_IC': [[(38,42),(51,42)]],
        'CS_N': [[(25,44),(51,44)],[(47,36),(47,44)]],
        'DRDY': [[(25,46),(51,46)]],
    }
    b=d.block('02  Mechanical references',5,69,50,10)
    b.place('H1',17,7);b.place('H2',37,7)


def motion(d):
    d.text('MORI MOTION CARRIER | FUNCTIONAL CIRCUIT',6,7,2.8)
    d.text('P1-S1 drawing revision. Four actuators remain external. Labels connect blocks; solid wires show each local circuit.',6,11,1.3)
    b=d.block('01  Motion MCU module / accessible top-side SWD',5,15,82,133,'WeAct F412RET6 V1.1 adaptation. NC means this carrier does not wire that pad.')
    c=d.parts['U100'];active=[pn for pn,p in c['pins'].items() if p['net'] and p['net'] not in ['GND','+3V3','+5V_MOTION']]
    nc=[pn for pn,p in c['pins'].items() if p['net'] is None]
    power=[pn for pn,p in c['pins'].items() if p['net'] in ['+3V3','+5V_MOTION']]
    ground=[pn for pn,p in c['pins'].items() if p['net']=='GND']
    # Functional ordering is deliberately different from connector numbering;
    # the real A/B/C/D/E pad number and GPIO are printed on every pin.
    active.sort(key=lambda pn:({'S288':0,'HEAD':1,'LINK':2,'IMU':3,'ARM':4,'CLR':5,'NRST':5,'FAULT':5,'CHG':5,'BAT':6,'WHEEL':6,'CURRENT':6,'USER':7}.get(c['pins'][pn]['net'].split('_')[0],8),c['pins'][pn]['net']))
    pins=icpins(left=nc,right=active,top=power,bottom=ground,w=35,h=91)
    b.place('U100',42,65,pins=pins,w=35,h=91,short='WeAct F412RET6 / 64Pin V1.1')
    b=d.block('02  Physical enable / reset supervisor / ARM latch',89,15,116,71,'Clear dominates. Fault recovery requires a new ARM edge; supervisor is not a firmware watchdog.')
    b.place('J8',24,17,orient='r');b.place('R6',14,17,orient='v')
    b.place('U6',24,43,pins=icpins(right=[2],top=[3],bottom=[1],w=12,h=10),w=12,h=10)
    b.place('U5',67,32,pins=icpins(left=[2,1,6,7],right=[5,3],top=[8],bottom=[4],w=16,h=16),w=16,h=16)
    b.place('R5',45,46,orient='v');b.place('R7',45,58,orient='v')
    b.place('C12',58,57,orient='v');b.place('C5',86,49,orient='v');b.place('C6',24,58,orient='v')
    for ref,y in [('D1',16),('D2',28),('D3',40)]:b.place(ref,98,y,kind='schottky')
    b.place('R19',82,61)
    b=d.block('03  Gated half-duplex wheel interface',207,15,118,48,'S288 DATA only. Motor current returns on the power PCB; electrical levels still require bench verification.')
    b.place('U1',44,25,pins=icpins(left=[1,2,3],right=[6,5],top=[8],bottom=[7,4],w=18,h=14),w=18,h=14)
    b.place('R1',68,24);b.place('J2',92,25);b.place('C1',43,40,orient='v')
    b=d.block('04  Gated half-duplex head interface',207,65,118,48,'SCS0009 chain. Two position servos; data connector J3.3 intentionally unwired.')
    b.place('U2',44,25,pins=icpins(left=[1,2,3],right=[6,5],top=[8],bottom=[7,4],w=18,h=14),w=18,h=14)
    b.place('R2',68,24);b.place('J3',92,25);b.place('C2',43,40,orient='v')
    b=d.block('05  Output-enable interlock logic',89,88,116,43,'OE_N = request_N OR ARM_Q_N. Pull-ups default both transmitters to disabled.')
    b.place('U3',64,23,pins=icpins(left=[1,2,5,6],right=[7,3],top=[8],bottom=[4],w=18,h=16),w=18,h=16)
    b.place('R3',30,19,orient='v');b.place('R4',43,19,orient='v');b.place('C3',87,23,orient='v')
    b=d.block('06  Body IMU / series damping / CS pull-up',207,115,118,45,'SPI and DRDY are body-mounted. Data-ready timing and axis transform are software/bench gates.')
    b.place('J4',94,24)
    for ref,y in [('R10',13),('R11',22),('R12',31)]:b.place(ref,48,y)
    b.place('R13',73,20,orient='v')
    b=d.block('07  Interaction MCU / isolated UART power domains',89,133,116,48,'CAM J11.3 supplies only VCCB. TXU0202 isolation protects the link when one logic domain is off.')
    b.place('U4',48,25,pins=icpins(left=[5,4,6],right=[8,1],top=[3,7],bottom=[2],w=18,h=14),w=18,h=14)
    b.place('R9',74,23);b.place('J5',94,24);b.place('C4',31,38,orient='v');b.place('C7',65,38,orient='v')
    b=d.block('08  Power-board control / ADC input filters',207,162,118,58,'RC: 1k / 10nF. Fault/charge are active-low. ADC scaling is on the power PCB.')
    b.place('J7',28,28,orient='r')
    for ref,cap,y in [('R14','C9',20),('R15','C10',33),('R16','C11',46)]:
        b.place(ref,58,y);b.place(cap,75,y+2,orient='v')
    b.place('R17',91,16,orient='v');b.place('R18',103,36,orient='v')
    b=d.block('09  Logic input / function button / board mounting',5,150,82,70,'J6 is a function button, not the emergency-stop loop. No motor supply current flows through J1.')
    b.place('J1',21,19,orient='r');b.place('C8',43,21,orient='v')
    b.place('J6',23,43,orient='r');b.place('R8',43,42,orient='v')
    for ref,x,y in [('#FLG1',63,20),('#FLG2',63,35),('#FLG3',63,50)]:b.place(ref,x,y)
    for i in range(1,5):b.place('H'+str(i),9+i*15,62)
    d.text('PROTOTYPE / UNVALIDATED. Electrical connectivity, values, pad numbers and routed PCB are unchanged by this drawing revision.',91,199,1.4)
    d.text('Schematic review: follow solid wires inside each numbered block. Identical labels link blocks on this sheet.',91,204,1.2)
    d.text('Do not use MCU reset as a routine stop while balancing. Bench / thermal / motor / battery tests remain NOT_TESTED.',91,209,1.2)


def power(d):
    d.text('MORI POWER CONDITIONER | FUNCTIONAL CIRCUIT',6,7,2.8)
    d.text('P1-S1 drawing revision. Protected 3S pack and buck converters are external. This board does not implement USB-C charging.',6,11,1.3)
    b=d.block('01  Pack input / reverse protection / discharge current',5,15,104,69,'J1 is downstream of the external fuse/master. INA180 measures discharge current only: nominal 0.2 V/A.')
    b.place('J1',15,20,orient='r');b.place('Q1',38,20,kind='pmos');b.place('R2',66,20,short='10mR / 1% / 1W')
    b.place('D1',38,36,kind='zener',orient='v');b.place('R1',22,49,orient='v')
    b.place('U1',68,49,pins=icpins(left=[3,4],right=[1],top=[5],bottom=[2],w=14,h=10),w=14,h=10)
    b.place('R3',56,33,orient='v');b.place('R4',79,33,orient='v')
    b.place('C1',87,50,orient='v');b.place('C2',92,20,orient='v')
    for base,prefix,x,title in [(10,'W',111,'02  Wheel rail / reverse blocking / hardware power enable'),(30,'H',218,'03  Head rail / reverse blocking / hardware power enable')]:
        b=d.block(title,x,15,105,69,'PMOS power gate follows ARM_Q. 1000uF reservoir has no qualified soft start; inrush / heat remain NOT_TESTED.')
        b.place('J3' if base==10 else 'J5',15,19,orient='r')
        b.place('D'+str(base),36,18,kind='schottky',orient='hr')
        b.place('Q'+str(base),59,18,kind='pmos')
        b.place('R'+str(base),46,33,orient='v');b.place('R'+str(base+1),59,38,orient='v')
        b.place('Q'+str(base+1),59,54,kind='nmos')
        b.place('C'+str(base),81,36,kind='cp',orient='v',short='1000u / 16V')
        if base==10:
            b.place('J7',94,21);b.place('J8',94,49);b.place('J13',22,51,orient='r')
        else:
            b.place('J9',94,24);b.place('J14',22,51,orient='r')
    b=d.block('04  External buck input distribution',5,86,104,47,'Connectors are boundaries only; buck converters, finished pack, 3S charger and USB-C negotiation are external.')
    b.place('J2',25,20,orient='r');b.place('J4',51,20,orient='r');b.place('J6',79,20,orient='r',short='LOGIC BUCK VIN')
    b.d.text('J2 -> 9V buck -> J3    |    J4 -> 6V buck -> J5',b.x+10,b.y+34,1.2)
    b.d.text('J6 -> separate motion / interaction 5V converters',b.x+10,b.y+39,1.2)
    for base,prefix,x,title in [(20,'W',111,'05  Wheel regenerative clamp / overvoltage fault'),(40,'H',218,'06  Head regenerative clamp / overvoltage fault')]:
        b=d.block(title,x,86,105,87,'Rail-powered analog circuit. R-dump is external; resistor pulse energy and clamp dynamics are not qualified.')
        b.place('U'+str(base),60,42,pins=icpins(left=[3,2,5,6],right=[1,7],top=[8],bottom=[4],w=18,h=16),w=18,h=16)
        b.place('U'+str(base+1),24,39,pins=icpins(left=[2],top=[1],bottom=[3],w=8,h=8),w=8,h=8)
        b.place('R'+str(base),24,21,orient='v')
        b.place('R'+str(base+1),42,19,orient='v');b.place('R'+str(base+2),42,57,orient='v')
        b.place('R'+str(base+3),65,17)
        b.place('R'+str(base+4),82,21,orient='v')
        b.place('R'+str(base+5),27,62,orient='v');b.place('R'+str(base+6),27,77,orient='v')
        b.place('C'+str(base),61,70,orient='v');b.place('C'+str(base+1),42,75,orient='v')
        b.place('Q'+str(base),85,46,kind='nmos')
        b.place('D'+str(base),85,67,kind='zener',orient='v')
        b.place('J11' if base==20 else 'J12',93,13,short='DUMP 5R6 / 5W' if base==20 else 'DUMP 10R / 5W')
    b=d.block('07  Voltage dividers / motion-board control connector',5,135,104,85,'Nominal dividers 100k / 27k. Motion PCB adds 1k / 10nF filtering. Connector pin numbering is board-side.')
    b.place('J10',77,34)
    b.place('R50',24,22,orient='v');b.place('R51',24,39,orient='v')
    b.place('R52',45,22,orient='v');b.place('R53',45,39,orient='v')
    b.place('R54',52,63,orient='v')
    for ref,x,y in [('#FLG1',21,66),('#FLG2',35,66),('#FLG3',70,66),('#FLG4',83,66),('#FLG5',93,66)]:b.place(ref,x,y)
    b=d.block('08  Charger-present / insertion interlock',111,175,105,45,'VBUS sense only: no CC, PD, CC/CV or cell balancing. An open J15 wire is not inherently fail-safe.')
    b.place('J16',16,21,orient='r');b.place('R55',38,20);b.place('Q50',62,21,kind='npn')
    b.place('R56',44,34,orient='v');b.place('J15',88,21)
    b=d.block('09  Mounting / release boundaries',218,175,105,45)
    for i in range(1,5):b.place('H'+str(i),6+i*21,13)
    b.d.text('PCB: 80 x 45 mm. Largest capacitor: 16 mm high.',b.x+5,b.y+24,1.2)
    b.d.text('Old power allocation does not fit this prototype.',b.x+5,b.y+29,1.2)
    b.d.text('PROTOTYPE / UNVALIDATED. No fabrication release.',b.x+5,b.y+35,1.3)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('projects',nargs='*')
    args=parser.parse_args()
    results=[]
    for name in args.projects or ['MORI_motion_P1','MORI_imu_P1','MORI_power_P1']:
        results.append(render_project(name))
        print(name,'functional layout written',flush=True)
    out=ROOT/'reports/functional_schematic';out.mkdir(exist_ok=True)
    (out/'layout.json').write_text(json.dumps(results,indent=2)+'\n')


def render_project(name):
    import readable_schematic
    d=Drawing(name)
    {'motion':readable_schematic.motion,'imu':imu,'power':readable_schematic.power}[name.split('_')[1]](d)
    return d.finish()


if __name__=='__main__':main()
