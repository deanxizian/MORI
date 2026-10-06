"""Bounded bench order for the independent connector-adjacent anchor."""
from pathlib import Path
AS_SCRIPT=Path(__file__).resolve();AS_ROOT=AS_SCRIPT.parent
AS_HELPER=AS_ROOT/'screen_CAM_pitch_anchor_warp.py';__file__=str(AS_HELPER)
exec(compile(AS_HELPER.read_text().split('\npw_rows=[];',1)[0],str(AS_HELPER),'exec'),globals())
__file__=str(AS_SCRIPT);AS_OUT=AS_ROOT/'cam_pitch_anchor/connector_anchor'
ar=json.loads((AS_OUT/'root_v3_screen.json').read_text());assert ar['status']=='PASS'
as_cradle=pw_readsolid(AS_OUT/'Pitch_Cradle.npz');as_addition=pw_readsolid(AS_OUT/'addition.npz')
as_tie=pw_readsolid(AS_OUT/'z212.0_band.npz')+pw_readsolid(AS_OUT/'z212.0_head.npz')
as_wires={f'local_wire_{i}':manifold.Manifold.cylinder(14.6,OD/2,circular_segments=64).translate([float(x),float(slots[0,1]),200.]) for i,x in enumerate(slots[:,0])}
as_bench={'Pitch_Cradle':as_cradle}|{n:s.m for n,s in ss.items() if n.startswith('CAM_Mount_Insert_')}

def as_sweep(moving,fixture,axis,travel,step=.1):
    failures=[];count=0;nearest=2.;axis=np.array(axis,float)
    for dist in np.linspace(0,travel,math.ceil(travel/step)+1):
        shift=axis*dist;count+=1
        for n,m in moving.items():
            placed=m.translate(shift.tolist())
            for key,target in fixture.items():
                if not overlap_boxes(placed,target,.6):continue
                v=max(0.,float((placed^target).volume()))
                if v>1e-5:
                    failures.append({'moving':n,'obstacle':key,'displacement_mm':shift.tolist(),'intersection_mm3':v})
                    return {'status':'BLOCKED','samples':count,'hits':failures,'step_mm':step,'travel_mm':travel,'axis':axis.tolist()}
                gap=float(placed.min_gap(target,.6));nearest=min(nearest,gap)
    return {'status':'PASS','samples':count,'hits':[],'minimum_sampled_gap_mm':nearest,'step_mm':step,'travel_mm':travel,'axis':axis.tolist(),
       'continuous_sweep':'NOT_TESTED','scope':'Finite rigid sample positions, not flexible threading, human access or connector engagement force'}

as_rows={}
as_rows['plug_after_board_from_below']=as_sweep({'CAM_catalogue_housing':housing},{'anchor':as_addition},[0,0,-1],12.)
print('CAM_ANCHOR_ASSEMBLY','plug_after_board_from_below',as_rows['plug_after_board_from_below'],flush=True)
as_rows['preplugged_CAM_to_detached_cradle']=as_sweep({'CAM_Mainboard':ss['CAM_Mainboard'].m,'CAM_catalogue_housing':housing}|as_wires,as_bench,[0,1,0],20.)
print('CAM_ANCHOR_ASSEMBLY','preplugged_CAM_to_detached_cradle',as_rows['preplugged_CAM_to_detached_cradle'],flush=True)
as_rows['preclosed_tie_below_on_bench']=as_sweep({'tie':as_tie},as_bench|{'CAM_Mainboard':ss['CAM_Mainboard'].m,'CAM_catalogue_housing':housing}|as_wires,[0,0,-1],12.)
print('CAM_ANCHOR_ASSEMBLY','preclosed_tie_below_on_bench',as_rows['preclosed_tie_below_on_bench'],flush=True)
as_report={'status':'PASS' if as_rows['preplugged_CAM_to_detached_cradle']['status']==as_rows['preclosed_tie_below_on_bench']['status']=='PASS' else 'BLOCKED',
 'scope':'Bounded detached-cradle rigid assembly allocations and local loose wires; not complete harness assembly',
 'script_sha256':sha(AS_SCRIPT),'helper_sha256':sha(AS_HELPER),'source_main_sha256':source_hash,
 'root_report_sha256':sha(AS_OUT/'root_v3_screen.json'),'part_sha256':sha(AS_OUT/'Pitch_Cradle.npz'),
 'rows':as_rows,'fixture_ids':list(as_bench),'temporary_wire_span_z_mm':[200.,214.6],
 'complete_wire_end_storage':'NOT_TESTED','flexible_tie_threading_and_tension':'NOT_TESTED','full_assembly':'NOT_TESTED',
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(AS_OUT/'assembly.json').write_text(json.dumps(as_report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CAM_ANCHOR_ASSEMBLY_DONE',as_report['status'],flush=True)
