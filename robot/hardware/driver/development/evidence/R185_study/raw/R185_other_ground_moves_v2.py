"""Screen nearest original GND-via relocations for unresolved transitions.

Omit only the selected via and explicit terminal GND segments from obstacles.
Candidate counts are physical/refill planning only. Full annulus containment in the OLD ground fill is not required; positive prospective contact is screened, with actual refilled plane contacts mandatory. The prior full-containment screen was overly conservative, not a native rule. Attached returns must be
rebuilt and full canonical connectivity, power and reference checks must pass.
"""
import json,math,sys
from pathlib import Path
from shapely.geometry import box
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R185-other-ground-moves-v2.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
audit=json.loads(Path('robot/hardware/driver/development/evidence/R181C/regression.json').read_text())
flags=[r for r in audit['reference_transitions'] if r['status']=='FAIL'];rows=[]
ground_planes=[c.copper['GND',ly] for ly in ['In1.Cu','In4.Cu']]
edge=box(.755,.755,69.245,34.245)
gnd=[o for o in c.anchors('GND') if all((uid(o),ly) in c.shapes and c.shapes[uid(o),ly].intersects(c.copper['GND',ly]) for ly in ['In1.Cu','In4.Cu'])]
power=unary_union([g for net,ly,g in c.fills if net!='GND'])
for f in flags:
    if f['uuid']=='2ceba827-433b-44de-af01-ce89cb121093':continue
    v=c.by_id[f['nearest_ground_uuid']];old=xy(v.GetPosition());sp=tuple(f['position_mm'])
    assert v.GetNetname()=='GND'
    attached=[t for t in c.segments if t.GetNetname()=='GND' and (math.dist(xy(t.GetStart()),old)<.001 or math.dist(xy(t.GetEnd()),old)<.001)]
    omit={uid(v)}|{uid(t) for t in attached};obs=[]
    for (u,ly),s in c.shapes.items():
        if u in omit:continue
        o=c.by_id[u]
        if isinstance(o,pcb.PAD) or o.GetNetname()!='GND':obs.append(s.buffer(.455))
        elif isinstance(o,pcb.PCB_VIA):obs.append(Point(xy(o.GetPosition())).buffer(.705))
    obs.extend(k['shape'].buffer(.255) for k in c.keepouts if k['vias'])
    obs.extend(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.555) for p in c.pads if max(xy(p.GetDrillSize()))>0)
    blocked=prep(unary_union(obs));oldvoid=Point(old).buffer(.655);candidates=[]
    served=[r for r in audit['reference_transitions'] if r['status']=='PASS' and r.get('nearest_ground_uuid')==uid(v)]
    for ix in range(math.ceil((sp[0]-1.95)*40),math.floor((sp[0]+1.95)*40)+1):
        for iy in range(math.ceil((sp[1]-1.95)*40),math.floor((sp[1]+1.95)*40)+1):
            q=(ix/40,iy/40);pt=Point(q)
            if not .705<=math.dist(q,sp)<=1.95 or not .001<math.dist(q,old)<=1.8 or blocked.intersects(pt) or not edge.contains(pt) or any(g.intersection(pt.buffer(.25)).area<=1e-8 for g in ground_planes):continue
            distances=[min([math.dist(q,r['position_mm'])]+[math.dist(xy(g.GetPosition()),r['position_mm']) for g in gnd if uid(g)!=uid(v)]) for r in served]
            if any(d>2 for d in distances):continue
            candidates.append(dict(position_mm=q,signal_distance_mm=math.dist(q,sp),displacement_mm=math.dist(q,old),
                                   new_power_projection_mm2=pt.buffer(.655).difference(oldvoid).intersection(power).area))
    candidates.sort(key=lambda r:(r['new_power_projection_mm2'],r['displacement_mm']))
    row=dict(signal_net=f['net'],signal_uuid=f['uuid'],signal_position_mm=sp,ground_uuid=uid(v),source_via=via_snapshot(c.board,v),
             attached_tracks=[dict(uuid=uid(t),net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=xy(t.GetStart()),end_mm=xy(t.GetEnd())) for t in attached],
             served_pass_transitions=served,candidate_count=len(candidates),candidates=candidates)
    rows.append(row);print(json.dumps(dict(net=f['net'],count=len(candidates),best=candidates[:2])),flush=True)
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,grid_mm=.025,results=rows,adopted=False),indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
