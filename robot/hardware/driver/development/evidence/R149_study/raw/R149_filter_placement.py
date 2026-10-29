"""Compare front-face RC placements near the new U1001 escape, including both signal access and capacitor ground.

Read-only optimistic grid screen on unadopted C. New bodies and native refill
must still be checked together; no placement or route here is accepted.
"""
import ast,json,math,sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely import contains_xy,intersects_xy
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
from shapely.strtree import STRtree
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R149-filter-placement.json';assert not out.exists()
p=Planner(str(b/'R149C/MORI_Interface_C3.kicad_pcb'),.05,['F.Cu','In3.Cu','B.Cu','In2.Cu'],.2);c=p.c
def load_function(path,name):
    n=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[n],type_ignores=[]),name,'exec'),globals())
load_function(b/'R138_joint_search.py','fab')
moving={'R1102','C1102'}
bodies={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly and f.GetReference() not in moving]) for ly in ['F.Cu','B.Cu']}
metrics=[]
load_function(b/'R143A_U303_placement.py','reachable')
access={'/ACT_CURRENT_FILTERED':reachable('/ACT_CURRENT_FILTERED','U1001.9'),'Net-(U1101-OUT)':reachable('Net-(U1101-OUT)','U1101.1'),'GND':mask(c.copper[('GND','F.Cu')],p.xx,p.yy,True)}
others=[polyset(f.GetCourtyard(pcb.F_CrtYd)) for f in c.footprints if f.GetLayer()==pcb.F_Cu and f.GetReference() not in moving]
others=[g for g in others if not g.is_empty]
others += [k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'F.Cu' in k['layers']]
via=prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly=='F.Cu' and isinstance(c.by_id[u],pcb.PCB_VIA)]))
all_tracks=unary_union([c.shapes[uid(t),'F.Cu'] for t in c.segments if t.GetLayer()==pcb.F_Cu])
xs,ys=np.arange(22,48.001,.1),np.arange(5.8,9.001,.1);xx,yy=np.meshgrid(xs,ys)
positions={};geometries={}
for ref in sorted(moving):
    f=next(f for f in c.footprints if f.GetReference()==ref);origin=xy(f.GetPosition());oldangle=f.GetOrientationDegrees();court=polyset(f.GetCourtyard(pcb.F_CrtYd));body=fab(f);pads=list(f.Pads());mine={uid(q) for q in pads}
    obstacles={q.GetNetname():prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly=='F.Cu' and u not in mine and c.by_id[u].GetNetname()!=q.GetNetname()])) for q in pads}
    rows=[];shapes=[]
    for angle in [0,90,180,270]:
        rot=rotate(court,-(angle-oldangle),origin=origin);x0,y0,x1,y1=rot.bounds;hx,hy=(x1-x0)/2+.005,(y1-y0)/2+.005
        forbidden=unary_union([box(a-hx,d-hy,e+hx,g+hy) for a,d,e,g in [x.bounds for x in others]])
        free=~intersects_xy(forbidden,xx,yy)
        for yi,xi in zip(*np.where(free)):
            x,y=float(xs[xi]),float(ys[yi]);tr=lambda g:translate(rotate(g,-(angle-oldangle),origin=origin),xoff=x-origin[0],yoff=y-origin[1]);pp=[(q,tr(c.shapes[uid(q),'F.Cu'])) for q in pads]
            if any(obstacles[q.GetNetname()].intersects(g) or via.intersects(g) for q,g in pp):continue
            bg=tr(body);lands=unary_union([g for _,g in pp])
            if all_tracks.intersection(bg).difference(lands).area>1e-6:continue
            counts={}
            for q,g in pp:
                a,d,e,h=g.bounds;x0=max(0,int((a-.8)/p.grid)-1);x1=min(p.xx.shape[1],int((e-.8)/p.grid)+2);y0=max(0,int((d-.8)/p.grid)-1);y1=min(p.xx.shape[0],int((h-.8)/p.grid)+2);gx,gy=p.xx[y0:y1,x0:x1],p.yy[y0:y1,x0:x1];vx,vy=g.centroid.x-x,g.centroid.y-y
                counts[q.GetNumber()]=int((contains_xy(g,gx,gy)&access[q.GetNetname()][y0:y1,x0:x1]&((gx-g.centroid.x)*vx+(gy-g.centroid.y)*vy>=0)).sum())
            if not all(counts.values()):continue
            rows.append(dict(position_mm=[round(x,4),round(y,4)],angle_deg=angle,pads_mm={q.GetNumber():[round(g.centroid.x,6),round(g.centroid.y,6)] for q,g in pp},optimistic_outward_access_cells=counts));shapes.append(tr(court))
    positions[ref]=rows;geometries[ref]=shapes;print(ref,len(rows),'preliminary positions',flush=True)
pairs=[]
for i,r in enumerate(positions['R1102']):
    for j,cap in enumerate(positions['C1102']):
        distance=math.dist(r['pads_mm']['2'],cap['pads_mm']['1'])
        if distance>3 or geometries['R1102'][i].intersects(geometries['C1102'][j]):continue
        pairs.append(dict(resistor=r,capacitor=cap,filtered_pad_distance_mm=distance,score=distance+math.dist(r['pads_mm']['1'],[46.05,20.8375])+math.dist(cap['pads_mm']['1'],[31.05,5.85])))
pairs.sort(key=lambda x:x['score'])
data=dict(scope=__doc__,source_sha256=c.sha,metrics=metrics,positions=positions,pair_count=len(pairs),best_pairs=pairs[:30],physical='NOT_TESTED',adopted=False)
out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(dict(pair_count=len(pairs),best=pairs[:2])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
