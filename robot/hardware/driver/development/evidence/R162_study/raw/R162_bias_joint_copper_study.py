"""Bias pair packing with explicitly pending non-ground copper relocation.
The strict fixed-copper searches found no pair. This diagnostic preserves
native fixed component/PTH geometry and every GND hole, but reports existing
signal/power tracks and non-ground vias that would need explicit rerouting.
No conflicting placement is accepted and no PCB or design rule is changed.
"""
from pathlib import Path
wrapper=Path('robot/.state/c3-completion/trials/R162_bias_packing.py').read_text().split('"""',2)[2]
old="exec(compile(s,'R162_bias_packing_preserved_geometry','exec'))"
assert wrapper.count(old)==1
namespace={'__doc__':__doc__};exec(compile(wrapper.replace(old,'generated=s'),'packing_source','exec'),namespace)
s=namespace['generated'].replace("out=b/'R162-bias-packing.json'","out=b/'R162-bias-joint-copper.json'")
old="holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias]"
new="guard_tracks=[t for t in tracks if isinstance(t,pcb.PCB_VIA) and t.GetNetname()=='GND']\nholes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias if v.GetNetname()=='GND']"
assert s.count(old)==1;s=s.replace(old,new)
old="track_shapes=unary_union([c.shapes[(uid(t),'B.Cu')] for t in tracks])"
assert s.count(old)==1;s=s.replace(old,old.replace('in tracks','in guard_tracks'))
old="for t in tracks if t.GetNetname()!=net";assert s.count(old)==2
s=s.replace(old,"for t in guard_tracks if t.GetNetname()!=net")
marker="pairs.sort(key=lambda r:r['score'])"
extra="""for row in pairs:
 cy1,body1,pa=geometry[row['poses'][0]['id']];cy2,body2,pz=geometry[row['poses'][1]['id']]
 body=body1.union(body2);line=LineString(row['common_node_route_B_mm']);conflicts=[]
 for t in tracks:
  sh=c.shapes[(uid(t),'B.Cu')];net=t.GetNetname();via=isinstance(t,pcb.PCB_VIA)
  hit_body=body.intersection(sh).area>1e-6
  hit_pad=any((via or n!=net) and land.distance(sh)<.202 for n,land,_ in list(pa.values())+list(pz.values()))
  hit_route=net!=mid and line.distance(sh)<.302
  if hit_body or hit_pad or hit_route:conflicts.append({'uuid':uid(t),'net':net,'via':via,'body':hit_body,'pad':hit_pad,'common_route':hit_route})
 assert not any(x['via'] and x['net']=='GND' for x in conflicts)
 row['pending_copper_conflicts']=conflicts;row['nominal_distance_score']=row['score']
 row['score']=sum(6 if x['via'] else 1 for x in conflicts)+.1*row['nominal_distance_score']
"""
assert s.count(marker)==1;s=s.replace(marker,extra+marker)
exec(compile(s,'R162_bias_joint_copper_diagnostic','exec'))
