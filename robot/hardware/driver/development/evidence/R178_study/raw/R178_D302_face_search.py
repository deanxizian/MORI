"""Native D302 placement/access comparison on both outer faces, read only.

All fixed interfaces and native copper remain. Explicitly screen PTH/assembly,
mount envelopes and actual exposed-pad mask margins before native trial builds.
Moving the diode to the front is a comparison, not package/pin substitution.
Source is the exact R177A preparation, whose five CLR removals are reproduced
from accepted R168G if a candidate is built. No board is saved by this script.
"""
import ast,collections,json,math,sys,time
from pathlib import Path
import numpy as np
from shapely.affinity import translate,rotate,scale
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import mask

b=Path('robot/.state/c3-completion/trials');out=b/'R178-D302-face-search.json';assert not out.exists()
base=(b/'R177_D302_pose_access.py').read_text().split('rows=[];rejects=',1)[0]
base=base.replace("out=b/'R177-D302-pose-access.json'", "out=b/'R178-D302-face-search.json'")
base=base.replace("reachable=lookup[labels[0]]&free[0]", "reach_by_face={ly:lookup[labels[i]]&free[i] for i,ly in enumerate(p.layers) if ly in ['F.Cu','B.Cu']}")
old="net='/FAULT_N';free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)"
assert base.count(old)==1
new=old+"\ninductor=fab(next(o for o in c.footprints if o.GetReference()=='L701'))\nblocked=[ob.union(inductor.buffer(.102)) for ob in blocked]"
base=base.replace(old,new)
contexts={}
for net,target in [('/FAULT_N','Q1701.3'),('/CLR_N','U303.2')]:
    code=base.replace("net='/FAULT_N';",'net='+repr(net)+';').replace("if 'Q1701.3' in g['pads']",'if '+repr(target)+" in g['pads']")
    ns={};exec(compile(code,str(__file__)+':relaxed_geometry','exec'),ns);contexts[net]=ns
ns=contexts['/FAULT_N'];p=ns['p'];c=ns['c'];original=ns['original'];origin=ns['origin'];guard=ns['guard'];fab=ns['fab'];outline=ns['outline']
assert original.GetFPIDAsString()=='C3_Packages:D_SOD-323' and original.GetValue()=='BAT54WS-7-F'
mount=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_')])
env={}
for face in ['B.Cu','F.Cu']:
    lid=c.ids[face];silkid=pcb.B_SilkS if face=='B.Cu' else pcb.F_SilkS;yardid=pcb.B_CrtYd if face=='B.Cu' else pcb.F_CrtYd;maskid=pcb.B_Mask if face=='B.Cu' else pcb.F_Mask
    env[face]=dict(
        body=unary_union([fab(f) for f in c.footprints if f.GetLayer()==lid]),
        yard=unary_union([outline(f,yardid) for f in c.footprints if f.GetLayer()==lid]),
        silk=unary_union([shape(g,silkid) for f in c.footprints for g in f.GraphicalItems() if isinstance(g,pcb.PCB_SHAPE) and g.GetLayer()==silkid]),
        exposed=unary_union([shape(q,lid).buffer(q.GetSolderMaskExpansion(lid)/1e6) for q in c.pads if q.IsOnLayer(maskid)]),
        pth=unary_union([shape(q,lid) for q in c.pads if q.GetAttribute()==pcb.PAD_ATTRIB_PTH]),
        vias=unary_union([c.shapes[uid(v),face] for v in c.vias]),
        tracks=unary_union([c.shapes[uid(t),face] for t in c.segments if t.GetLayer()==lid]),
        foreign={net:unary_union([s for (u,ly),s in c.shapes.items() if ly==face and c.by_id[u].GetNetname()!=net]) for net in ['/FAULT_N','/CLR_N']},
        pad_keepout=unary_union([polyset(z.Outline()) for z in c.zones if z.GetIsRuleArea() and z.IsOnLayer(lid) and z.GetDoNotAllowPads() and not z.GetZoneName().startswith('BODY_D302_')]))
