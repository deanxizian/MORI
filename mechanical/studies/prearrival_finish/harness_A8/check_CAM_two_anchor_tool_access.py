"""Check profiled tooling at BOTH CAM ties after the cradle is seated.

This is a local work-volume study, not a complete cable installation path.
The photo-derived tool remains ASSUMED and the robot model is not modified.
"""
from pathlib import Path
TA_SCRIPT=Path(__file__).resolve();TA_ROOT=TA_SCRIPT.parent
TA_HELPER=TA_ROOT/'check_CAM_profiled_tool.py';__file__=str(TA_HELPER)
exec(compile(TA_HELPER.read_text().split('\npt_profiles=',1)[0],str(TA_HELPER),'exec'),globals())
__file__=str(TA_SCRIPT)
TA_OUT=TA_ROOT/'cam_profiled_tool'
ta_targets=wi_fixed|wi_moving
ta_xsum=float(slots[:,0].mean()+xx.mean())
ta_matrix=np.array([[-1.,0.,0.,ta_xsum],[0.,1.,0.,float(slots[0,1]+1.5)],[0.,0.,1.,-20.]])
ta_connector_pivot=(ta_matrix[:,:3]@st_pivot)+ta_matrix[:,3]

def ta_wire_minimum(m):
    mesh=m.to_mesh64();tree=BVHTree.FromPolygons(mesh.vert_properties[:,:3],mesh.tri_verts.tolist(),all_triangles=True)
    core,meta=wi_core(0.);best={'gap_lower_bound_mm':math.inf}
    for slot in range(4):
        curves=[('core',core+[xx[slot]-xx[0],0.,0.],meta['curve_error_mm']),
                ('tail',PW_OLD_TAILS[slot],tail_error),
                ('fan',pw_fans[slot][0],pw_fan_errors[slot]),
                ('body',body_samples[slot+1,0][0],body_error)]
        for kind,p,error in curves:
            half_step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())/2
            for i,q in enumerate(p):
                nearest=tree.find_nearest(Vector(q));d=float(nearest[3])
                bound=d-half_step-error-OD/2-.0001
                if bound<best['gap_lower_bound_mm']:
                    best={'gap_lower_bound_mm':bound,'centre_to_tool_mm':d,'slot':slot,'route':kind,
                          'point_mm':q.tolist(),'nearest_tool_mm':list(nearest[0]),
                          'half_step_mm':half_step,'curve_error_mm':error}
    best['status']='PASS' if best['gap_lower_bound_mm']>=.3 else 'BLOCKED'
    return best

ta_rows=[];ta_started=time.time()
for anchor in ['yaw','connector']:
    mat=None if anchor=='yaw' else ta_matrix
    pivot=st_pivot if anchor=='yaw' else ta_connector_pivot
    toolbase=pt_tool if mat is None else pt_tool.transform(mat)
    sweepbase=pt_sweep if mat is None else pt_sweep.transform(mat)
    tailbase=st_tail if mat is None else st_tail.transform(mat)
    tail_fit=st_hits(tailbase,ta_targets)
    for angle in ([30.,45.] if anchor=='yaw' else list(np.arange(-180.,180.,15.))):
        def orient(m):return m.translate((-pivot).tolist()).rotate([0.,float(angle),0.]).translate(pivot.tolist())
        swept=orient(sweepbase);tool=orient(toolbase)
        fit=st_hits(swept,ta_targets)
        wires=st_wire_hits(swept,0.) if fit['status']=='PASS' else {'status':'NOT_TESTED'}
        row={'anchor':anchor,'angle_deg':float(angle),'fixture':fit,'wires':wires,'tail':tail_fit,
             'status':'PASS' if fit['status']==wires['status']==tail_fit['status']=='PASS' else 'BLOCKED'}
        if row['status']=='PASS':
            row['wire_minimum']=ta_wire_minimum(swept)
            assert row['wire_minimum']['status']=='PASS'
            row['rigid_without_ties']=st_hits(swept,{n:m for n,m in ta_targets.items() if n not in ['CAM_Tie_Head','CAM_Tie_Band','CAM_connector_tie_head','CAM_connector_tie_band']})
            cache(TA_OUT/f'{anchor}_{angle:g}_tool.npz',tool)
            cache(TA_OUT/f'{anchor}_{angle:g}_sweep.npz',swept)
            cache(TA_OUT/f'{anchor}_tail_corridor.npz',tailbase)
        ta_rows.append(row)
        print('TWO_ANCHOR_TOOL',anchor,angle,row['status'],[r['object'] for r in fit['hits']],row.get('wire_minimum'),flush=True)
ta_result={'status':'PASS' if all(any(r['status']=='PASS' and r['anchor']==a for r in ta_rows) for a in ['yaw','connector']) else 'BLOCKED',
    'scope':'Both proposed CAM ties, seated cradle, all current servos retained, four prescribed CAM wires at mechanical zero; profiled 60 mm axial cutter work volume',
    'script_sha256':sha(TA_SCRIPT),'helper_sha256':sha(TA_HELPER),'source_main_sha256':source_hash,
    'source_receipt_sha256':sha(TA_OUT/'sources/receipt.json'),
    'rows':ta_rows,'fixture_ids':list(ta_targets),'not_yet_fitted':wi_excluded,
    'profile_stations_z_width_depth_mm':PT_STATIONS,'tool_shape_evidence':'ASSUMED from manufacturer photographs, with documented head and general dimensions',
    'pivots_mm':{'yaw':st_pivot.tolist(),'connector':ta_connector_pivot.tolist()},
    'wire_required_clearance_mm':.3,'main_applied':False,'manufacturing_release':False,
    'whole_harness':'BLOCKED','forming_wires_and_threading_ties':'NOT_TESTED','tool_physical_fit':'NOT_TESTED',
    'hands_closing_motion_cutting_force':'NOT_TESTED','remaining_seven_wires_FPC':'NOT_TESTED','elapsed_s':time.time()-ta_started}
(TA_OUT/'both_anchors.json').write_text(json.dumps(ta_result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('TWO_ANCHOR_DONE',ta_result['status'],[(r['anchor'],r['angle_deg']) for r in ta_rows if r['status']=='PASS'],flush=True)
