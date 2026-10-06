"""Replay the CAM-board-last sequence on explicit M1.48 geometry.

Only sampled flexible-wire shapes and bounded rigid translations are checked.
The wire curves are read as data; no historical host initialization is run.
"""
from pathlib import Path
from types import SimpleNamespace
import sys, json, time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'yaw_service_M1_48'))
from current_context import RetentionContext, PROJECT, np, manifold, sha, overlap_boxes
from local_clearance import adaptive_clear
ctx=RetentionContext();started=time.time();A8=HERE.parent/'harness_A8'
source=A8/'cam_board_last';old=json.loads((source/'screen.json').read_text())
assert old['status']=='PASS' and old['curves_sha256']==sha(source/'curves.npz')
curves=np.load(source/'curves.npz');excluded=set(old['not_yet_fitted_pitch_parts'])
assert all(n in ctx.base for n in excluded)
deferred={n for n in ctx.base if n.startswith('CAM_Mount_Screw_')}
board_names={'CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R'}
fixture={n:m for n,m in ctx.targets.items() if n not in excluded|deferred|board_names}
for n in ['Pitch_Yoke','Pitch_Cradle']:fixture[n]=ctx.read(HERE/(n+'.npz'))
# The connector-side tie is closed only after the board reaches its seats.
for kind in ['band','head']:fixture['yaw_'+kind]=ctx.read(HERE/('yaw_'+kind+'.npz'))

cam=ctx.ctx.ss['CAM_Mainboard'];o=cam.o
vertices=np.asarray([o.matrix_world@v.co for v in o.data.vertices])
faces=np.asarray([list(p.vertices) for p in o.data.polygons],np.uint64)
assert all(len(p.vertices)==3 for p in o.data.polygons)
components={}
for row in json.loads(o['component_reference_index']):
    va,vb=row['vertices'];fa,fb=row['faces']
    part=manifold.Manifold(manifold.Mesh64(vertices[va:vb],faces[fa:fb]-va))
    assert part.status()==manifold.Error.NoError
    components[row['reference']]=manifold.Manifold.batch_boolean(part.decompose(),manifold.OpType.Add)
full=manifold.Manifold.batch_boolean(list(components.values()),manifold.OpType.Add)
source_difference=abs(float((full-cam.m).volume()))+abs(float((cam.m-full).volume()))
assert source_difference<.02
rest=manifold.Manifold.batch_boolean([m for n,m in components.items() if n!='UART_4P'],manifold.OpType.Add)
board={'CAM_without_own_UART':rest,'CAM_UART_4P':components['UART_4P']}
board.update({n:ctx.base[n] for n in board_names if n!='CAM_Mainboard'})
alloc_file=A8/'cam_pitch_port/allocation_meshes.npz';data=np.load(alloc_file)
housing=manifold.Manifold(manifold.Mesh64(data['housing_v'],data['housing_f'].astype(np.uint64)))
bb=np.asarray(housing.bounding_box());slots=np.array([[float((bb[0]+bb[3])/2)+d,float((bb[1]+bb[4])/2),float(bb[2])] for d in [-1.5,-.5,.5,1.5]])
prefixes={};native_final={}
for pin in range(1,5):
    p=ctx.curves[f'pin{pin}_y0_p0'];q=curves[f'seating_plug0_board0_slot{pin-1}']
    matches=np.flatnonzero(np.linalg.norm(p-q[0],axis=1)<1e-6)
    assert len(matches)==1 and np.linalg.norm(p[-1]-q[-1])<1e-6
    assert np.linalg.norm(p[-1]-slots[pin-1])<1e-6
    prefixes[pin]=p[:matches[0]+1];native_final[pin]=p[matches[0]:]

def collision(shape,targets):
    result=[]
    for n,t in targets.items():
        if not overlap_boxes(shape,t):continue
        vol=max(0.,float((shape^t).volume()))
        if vol>1e-6:result.append(dict(target=n,intersection_mm3=vol))
    return result

