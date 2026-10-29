"""Compare relocating the UV output transistor near the detector group.
Native pad/face/rotation geometry is kept. Ground vias, fixed courtyards and
through-hole contacts are hard constraints; conflicting non-ground copper is
listed for explicit joint rerouting, not silently removed or accepted.
"""
import ast,json,sys
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.strtree import STRtree
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *

b=Path('robot/.state/c3-completion/trials');out=b/'R165-output-stage-placement.json';assert not out.exists()
c=Copper(b/'R165C/MORI_Interface_C3.kicad_pcb');face='B.Cu';lid=c.ids[face]
fs={f.GetReference():f for f in c.footprints};moving={'Q1301','R1308'}
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fixed=[f for f in c.footprints if f.GetReference() not in moving]
for f in fixed:f.BuildCourtyardCaches()
courtyards=unary_union([polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in fixed if f.GetLayer()==lid])
fixedpads=[p for f in fixed for p in f.Pads() if p.IsOnLayer(lid)]
pth=unary_union([shape(p,lid) for p in fixedpads if p.GetAttribute()==pcb.PAD_ATTRIB_PTH])
ground=unary_union([shape(v,lid) for v in c.vias if v.GetNetname()=='GND'])
nets={p.GetNetname() for p in fs['Q1301'].Pads()}
padblock={net:unary_union([shape(p,lid) for p in fixedpads if p.GetNetname()!=net]).buffer(.199999) for net in nets}
tracks=[t for t in c.tracks if t.GetNetname()!='GND' and (uid(t),face) in c.shapes]
shapes=[c.shapes[uid(t),face] for t in tracks];tree=STRtree(shapes)
rows=[];tested=0
for angle in [0,90,180,270]:
    f=pcb.FOOTPRINT(fs['Q1301']);f.SetPosition(pcb.VECTOR2I(0,0));f.SetOrientationDegrees(angle);f.BuildCourtyardCaches()
    cy0=polyset(f.GetCourtyard(pcb.B_CrtYd));body0=fab(f)
    ps0=[(p.GetNumber(),p.GetNetname(),shape(p,lid),xy(p.GetPosition())) for p in f.Pads()]
    for ix in range(216,269):
        x=ix*.25
        for iy in range(60,104):
            y=iy*.25;tested+=1
            cy=translate(cy0,x,y)
            if cy.intersection(courtyards).area>1e-8 or cy.intersects(pth):continue
            body=translate(body0,x,y)
            if body.intersection(ground).area>1e-8:continue
            pads=[(n,net,translate(s,x,y),(pt[0]+x,pt[1]+y)) for n,net,s,pt in ps0]
            if not box(.505,.505,69.495,34.495).covers(unary_union([s for n,net,s,pt in pads])):continue
            if any(s.intersects(padblock[net]) or s.distance(ground)<.2-1e-6 for n,net,s,pt in pads):continue
            pending=[]
            env=unary_union([body]+[s.buffer(.201) for n,net,s,pt in pads])
            for idx in tree.query(env):
                t=tracks[idx];sh=shapes[idx];via=isinstance(t,pcb.PCB_VIA)
                if body.intersection(sh).area>1e-8 or any((via or net!=t.GetNetname()) and s.distance(sh)<.2-1e-6 for n,net,s,pt in pads):
                    pending.append({'uuid':uid(t),'net':t.GetNetname(),'via':via})
            source=next(pt for n,net,s,pt in pads if n=='2')
            drain=next(pt for n,net,s,pt in pads if n=='3')
            gate=next(pt for n,net,s,pt in pads if n=='1')
            distance=Point(source).distance(Point(64.0625,28.85))+Point(drain).distance(Point(67.45,28.35))+Point(gate).distance(Point(69.15,16.525))
            rows.append({'reference':'Q1301','face':face,'position_mm':[x,y],'rotation_deg':angle,
                'pads':[{'number':n,'net':net,'position_mm':pt} for n,net,s,pt in pads],
                'pending_non_ground_copper':pending,'endpoint_distance_sum_mm':distance,
                'score':len(pending)*5+distance})
rows.sort(key=lambda r:r['score'])
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'tested':tested,'candidate_count':len(rows),
    'candidates':rows,'paired_resistor_placement':'NOT_TESTED','routing':'NOT_TESTED','adopted':False},indent=2)+'\n')
print(json.dumps({'tested':tested,'candidate_count':len(rows),'best':rows[:12]}),flush=True)
