"""Conditional local feed gate with an explicitly assumed bare-contact envelope."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';OUT=BASE/'cam_restraints/terminal_gate_v2'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
ctx=Context();started=time.time();G=BASE/'cam_restraints/sliding_guide_v4';gr=json.loads((G/'review.json').read_text())
assert gr['status']=='PASS'
for f,h in {**gr['sources'],**gr['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(G/'addition.npz')==gr['output_geometry']['addition.npz']
a=np.load(G/'addition.npz');guide=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
src=HERE.parent/'neck_threading_M1_48/native_threading_screen.json';prior=json.loads(src.read_text());dims=prior['terminal_dimensions_mm'];assert sorted(dims)==[1.,1.8,4.1]
def box(lo,hi):return manifold.Manifold.cube((np.asarray(hi)-lo).tolist()).translate(lo)
center=np.array([-26.6,-11.]);lo=np.r_[center-[.9,.5],221.-2.05];hi=np.r_[center+[.9,.5],231.+2.05]
nominal=box(lo.tolist(),hi.tolist());padded=box((lo-.31).tolist(),(hi+.31).tolist())
hits=[];close=[];targets={**ctx.targets,'Sliding_guide':ctx.target(guide)}
for name,t in targets.items():
    if not (np.all(t['lo']<=hi+.31) and np.all(t['hi']>=lo-.31)):continue
    v=float((padded^t['m']).volume());row=dict(target=name,expanded_sweep_overlap_mm3=v,status='PASS' if abs(v)<1e-6 else 'BLOCKED');close.append(row)
    if row['status']!='PASS':hits.append(row)
fixed=[];wire_rows=[];xy=[]
for i in range(3):
    x=-30.85+.32+.3302+i*(.6604+.32);xy.append([x,-11.])
    r=(.3302+.31)/np.cos(np.pi/64)
    m=manifold.Manifold.cylinder(3.,r,circular_segments=64).translate([x,-11.,224.0]);fixed.append(m)
    vg=float((m^guide).volume());d=float(nominal.min_gap(m,.31))
    wire_rows.append(dict(index=i,position_mm=[x,-11.],padded_wire_guide_overlap_mm3=vg,
                          incoming_sweep_vs_padded_wire_gap_mm=d,status='PASS' if abs(vg)<1e-6 and d>.001 else 'BLOCKED'))
# Direct separation is computed on original cross sections; the padded wire
# is only used for guide clearance, not as a second gap added to the terminal.
gaps=[(-26.6-.9)-(x+.3302) for x,y in xy]
assert min(gaps)>.3
ctx.assert_unchanged();inputs=[G/'review.json',G/'addition.npz',src]
r=dict(status='PASS' if not hits and all(x['status']=='PASS' for x in wire_rows) else 'BLOCKED',
       scope='Only a local straight bare-terminal gate at zero pose; not complete threaded harness assembly',
       terminal_data_status='ASSUMED',terminal_envelope_oriented_xyz_mm=[1.8,1.,4.1],terminal_source_note=prior['terminal_evidence'],
       reference_cross_section_padding_mm=.31,incoming_terminal_center_xy_mm=center.tolist(),center_z_travel_mm=[221.,231.],
       window_mm=[5.5,2.6],temporarily_parked_wires=wire_rows,last_terminal_to_nearest_parked_wire_surface_gap_mm=min(gaps),
       native_and_guide_checks=close,hits=hits,
       assembly_requirement='Supplier leaves CAM-end contacts outside the loose four-way housing until neck and guide threading is complete. Assumed contact envelope must be replaced by confirmed crimped dimensions.',
       full_wire_repositioning='NOT_TESTED',terminal_supplier_dimensions='BLOCKED',physical_feed='NOT_TESTED',main_changed=False,approved=False,
       sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('TERMINAL_GATE',r['status'],hits,min(gaps),flush=True)
