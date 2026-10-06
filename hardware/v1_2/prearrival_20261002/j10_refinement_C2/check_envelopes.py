"""Read the current Blender assembly; write only this hardware study.

Moving housing box derived from JST's documented dimensions. Exact seating
height, withdrawal force and hand access remain unqualified. Never moves or
saves objects in the main assembly.
"""
from pathlib import Path
import sys,json,hashlib,itertools
HERE=Path(__file__).resolve().parent
PROJECT_ROOT=HERE.parents[3]
sys.path.insert(0,str(PROJECT_ROOT/'mechanical/scripts'))
from common import *
from validate import Solid
from native_electronics import board_transform,source_mesh,solid_from
load_collections();assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(PROJECT_ROOT)):digest(p)for p in [source,PROJECT_ROOT/'config/geometry.json',PROJECT_ROOT/'contracts/mechanical_interfaces.json',PROJECT_ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A2.json']}
cache=source_mesh(P['native_electronics']['boards']['power']['mesh'])
r,t=board_transform('power',cache)
pcb=next(c for c in cache['components']if c['reference']=='PCB')
top=pcb['bounds_xyz_mm'][2][1]
assert np.max(np.abs(r-np.eye(3)))<1e-8
def box(lo,hi):
 pts=np.array([r@np.array([x,-y,z+top])+t for x,y,z in itertools.product(*zip(lo,hi))])
 a,b=pts.min(0),pts.max(0)
 return manifold.Manifold.cube((b-a).tolist()).translate(a.tolist())
obs={o.name.removeprefix(PREFIX):Solid(o).m for o in parts()if o.type=='MESH'and o.get('group')not in ['dock','coupon']and o.name!=PREFIX+'Power_Module'}
fallbacks=[]
for c in cache['components']:
 if c['reference']=='J10':continue
 pieces=[solid_from(np.asarray(s['vertices_mm'])@r.T+t,s['triangles'],c['reference']+'/'+str(i),fallbacks)for i,s in enumerate(c['solids'])]
 obs['Power/'+c['reference']]=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
def hits(m):
 rows=[];a=m.bounding_box()
 for n,o in obs.items():
  b=o.bounding_box()
  if any(a[i+3]<=b[i]+1e-6 or b[i+3]<=a[i]+1e-6 for i in range(3)):continue
  v=(m^o).volume()
  if v>.001:rows.append(dict(object=n,intersection_mm3=round(v,6)))
 return sorted(rows,key=lambda q:-q['intersection_mm3'])
body=box([38.25,25.05,0],[45.85,42.95,4.8])
# PHR-8 length along insertion is6.85, width17.8. Its wire face is at the
# documented mated assembly's outer edge. Reserve whole0..4.8height because
# exact contact-level Z is not dimensioned; do not invent a seating offset.
plug_lo=[36.25,25.1,0];plug_hi=[43.10,42.9,4.8]
plug=box(plug_lo,plug_hi)
trials=[]
for stroke in [4.85,5.35,6.,8.,12.]:
 samples=[]
 for d in np.linspace(0,stroke,int(np.ceil(stroke/.25))+1):
  hh=hits(plug.translate([-float(d),0,0]))
  samples.append(dict(distance_mm=float(d),overlaps=hh))
 lift=[]
 for z in np.linspace(0,12,49):
  lift.append(dict(lift_mm=float(z),overlaps=hits(plug.translate([-stroke,0,float(z)]))))
 trials.append(dict(straight_mm=stroke,samples=samples,lift12mm_samples=lift,
   straight_objects=sorted({h['object']for s in samples for h in s['overlaps']}),
   lift_objects=sorted({h['object']for s in lift for h in s['overlaps']})))
# The full face is a bounding corridor, not an assumed physical ribbon cable.
wire_box=box([31.25,25.1,0],[36.25,42.9,4.8])
out=dict(revision='J10_C2_PATH_STUDY',status='BLOCKED',assembly=P['revision'],
 body_hits=hits(body),plug_hits=hits(plug),full_wire_exit_corridor_hits=hits(wire_box),
 plug_bounds_board_mm=[plug_lo,plug_hi],socket_bounds_board_mm=[[38.25,25.05,0],[45.85,42.95,4.8]],
 minimum_geometric_body_clearance_stroke_mm=4.85,trial_stroke_with_0p5_margin_mm=5.35,
 derivation='43.10-38.25=4.85mm to put the whole housing ahead of socket front; +0.5mm project clearance. Not a vendor withdrawal specification.',
 trials=trials,source_hashes=before,proxy_fallbacks=fallbacks,
 limits=['Nominal bounding-box study; not exact contact, latch or force analysis.','Wires, crimp exit heights, strain relief, grip/tool space and tolerances are not qualified.','No formal geometry or PCB modified.'],
 sources_unchanged=all(digest(PROJECT_ROOT/p)==h for p,h in before.items()))
(HERE/'path_study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('J10_C2',json.dumps({k:out[k]for k in ['body_hits','plug_hits','full_wire_exit_corridor_hits']},ensure_ascii=False),flush=True)
for q in trials:print('STROKE',q['straight_mm'],'STRAIGHT',q['straight_objects'],'LIFT',q['lift_objects'],flush=True)
# Independent two-face placement alternative. Conservative max package bounds
# plus0.15mm assembly allowance, not a change to the main assembly.
for name in ['Power/D30','Power/F70','Power/R50']:del obs[name]
back_specs={'D30':([32.89,30.935,-4.25],[39.11,39.065,-1.6]),
            'F70':([29.03,33.85,-4.69],[31.97,40.15,-1.6]),
            'R50':([38.5,23.5,-2.6],[40.5,24.5,-1.6])}
back=[]
for name,(lo,hi)in back_specs.items():
 m=box(lo,hi);back.append(dict(reference=name,board_bounds_mm=[lo,hi],overlaps=hits(m)))
 obs['Power/'+name+'_BACK_CANDIDATE']=m
# Current C2 has an in-plane rotated JP70 and relocated exposed ground TP71.
for ref,new_xy,delta_deg in [('JP70',(35.,44.5),-90.),('TP71',(23.,35.),0.)]:
 c=next((c for c in cache['components']if c['reference']==ref),None)
 if c is None:
  assert ref=='TP71','Only bare-pad testpoint may be absent from populated source'
  continue
 old_xy=(36.5,44.5)if ref=='JP70'else(34.5,48.)
 pivot=r@np.array([old_xy[0],-old_xy[1],top])+t
 dest=r@np.array([new_xy[0],-new_xy[1],top])+t
 obs['Power/'+ref]=obs['Power/'+ref].translate((-pivot).tolist()).rotate([0,0,delta_deg]).translate(dest.tolist())
refined=[]
for d in np.linspace(0,5.35,23):refined.append(dict(phase='withdraw',distance_mm=float(d),overlaps=hits(plug.translate([-float(d),0,0]))))
for z in np.linspace(0,12,49):refined.append(dict(phase='lift',distance_mm=float(z),overlaps=hits(plug.translate([-5.35,0,float(z)]))))
out2=dict(revision='J10_C2_BACKSIDE_SCREEN',status='BLOCKED',
  source_hashes=before,backside_envelopes=back,body_hits=hits(body),plug_hits=hits(plug),wire_corridor_hits=hits(wire_box),
  withdraw5p35_lift12_samples=refined,
  bounds_basis={'D30':'DS13012 Rev18-2 p4 maximum6.22x8.13x2.50 plus ASSUMED0.15 assembly allowance',
                'F70':'Littelfuse451/453 nominal6.10x2.69x2.69, tolerances0.20/0.25/0.25 plus ASSUMED0.15 assembly allowance',
                'R50':'ASSUMED2x1x1mm 0603 assembly allocation; not a measured or vendor-complete package'},
  old_backside_allocation_mm=3.,D30_proposed_backside_mm=2.65,F70_proposed_backside_mm=3.09,
  allocation_exceedance_mm=.09,
  limits=['Independent candidate only. F70 exceeds3mm historical allocation by0.09mm after proposed0.15mm assembly allowance; mechanical acceptance required.',
          'Cleared plug bbox does not qualify hand access or actual wire bend.','Electrical rerouting/thermal performance not demonstrated by this screen.'],
  sources_unchanged=all(digest(PROJECT_ROOT/p)==h for p,h in before.items()))
(HERE/'backside_screen.json').write_text(json.dumps(out2,ensure_ascii=False,indent=2)+'\n')
print('BACKSIDE',back,'PLUG',out2['plug_hits'],'WIRE',out2['wire_corridor_hits'],'PATH_HITS',sum(bool(s['overlaps'])for s in refined),flush=True)
# Test candidate bends rather than assert an unspecified harness fits.
# Wire positions follow2mm contact pitch, but actual crimp Z is not supplied.
# Sweep several exit-height assumptions and preserve all resulting failures.
radius=1.0922/2;Rbend=10.922
def tube(points):
 pieces=[];rr=radius/math.cos(math.pi/32)
 for a,z in zip(points,points[1:]):
  d=z-a;length=float(np.linalg.norm(d));angle=math.degrees(math.atan2(d[0],d[2]))
  assert abs(d[1])<1e-8
  pieces.append(manifold.Manifold.cylinder(length,rr,circular_segments=32).rotate([0,angle,0]).translate(a.tolist()))
 # Circumscribed small cubes at endpoints conservatively close polygon joints.
 # Cubes overestimate swept tube locally; any collision remains a screen.
 for a in points:pieces.append(manifold.Manifold.cube([2*radius]*3,center=True).translate(a.tolist()))
 return manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
wire_rows=[]
for zc in [1.,1.5,2.,2.5,3.,3.5,4.25]:
 rows=[]
 for i in range(8):
  yy=27+2*i
  local=[[36.25,yy,zc],[31.25,yy,zc]]+[[31.25-Rbend*math.sin(a),yy,zc+Rbend*(1-math.cos(a))]for a in np.linspace(0,math.pi/2,33)[1:]]
  points=[r@np.array([x,-y,z+top])+t for x,y,z in local]
  rows.append(dict(pin=i+1,overlaps=hits(tube(points))))
 wire_rows.append(dict(exit_center_above_PCB_mm=zc,bend_radius_mm=Rbend,straight_exit_mm=5,wire_OD_mm=2*radius,
                       highest_surface_above_PCB_mm=zc+Rbend+radius,rows=rows))
dump=dict(revision='J10_C2_WIRE_SENSITIVITY',status='NOT_TESTED',rows=wire_rows,
 assumptions=['Wire exit Z not dimensioned. Each scenario is an assumption, not a qualified harness.',
              'Individual AWG26 reference-wire OD max1.0922mm; not a finished bound bundle or dynamic-flex qualification.',
              'Polyline tubes plus conservative joint cubes can over-reject; no smoothing or source shrinking used.',
              'Tail beyond the90degree bend, strain relief, dressing, withdrawal with wires and grip/tool access not checked.'])
(HERE/'wire_sensitivity.json').write_text(json.dumps(dump,ensure_ascii=False,indent=2)+'\n')
for row in wire_rows:print('WIRE_Z',row['exit_center_above_PCB_mm'],'HITS',[(v['pin'],[h['object']for h in v['overlaps']])for v in row['rows']if v['overlaps']],flush=True)
# An independently named5D wire is not permission to shrink5853's radius.
# This is a candidate/static bend comparison; no wire substitution is adopted.
radius=1.016/2;Rbend=5.08
eco=[]
for straight in [1.5,3.,5.]:
 for zc in [radius,1.2,2.4,3.6,4.8-radius]:
  rows=[]
  for i in range(8):
   yy=27+2*i;start=36.25-straight
   local=[[36.25,yy,zc],[start,yy,zc]]+[[start-Rbend*math.sin(a),yy,zc+Rbend*(1-math.cos(a))]for a in np.linspace(0,math.pi/2,33)[1:]]
   points=[r@np.array([x,-y,z+top])+t for x,y,z in local]
   rows.append(dict(pin=i+1,overlaps=hits(tube(points))))
  eco.append(dict(straight_exit_mm=straight,exit_center_mm=zc,rows=rows))
(HERE/'ecowire_comparison.json').write_text(json.dumps(dict(status='NOT_TESTED',part='Alpha6711',OD_max_mm=1.016,Rbend_mm=5.08,
 source='https://www.alphawire.com/products/wire/ecogen/ecowire/6711',source_date='2026-10-02',rows=eco,
 limits=['Price/short-length domestic supply not confirmed; not a selected cable.',
         'Only individual static-wire escape tubes; crimp strain, tail, bundle, dressing, and cable-attached plug removal not qualified.',
         '1.5/3/5mm straight exit are comparative design allocations, NOT manufacturer minima. A3 retains5mm pending review.',
         'These tests use no extra0.3mm mechanical tolerance buffer; joint cubes conservatively bound nominal tube geometry.']),ensure_ascii=False,indent=2)+'\n')
for row in eco:print('ECO',row['straight_exit_mm'],row['exit_center_mm'],[(v['pin'],[h['object']for h in v['overlaps']])for v in row['rows']if v['overlaps']],flush=True)