fixed_targets={n:ctx.ctx.target(m) for n,m in fixture.items()}
rows=[];stage_curves={}
for row in old['rows']:
    board_shift=row['board_shift_mm'];plug_shift=row['plug_shift_mm']
    h=plug_shift[2];bh=board_shift[2];stage=row['stage']
    key=f'{stage}_plug{h:g}_board{bh:g}'
    moved={n:m.translate(board_shift) for n,m in board.items()}
    moved['CAM_catalogue_housing']=housing.translate(plug_shift)
    hits=[]
    for n,m in moved.items():
        hits.extend(dict(part=n,**r) for r in collision(m,fixture))
    hits.extend(dict(part='CAM_catalogue_housing',**r) for r in collision(moved['CAM_catalogue_housing'],{n:m for n,m in moved.items() if n not in ['CAM_catalogue_housing','CAM_UART_4P']}))
    targets=fixed_targets|{n:ctx.ctx.target(m) for n,m in moved.items()}
    wire_hits=[];lengths=[]
    for pin in range(1,5):
        upper=curves[key+f'_slot{pin-1}'];p=np.vstack([prefixes[pin],upper[1:]])
        assert np.linalg.norm(upper[0]-prefixes[pin][-1])<1e-6
        assert np.linalg.norm(p[-1]-(slots[pin-1]+plug_shift))<1e-6
        lengths.append(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()))
        stage_curves[f'{key}_pin{pin}']=p
        # Per-target intended contact is limited to the unchanged straight
        # wire roots and bed seats. Allocation housing roots are not real
        # terminal geometry: their declared first 5 mm are excluded only from
        # their own housing/connector. Bed material is still checked below.
        for name,target in targets.items():
            contact=np.zeros(len(p),bool)
            if name=='Plug_motion_J5':
                root=p[0];contact=(np.abs(p[:,0]-root[0])<1e-5)&(np.abs(p[:,1]-root[1])<1e-5)&(p[:,2]>=root[2]-1e-5)&(p[:,2]<=root[2]+5.+1e-5)
            if name in ['Pitch_Yoke','yaw_band','yaw_head']:
                contact=(np.abs(p[:,1]+1.5)<1e-5)&(p[:,2]>=229.9-1e-5)&(p[:,2]<=234.3+1e-5)
            if name=='Pitch_Cradle':
                contact=(np.abs(p[:,0]-slots[pin-1,0])<1e-5)&(np.abs(p[:,1]-slots[pin-1,1])<1e-5)&(p[:,2]>=slots[pin-1,2]-5.-1e-5)&(p[:,2]<=slots[pin-1,2]+1e-5)
            if name in ['CAM_catalogue_housing','CAM_UART_4P']:
                contact=(np.abs(p[:,0]-slots[pin-1,0])<1e-5)&(np.abs(p[:,1]-slots[pin-1,1])<1e-5)&(p[:,2]>=slots[pin-1,2]+h-5.-1e-5)&(p[:,2]<=slots[pin-1,2]+h+1e-5)
            tinyctx=SimpleNamespace(targets={name:target})
            for mask,gap in [(~contact,.3),(contact,0.)]:
                if gap==0 and name in ['Plug_motion_J5','CAM_catalogue_housing','CAM_UART_4P']:
                    continue
                ids=np.flatnonzero(mask)
                spans=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)
                for ids in spans:
                    if len(ids)<2:continue
                    result=adaptive_clear(tinyctx,p[ids],.0003,surface_gap=gap)
                    if result:wire_hits.append(dict(pin=pin,intended_contact=(gap==0),**result));break
                if wire_hits and wire_hits[-1]['pin']==pin:break
            if wire_hits and wire_hits[-1]['pin']==pin:break
    rows.append(dict(stage=stage,board_shift_mm=board_shift,plug_shift_mm=plug_shift,
        status='BLOCKED' if hits or wire_hits else 'PASS',rigid_hits=hits,wire_hits=wire_hits,
        full_polyline_lengths_mm=lengths,source_curve_radius_lower_mm=row['curve']['minimum_radius_bound_mm']))
    print('CURRENT_CAM_BOARD',stage,h,bh,rows[-1]['status'],hits,wire_hits,flush=True)

# Continuous translations use each original component's individual convex
# swept envelope; the board's large empty gaps are not filled by one hull.
sweeps=[]
for name,m in (components|{n:ctx.base[n] for n in board_names if n!='CAM_Mainboard'}).items():
    swept=manifold.Manifold.batch_hull([m,m.translate([0.,0.,6.])])
    hits=collision(swept,fixture)
    sweeps.append(dict(part=name,stage='board_lowering',status='BLOCKED' if hits else 'PASS',hits=hits))
plug_sweep=manifold.Manifold.batch_hull([housing,housing.translate([0.,0.,6.])])
for label,targets in [('mated_lowering',fixture),('mate_to_raised_board',fixture|{n:m.translate([0.,0.,6.]) for n,m in board.items() if n!='CAM_UART_4P'})]:
    hits=collision(plug_sweep,targets)
    sweeps.append(dict(part='CAM_catalogue_housing',stage=label,status='BLOCKED' if hits else 'PASS',hits=hits))
np.savez_compressed(HERE/'board_installation_curves.npz',**stage_curves)
length_table=np.asarray([r['full_polyline_lengths_mm'] for r in rows])
ctx.assert_unchanged()
result=dict(status='PASS' if all(r['status']=='PASS' for r in rows+sweeps) else 'BLOCKED',
    scope='16 full mathematical wire placements and componentwise continuous 6 mm board/plug translations on explicit current candidates',
    **ctx.evidence(),script_sha256=sha(__file__),context_sha256=sha(HERE/'current_context.py'),
    sources={str(p.relative_to(PROJECT)):sha(p) for p in [source/'screen.json',source/'curves.npz',alloc_file]},
    component_count=len(components),source_reconstruction_symmetric_difference_mm3=source_difference,
    excluded_not_installed=sorted(excluded),deferred_CAM_screws=sorted(deferred),
    connector_tie='Not closed until after seating',yaw_tie='Installed nominal allocation',
    intentional_mating_root_exclusions='First 5 mm at body J5 and moving CAM exit against their own connector/housing only; these are allocated port faces, not a terminal-fit qualification. Host groove material checked with zero extra air gap.',
    rows=rows,rigid_sweeps=sweeps,polyline_length_spread_mm=np.ptp(length_table,axis=0).tolist(),
    analytical_length_rule=old['analytical_length_rule'],
    curve_cache_sha256=sha(HERE/'board_installation_curves.npz'),
    continuous_flexible_wire_motion='NOT_TESTED',wire_mutual_clearance='Historical same upper-curve evidence only; no new full-route packing approval',
    current_screw_tools='Approved M1.48 tool review remains separate from this stage',
    actual_plug_depth='BLOCKED',complete_wire_feed='NOT_TESTED',elapsed_s=time.time()-started)
(HERE/'board_installation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CURRENT_CAM_BOARD_DONE',result['status'],flush=True)
