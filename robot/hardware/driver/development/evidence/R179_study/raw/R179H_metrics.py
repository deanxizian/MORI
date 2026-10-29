"""Read-only native comparison metrics; cache each pad-group enumeration once."""
import hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R179H/MORI_Interface_C3.kicad_pcb');out=b/'R179H-metrics-v2.json';assert not out.exists()
new=[t for t in c.segments if uid(t) not in a.by_id];stroke=unary_union([c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())] for t in new]);rows=[]
for (n,ly),g in c.copper.items():
 if ly=='In2.Cu' or n in ['GND','/CLR_N']:continue
 ov=stroke.intersection(g)
 if ov.area>1e-8:rows.append(dict(net=n,layer=ly,overlap_mm2=ov.area,unshielded_by_intervening_plane_mm2=ov.difference(c.copper['GND','In1.Cu' if ly=='F.Cu' else 'In4.Cu']).area if ly in ['F.Cu','B.Cu'] else None,intervening_ground_plane=('In1.Cu' if ly=='F.Cu' else 'In4.Cu') if ly in ['F.Cu','B.Cu'] else None))
ag=a.pad_groups();cg=c.pad_groups()
gate=[]
for t in c.segments:
 if t.GetNetname()!='Net-(U1001-S2_{slash}_WHEEL_sense)' or c.board.GetLayerName(t.GetLayer())!='In3.Cu':continue
 s=c.shapes[uid(t),'In3.Cu'];ov=stroke.intersection(s)
 if ov.area>1e-8:gate.append(dict(uuid=uid(t),start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())),width_mm=t.GetWidth()/1e6,overlap_mm2=ov.area))
r=dict(scope=__doc__,source_sha256=a.sha,board_sha256=c.sha,new_route_length_mm=sum(math.dist(xy(t.GetStart()),xy(t.GetEnd())) for t in new),source_route_length_mm=2.9,old_connection_changes=[n for n in ag if len(ag[n])!=len(cg[n])],projection_rows=rows,WHEEL_sense_In3_intersections=gate,adopted=False,physical='NOT_TESTED',local_coupling_acceptance='NOT_TESTED')
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
assert hashlib.sha256(Path(a.path).read_bytes()).hexdigest()==a.sha and hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