rows=[];rejects=collections.Counter();start=time.monotonic()
for face in ['B.Cu','F.Cu']:
    ff=pcb.FOOTPRINT(original);g=guard;angle0=ff.GetOrientationDegrees()
    if face!=c.board.GetLayerName(ff.GetLayer()):
        ff.Flip(ff.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT);g=scale(g,xfact=-1,yfact=1,origin=origin);angle0=ff.GetOrientationDegrees()
    for angle in [0,90,180,270]:
        part=pcb.FOOTPRINT(ff);part.SetOrientationDegrees(angle);lid=c.ids[face]
        body=fab(part);yard=outline(part,pcb.B_CrtYd if face=='B.Cu' else pcb.F_CrtYd)
        silk=unary_union([shape(item,pcb.B_SilkS if face=='B.Cu' else pcb.F_SilkS) for item in part.GraphicalItems() if isinstance(item,pcb.PCB_SHAPE) and item.GetLayer()==(pcb.B_SilkS if face=='B.Cu' else pcb.F_SilkS)])
        gg=rotate(g,-(angle-angle0),origin=origin)
        pads={q.GetNumber():(q.GetNetname(),shape(q,lid),xy(q.GetPosition())) for q in part.Pads()}
        for xi in range(6,275):
            for yi in range(6,135):
                pos=xi/4,yi/4;dx=pos[0]-origin[0];dy=pos[1]-origin[1]
                bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy)
                if not box(.3,.3,69.7,34.7).covers(ya):rejects[face+':board_margin']+=1;continue
                if ya.intersection(env[face]['yard']).area>1e-8 or bo.intersection(env[face]['body']).area>1e-8:rejects[face+':part_envelope']+=1;continue
                if ya.intersection(env[face]['pth']).area>1e-8:rejects[face+':PTH_courtyard']+=1;continue
                if bo.intersection(mount).area>1e-8:rejects[face+':mount_projection']+=1;continue
                si=translate(silk,xoff=dx,yoff=dy)
                if si.distance(env[face]['silk'])<.05 or si.distance(env[face]['exposed'])<.01:rejects[face+':native_silk_or_mask']+=1;continue
                gd=translate(gg,xoff=dx,yoff=dy)
                if gd.intersection(env[face]['vias']).area>1e-8:rejects[face+':native_via_guard']+=1;continue
                actual={pin:(net,translate(s,xoff=dx,yoff=dy),(pp[0]+dx,pp[1]+dy)) for pin,(net,s,pp) in pads.items()}
                if any(s.distance(env[face]['vias'])<.1999996-1e-9 or s.distance(env[face]['foreign'][net])<.1999996-1e-9 or s.intersection(env[face]['pad_keepout']).area>1e-8 for net,s,pp in actual.values()):rejects[face+':pad_clearance_or_keepout']+=1;continue
                lands=unary_union([s for net,s,pp in actual.values()])
                if gd.intersection(env[face]['tracks']).area>1e-8 or bo.difference(lands).intersection(env[face]['tracks']).area>1e-8:rejects[face+':retained_tracks']+=1;continue
                access={}
                for pin,(net,land,point) in actual.items():
                    x0,y0,x1,y1=land.bounds;xs=np.where((p.xs>=x0)&(p.xs<=x1))[0];ys=np.where((p.ys>=y0)&(p.ys<=y1))[0]
                    access[pin]=int((mask(land.buffer(-.001),p.xx[np.ix_(ys,xs)],p.yy[np.ix_(ys,xs)],True)&contexts[net]['reach_by_face'][face][np.ix_(ys,xs)]).sum())
                rows.append(dict(face=face,position_mm=pos,rotation_deg=angle,pads={pin:dict(net=n,position_mm=point) for pin,(n,s,point) in actual.items()},optimistic_access_cells=access,both_access=all(access.values()),displacement_mm=math.dist(pos,(25.75,7.5))))
rows.sort(key=lambda r:(not r['both_access'],r['displacement_mm'],r['face'],r['rotation_deg']))
result=dict(scope=__doc__,source_sha256=c.sha,canonical_source_sha256='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e',position_grid_mm=.25,route_grid_mm=.05,bounds_mm=[1.5,1.5,68.5,33.5],candidates=rows,rejections=dict(rejects),elapsed_seconds=time.monotonic()-start,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(candidate_count=len(rows),by_face=dict(collections.Counter(r['face'] for r in rows)),both_access_by_face=dict(collections.Counter(r['face'] for r in rows if r['both_access'])),best=[r for r in rows if r['both_access']][:12],seconds=result['elapsed_seconds'])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
