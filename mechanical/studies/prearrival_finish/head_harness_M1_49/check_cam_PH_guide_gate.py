"""Catalogue PH contact outline through the existing unapproved guide window.

The family drawing is not a supplier crimped-terminal model. Terminal choice
is also still unresolved: the native handoff names SPH002, whose 0.8 mm minimum
insulation OD is larger than the current 0.6604 mm route sample.
"""
from pathlib import Path
import json,sys,time,itertools
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
OUT=REST/'PH_terminal_gate';G=REST/'sliding_guide_v4';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));from harness_context import Context,np,sha
from common import manifold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());gr=read(G/'review.json');assert gr['status']=='PASS'
for f,h in {**gr['sources'],**gr['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(G/'addition.npz')==gr['output_geometry']['addition.npz']
a=np.load(G/'addition.npz');guide=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
pdf=HERE.parent/'supplier_made_harness/recheck_20261004/JST_PH.pdf'
handoff=ROOT/'hardware/v1_2/handoff/mechanical_P5R7.json';hr=read(handoff)
board=next(v for k,v in hr['boards'].items() if 'MORI_motion_' in k)
J5=next(x for x in board['connectors'] if x['ref']=='J5')
assert J5['mating']=='PHR-4' and J5['contact']=='SPH-002T-P0.5S'
def box(lo,hi):return manifold.Manifold.cube((np.asarray(hi)-lo).tolist()).translate(np.asarray(lo).tolist())
dims=np.array([2.08,1.5,5.7]);xy=np.array([-26.8,-11.]);lo=np.r_[xy-dims[:2]/2,221.-dims[2]/2];hi=np.r_[xy+dims[:2]/2,231.+dims[2]/2]
nominal=box(lo,hi);sweep=box(lo-.31,hi+.31);targets={**ctx.targets,'Sliding_guide':ctx.target(guide)}
checks=[];hits=[]
for n,t in targets.items():
    if not (np.all(t['lo']<=hi+.31)&np.all(t['hi']>=lo-.31)):continue
    v=float((sweep^t['m']).volume());r=dict(target=n,expanded_sweep_overlap_mm3=v,status='PASS' if abs(v)<1e-6 else 'BLOCKED');checks.append(r)
    if r['status']!='PASS':hits.append(r)
park=[[-30.15,-11.5],[-30.15,-10.5],[-29.2,-11.]];wr=[]
for i,p in enumerate(park):
    r=(.3302+.31)/np.cos(np.pi/64)
    tube=manifold.Manifold.cylinder(3.,r,circular_segments=64).translate([*p,224.])
    v=float((tube^guide).volume());over=float((nominal^tube).volume());gap=float(nominal.min_gap(tube,.31))
    wr.append(dict(index=i,xy_mm=p,expanded_wire_guide_overlap_mm3=v,incoming_nominal_vs_padded_wire_overlap_mm3=over,
                   residual_gap_mm=gap,status='PASS' if abs(v)<1e-6 and abs(over)<1e-6 and gap>.001 else 'BLOCKED'))
pairs=[dict(i=i,j=j,wire_surface_gap_mm=float(np.linalg.norm(np.asarray(park[i])-park[j])-.6604)) for i,j in itertools.combinations(range(3),2)]
ctx.assert_unchanged()
for name,m in [('PH_contact_sweep',nominal),('PH_padded_sweep',sweep)]:
    a=m.to_mesh64();np.savez_compressed(OUT/(name+'.npz'),vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
r=dict(status='PASS' if not hits and all(x['status']=='PASS' for x in wr) and min(x['wire_surface_gap_mm'] for x in pairs)>=.3 else 'BLOCKED',
    scope='Conditional local straight gate only, using dimensioned generic PH uncrimped contact outline; not complete feed or selected crimp geometry',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [G/'review.json',G/'addition.npz',pdf,handoff]},
    terminal_drawing=dict(file=str(pdf.relative_to(ROOT)),page=2,source_url='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
        nominal_oriented_xyz_mm=dims.tolist(),outline_evidence='VENDOR_DOCUMENTED generic family diagram; no per-SKU crimped maximum dimensions or tolerances provided'),
    native_J5=J5,route_wire_OD_mm=.6604,SPH002_insulation_OD_mm=[.8,1.5],SPH002_OD_check='FAIL',
    SPH004_candidate_insulation_OD_mm=[.5,.9],SPH004_OD_only_check='PASS',terminal_selected=False,
    procurement_and_crimp_fit='BLOCKED',contact_crimp_qualification='NOT_TESTED',
    incoming_center_xy_mm=xy.tolist(),incoming_center_z_range_mm=[221,231],clearance_padding_mm=.31,
    checks=checks,hits=hits,parked_wire_checks=wr,parked_pair_gaps=pairs,
    assembly_requirement='Bench-preassembly direction would leave BODY-side PH contacts outside PHR-4 housing until guide and neck feed. This supersedes neither the prior SH-side plan nor the hardware contact contract; sequence remains a candidate.',
    limits=['Two temporary wire rows are required for this local check; transition to these rows and full wire feed remain NOT_TESTED.',
            'Do not reuse the earlier assumed1.8x1.0x4.1mm SH-side box for PH-side threading.',
            'Electrical owner must reconcile actual wire/contact selection before a supplier drawing is released. No hardware file was edited.'],
    main_changed=False,approved=False,full_harness='BLOCKED',output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('PH_GATE_DONE',r['status'],hits,wr,flush=True)
