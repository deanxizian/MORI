"""Current-source move screens for the other four signal reference transitions.

The HEAD_OE screen is already recorded separately; HEAD_VM is a power transfer
and is not treated as a freely movable signal hole. Every touching segment is
explicitly inventoried. No PCB is saved or original connectivity waived.
"""
import json,math,sys
from pathlib import Path
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R185-other-reference-moves.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
prior=json.loads(Path('robot/hardware/driver/development/evidence/R181C/regression.json').read_text());assert prior['board_sha256']==c.sha
flags=[r for r in prior['reference_transitions'] if r['status']=='FAIL' and r['net'] not in ['/HEAD_VM','/01 {slash} Core/HEAD_OE_REQ_N']];assert len(flags)==4
gnd=[o for o in c.anchors('GND') if all((uid(o),ly) in c.shapes and c.shapes[uid(o),ly].intersects(c.copper['GND',ly]) for ly in ['In1.Cu','In4.Cu'])]
power=unary_union([g for n,ly,g in c.fills if n!='GND']);rows=[]
for flag in flags:
    v=c.by_id[flag['uuid']];net=v.GetNetname();old=xy(v.GetPosition())
    touched=[t for t in c.segments if t.GetNetname()==net and c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersects(c.shapes[uid(v),c.board.GetLayerName(t.GetLayer())])]
    retired={uid(t) for t in touched};omit=retired|{uid(v)};obstacles=[]
    for (u,ly),s in c.shapes.items():
        o=c.by_id[u]
        if u in omit:continue
        if isinstance(o,pcb.PAD) or o.GetNetname()!=net:obstacles.append(s.buffer(.457))
        elif isinstance(o,pcb.PCB_VIA):obstacles.append(Point(xy(o.GetPosition())).buffer(.607))
    obstacles.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
    obstacles.extend(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0)
    physical=prep(unary_union(obstacles));referenced=[]
    for t in c.segments:
        ly=c.board.GetLayerName(t.GetLayer())
        if uid(t) not in retired and ly in REFERENCE:referenced.append(c.shapes[uid(t),ly].intersection(c.copper['GND',REFERENCE[ly]]))
    refguard=prep(unary_union(referenced).buffer(.657));candidates=[];reject=dict(physical=0,reference=0,too_far=0)
    for ix in range(max(16,math.ceil((old[0]-1.5)*20)),min(1384,math.floor((old[0]+1.5)*20))+1):
        for iy in range(max(16,math.ceil((old[1]-1.5)*20)),min(684,math.floor((old[1]+1.5)*20))+1):
            q=(ix/20,iy/20);pt=Point(q)
            if math.dist(q,old)<.001 or math.dist(q,old)>1.5:continue
            nearest=min(math.dist(q,xy(o.GetPosition())) for o in gnd)
            if nearest>1.95:reject['too_far']+=1;continue
            if physical.intersects(pt):reject['physical']+=1;continue
            if refguard.intersects(pt):reject['reference']+=1;continue
            candidates.append(dict(position_mm=list(q),displacement_mm=math.dist(q,old),nearest_dual_plane_GND_mm=nearest,power_antipad_projection_mm2=pt.buffer(.657).intersection(power).area))
    candidates.sort(key=lambda r:(r['power_antipad_projection_mm2'],r['displacement_mm']))
    row=dict(net=net,signal_uuid=uid(v),source_via=via_snapshot(c.board,v),retired_segments=[dict(uuid=uid(t),net=net,layer=c.board.GetLayerName(t.GetLayer()),start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())),width_mm=t.GetWidth()/1e6) for t in touched],
             candidate_count=len(candidates),candidates=candidates[:60],rejections=reject)
    rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ['retired_segments','candidates','source_via']}|{'best':candidates[:3]}),flush=True)
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,grid_mm=.05,search_radius_mm=1.5,signals=rows,adopted=False),indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
