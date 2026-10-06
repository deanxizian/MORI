"""Screen sequence choices without changing any model or tool dimensions.

Rotate the same bounded cutter around the free-tail axis. Identify whether
moving the CAM/cradle or deferring the yaw servo changes the access result.
This only allocates tool solids, not hands, closing forces, or flexible ties.
"""
from pathlib import Path
ST_SCRIPT=Path(__file__).resolve();ST_ROOT=ST_SCRIPT.parent
ST_HELPER=ST_ROOT/'check_CAM_wired_cradle_insertion.py';__file__=str(ST_HELPER)
exec(compile(ST_HELPER.read_text().split('\nwi_rows=[];',1)[0],str(ST_HELPER),'exec'),globals())
__file__=str(ST_SCRIPT)
ST_OUT=ST_ROOT/'cam_wired_cradle';ST_OUT.mkdir(exist_ok=True)
st_tool=pw_readsolid(ST_ROOT/'cam_tie_install/cutter_allocation.npz')
st_sweep=pw_readsolid(ST_ROOT/'cam_tie_install/cutter_swept.npz')
st_tail=pw_readsolid(ST_ROOT/'cam_tie_install/tail_corridor.npz')
st_head=pw_readsolid(ST_ROOT/'cam_tie_install/oriented_head.npz')
st_pivot=np.array([float(xx.max()+1.2)+.5+2.6,float(st_head.bounding_box()[4])+.25,232.-2.7/2])
st_defer={n for n in wi_fixed if n.startswith('Head_Yaw_Ear_') or n in ['Yaw_Servo','Yaw_Output','Yaw_Horn','Yaw_Lock_Screw']}

def st_hits(m,targets):
    hits=[];gap={'gap_mm':3.,'object':None}
    for n,target in targets.items():
        if not overlap_boxes(m,target,3.):continue
        volume=max(0.,float((m^target).volume()))
        if volume>1e-5:hits.append({'object':n,'intersection_mm3':volume})
        d=float(m.min_gap(target,3.))
        if d<gap['gap_mm']:gap={'gap_mm':d,'object':n}
    return {'status':'BLOCKED' if hits else 'PASS','hits':hits,'nearest_below_3mm':gap}

def st_wire_hits(m,lift):
    mesh=m.to_mesh64();bb=np.array(m.bounding_box())
    tree=BVHTree.FromPolygons(mesh.vert_properties[:,:3],mesh.tri_verts.tolist(),all_triangles=True)
    core,meta=wi_core(lift);hits=[]
    for slot in range(4):
        routes=[('core',core+[xx[slot]-xx[0],0.,0.],meta['curve_error_mm']),
                ('tail',PW_OLD_TAILS[slot]+[0.,0.,lift],tail_error),
                ('fan',pw_fans[slot][0],pw_fan_errors[slot]),
                ('body',body_samples[slot+1,0][0],body_error)]
        for kind,p,error in routes:
            hit=check_one(p,error,bb[:3],bb[3:],m,tree)
            if hit:hits.append({'slot':slot,'route':kind,**hit})
    return {'status':'BLOCKED' if hits else 'PASS','hits':hits}

st_rows=[];st_start=time.time()
for lift in [0.,6.,12.]:
    moving={n:m.translate([0.,0.,lift]) for n,m in wi_moving.items()}
    for defer in [False,True]:
        targets={n:m for n,m in wi_fixed.items() if not (defer and n in st_defer)}|moving
        tailfit=st_hits(st_tail,targets)
        for angle in [0.,-90.,90.,180.,-45.,45.,-135.,135.]:
            def orient(m):return m.translate((-st_pivot).tolist()).rotate([0.,angle,0.]).translate(st_pivot.tolist())
            tool=orient(st_tool);sweep=orient(st_sweep)
            fit=st_hits(sweep,targets)
            wires=st_wire_hits(sweep,lift) if fit['status']=='PASS' else {'status':'NOT_TESTED'}
            row={'lift_mm':lift,'yaw_servo_deferred':defer,'angle_deg':angle,'fixture':fit,
                 'tail_corridor':tailfit,'prescribed_wires':wires,
                 'status':'PASS' if fit['status']==tailfit['status']==wires['status']=='PASS' else 'BLOCKED'}
            st_rows.append(row)
            if row['status']=='PASS':cache(ST_OUT/f'yaw_tool_lift{lift}_{angle}.npz',tool);cache(ST_OUT/f'yaw_sweep_lift{lift}_{angle}.npz',sweep)
            print('SEQUENCE_TOOL',lift,defer,angle,row['status'],[r['object'] for r in fit['hits']],wires['status'],flush=True)
st_result={'status':'PASS' if any(r['status']=='PASS' for r in st_rows) else 'BLOCKED',
    'scope':'Same sourced bounded cutter at eight roll angles, three CAM/cradle elevations, and two explicitly listed servo stages',
    'source_main_sha256':source_hash,'script_sha256':sha(ST_SCRIPT),'helper_sha256':sha(ST_HELPER),
    'deferred_yaw_parts':sorted(st_defer),'fixture_ids':list(wi_fixed|wi_moving),'already_excluded_pitch_parts':wi_excluded,
    'rows':st_rows,'pivot_mm':st_pivot.tolist(),'main_applied':False,'manufacturing_release':False,
    'hands_forces_tie_latch':'NOT_TESTED','other_tools_or_paths':'NOT_TESTED','whole_harness':'BLOCKED','elapsed_s':time.time()-st_start}
(ST_OUT/'sequence_tools.json').write_text(json.dumps(st_result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('SEQUENCE_TOOLS_DONE',st_result['status'],flush=True)
