"""Read-only bounded placement screen for the complete RAW OV divider/filter group.

Actual courtyard/pads, retained tracks and nominal bodies are screened. Proposals
still require explicit routing, native refill, DRC and full power/reference checks.
"""
import ast,json,math,sys
from pathlib import Path
import numpy as np
from shapely import intersects_xy
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R154-group-placements-via-study.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='a9121d98d1c6c5d86acbdb473a0873b76fe07ae8e85f26212c999d552f844ca0'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
moving={'R1304','R1305','R1306','R1307','C1302'}
replace_nets={'Net-(U1301-INB-_{slash}_OV)','Net-(R1304-~-Pad1)','Net-(R1305-~-Pad1)'}
remove={uid(t) for t in c.tracks if t.GetNetname() in replace_nets} if hasattr(c,'tracks') else {uid(t) for t in c.segments+c.vias if t.GetNetname() in replace_nets}
mpads={uid(p) for f in c.footprints if f.GetReference() in moving for p in f.Pads()}
xs=np.arange(29.8,54.001,.1);ys=np.arange(13.8,34.001,.1);xx,yy=np.meshgrid(xs,ys);target=(41.55,25.9625)
rows={};stats={}
for ref in ['C1302','R1307','R1306','R1305','R1304']:
 f=next(f for f in c.footprints if f.GetReference()==ref);layer=c.board.GetLayerName(f.GetLayer());lid=f.GetLayer();cl=pcb.F_CrtYd if lid==pcb.F_Cu else pcb.B_CrtYd
 origin=xy(f.GetPosition());a0=f.GetOrientationDegrees();court=polyset(f.GetCourtyard(cl));body=fab(f);pads=list(f.Pads())
 others=[polyset(q.GetCourtyard(cl)) for q in c.footprints if q.GetReference() not in moving];others=[g for g in others if not g.is_empty]
 others += [k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and layer in k['layers']]
 obstacles={q.GetNetname():prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly==layer and u not in remove|mpads and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=q.GetNetname()])) for q in pads}
 vias=prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly==layer and isinstance(c.by_id[u],pcb.PCB_VIA) and u not in remove and c.by_id[u].GetNetname()=='GND']))
 retained_tracks=unary_union([c.shapes[uid(t),layer] for t in c.segments if t.GetLayer()==lid and uid(t) not in remove])
 mount=unary_union([k['shape'] for k in c.keepouts if layer in k['layers'] and k['tracks'] and not any(k['name'].startswith('BODY_'+r+'_') for r in moving)])
 rows[ref]=[];stats[ref]=[]
 for angle in [0,90,180,270]:
  rc=rotate(court,-(angle-a0),origin=origin);x0,y0,x1,y1=rc.bounds;hx,hy=(x1-x0)/2+.005,(y1-y0)/2+.005
  forbidden=unary_union([box(a-hx,d-hy,e+hx,g+hy) for a,d,e,g in [x.bounds for x in others]])
  free=~intersects_xy(forbidden,xx,yy);n=0
  for yi,xi in zip(*np.where(free)):
   pos=(float(xs[xi]),float(ys[yi]))
   if math.dist(pos,target)>13:continue
   tr=lambda g:translate(rotate(g,-(angle-a0),origin=origin),xoff=pos[0]-origin[0],yoff=pos[1]-origin[1])
   pp=[(q,tr(c.shapes[uid(q),layer])) for q in pads]
   if any(obstacles[q.GetNetname()].intersects(g) or vias.intersects(g) for q,g in pp):continue
   affected_vias=[{'uuid':uid(v),**via_snapshot(c.board,v)} for v in c.vias if uid(v) not in remove and v.GetNetname()!='GND' and any(shape(v,lid).buffer(.205).intersects(g) for q,g in pp)]
   if len(affected_vias)>2:continue
   bg=tr(body);lands=unary_union([g for q,g in pp])
   impacted=[]
   for t in c.segments:
    if t.GetLayer()!=lid or uid(t) in remove:continue
    tg=c.shapes[uid(t),layer]
    collision=tg.intersection(bg).difference(lands).area>1e-6 or any(t.GetNetname()!=q.GetNetname() and tg.intersects(g.buffer(.205)) for q,g in pp)
    if collision:impacted.append({'uuid':uid(t),'net':t.GetNetname(),'layer':layer,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'width_mm':t.GetWidth()/1e6})
   if len(impacted)>6:continue
   ground_ok=all(c.copper.get(('GND',layer),GeometryCollection()).intersects(g) for q,g in pp if q.GetNetname()=='GND')
   if not ground_ok:continue
   row={'position_mm':[round(x,4) for x in pos],'angle_deg':angle,'layer':layer,'pads_mm':{q.GetNumber():[round(g.centroid.x,6),round(g.centroid.y,6)] for q,g in pp},'courtyard_bounds_mm':list(tr(court).bounds),'distance_to_U1301_4_mm':math.dist(pos,target),'impacted_retained_tracks':impacted,'non_ground_vias_requiring_relocation':affected_vias,'score':math.dist(pos,target)+1.5*len(impacted)+2*len(affected_vias)}
   rows[ref].append(row);n+=1
  stats[ref].append({'angle':angle,'passing_positions':n});print(ref,angle,n,flush=True)
 rows[ref].sort(key=lambda r:r['score'])
 (b/'R154-placement-via-progress.json').write_text(json.dumps({'source_sha256':c.sha,'counts':{k:len(v) for k,v in rows.items()},'stats':stats},indent=2)+'\n')
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'moving_components':sorted(moving),'replaced_nets':sorted(replace_nets),'exact_source_copper_to_replace':sorted(remove),'counts':{k:len(v) for k,v in rows.items()},'stats':stats,'positions':rows,'adopted':False,'physical':'NOT_TESTED'},indent=2)+'\n')
print(json.dumps({'counts':{k:len(v) for k,v in rows.items()},'closest':{k:v[:2] for k,v in rows.items()}}),flush=True)
