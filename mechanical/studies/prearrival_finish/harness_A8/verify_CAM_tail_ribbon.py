"""Replay saved tail solid and bound clearance; perturb only temporary routing."""
from pathlib import Path
TV_SCRIPT=Path(__file__).resolve();TV_ROOT=TV_SCRIPT.parent
TV_HELPER=TV_ROOT/'check_CAM_tail_ribbon_access.py';__file__=str(TV_HELPER)
exec(compile(TV_HELPER.read_text().split('\ntr_rows=[];',1)[0],str(TV_HELPER),'exec'),globals())
__file__=str(TV_SCRIPT)
tv_input=TR_OUT/'inner_corridor.json';tv_screen=json.loads(tv_input.read_text())
tv_selected=34;tv_mesh=TR_OUT/f'inner_tail_{tv_selected}.npz'
tv_m=pw_readsolid(tv_mesh)
tv_without_contact={n:m for n,m in tr_targets.items() if n not in ['CAM_connector_tie_head','CAM_connector_tie_band']}

def tv_wire_gap(m):
    mesh=m.to_mesh64();tree=BVHTree.FromPolygons(mesh.vert_properties[:,:3],mesh.tri_verts.tolist(),all_triangles=True)
    core,meta=wi_core(0.);best={'gap_lower_bound_mm':math.inf}
    for slot in range(4):
        curves=[('core',core+[xx[slot]-xx[0],0.,0.],meta['curve_error_mm']),
                ('tail',PW_OLD_TAILS[slot],tail_error),
                ('fan',pw_fans[slot][0],pw_fan_errors[slot]),
                ('body',body_samples[slot+1,0][0],body_error)]
        for kind,p,error in curves:
            half=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())/2
            for q in p:
                v=tree.find_nearest(Vector(q));bound=float(v[3])-half-error-OD/2-.0001
                if bound<best['gap_lower_bound_mm']:
                    best={'gap_lower_bound_mm':bound,'slot':slot,'route':kind,'point_mm':q.tolist(),
                          'nearest_tail_mm':list(v[0]),'half_step_mm':half,'curve_error_mm':error}
    best['status']='PASS' if best['gap_lower_bound_mm']>=.3 else 'BLOCKED'
    return best

tv_a=np.load(tv_mesh);tv_f=tv_a['triangles'];tv_v=tv_a['vertices_mm']
tv_edges=np.sort(np.vstack([tv_f[:,[0,1]],tv_f[:,[1,2]],tv_f[:,[2,0]]]),axis=1)
_,tv_counts=np.unique(tv_edges,axis=0,return_counts=True)
tv_geom={'status':'PASS' if np.all(tv_counts==2) and len(tv_m.decompose())==1 else 'FAIL',
         'components':len(tv_m.decompose()),'non_two_face_edges':int(np.sum(tv_counts!=2)),
         'volume_mm3':float(tv_m.volume()),'analytic_strip_volume_mm3':110.*1.3*2.7}
tv_nominal={'fixture':st_hits(tv_m,tr_targets),'wires':st_wire_hits(tv_m,0.),
            'rigid_excluding_start_contact':st_hits(tv_m,tv_without_contact),'wire_gap':tv_wire_gap(tv_m)}
tv_rows=[]
# These +/-0.5mm perturbations and extra0.2mm cross-section are a declared
# geometric robustness check, not a supplier tolerance or material rating.
tr_width=2.9;tr_thickness=1.5
for initial,column in itertools.product([3.5,4.,4.5],[-34.5,-34.,-33.5]):
    m,p,meta=tr_shape(initial,5.,column)
    fixture=st_hits(m,tr_targets);wires=st_wire_hits(m,0.)
    row={'initial_straight_mm':initial,'column_x_mm':column,
         'fixture':fixture,'wires':wires,
         'status':'PASS' if fixture['status']==wires['status']=='PASS' else 'BLOCKED'}
    if row['status']=='PASS':
        row['wire_gap']=tv_wire_gap(m);row['rigid_excluding_start_contact']=st_hits(m,tv_without_contact)
        row['status']=row['wire_gap']['status']
    tv_rows.append(row)
    print('TAIL_ROBUSTNESS',initial,column,row['status'],row.get('wire_gap'),flush=True)
tv_result={'status':'PASS' if tv_geom['status']=='PASS' and all(r['status']=='PASS' for r in tv_nominal.values()) and all(r['status']=='PASS' for r in tv_rows) else 'BLOCKED',
    'scope':'Stored strip mesh replay plus nine declared temporary-routing perturbations; no full threading or tightening approval',
    'source_main_sha256':source_hash,'script_sha256':sha(TV_SCRIPT),'helper_sha256':sha(TV_HELPER),
    'source_screen_sha256':sha(tv_input),'source_tail_sha256':sha(tv_mesh),
    'selected_candidate':tv_selected,'geometry':tv_geom,'nominal':tv_nominal,
    'perturbation_width_mm':tr_width,'perturbation_thickness_mm':tr_thickness,
    'sensitivity_rows':tv_rows,'required_wire_gap_mm':.3,
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
    'full_threading_tightening':'NOT_TESTED','material_bend_force':'NOT_TESTED'}
(TR_OUT/'verification.json').write_text(json.dumps(tv_result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('TAIL_REPLAY_DONE',tv_result['status'],tv_nominal,flush=True)
