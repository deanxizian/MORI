"""Try contact roll and a small guide offset inside unchanged neck prints.

This is a finite alternative-position search. It is neither a new printed
cut nor a completed wire-deformation/continuous-motion certificate.
"""
from pathlib import Path
SEARCH_SCRIPT=Path(__file__).resolve(); SEARCH_HELPER=SEARCH_SCRIPT.parent/'screen_CAM_neck_contact_consistency.py'
__file__=str(SEARCH_HELPER)
exec(compile(SEARCH_HELPER.read_text().split('\nallocations=',1)[0],str(SEARCH_HELPER),'exec'),globals())
__file__=str(SEARCH_SCRIPT)
SEARCH=NECK/'pose_search';SEARCH.mkdir(exist_ok=True)
dims=np.array([1.,1.8,4.1]);nominal=manifold.Manifold.cube(dims.tolist(),center=True)
padded=nominal.minkowski_sum(manifold.Manifold.sphere(.3,48))
started=time.time();rows=[];passed=[]
def check_path(r0,roll,phase,ids):
    p,segs=radial_path(r0,step=.08); ph=math.radians(phase);rho=math.radians(roll)
    er=np.array([math.cos(ph),math.sin(ph),0.]);ez=np.array([0.,0.,1.]);et=np.cross(ez,er)
    for idx,(r,z,a) in enumerate(p):
        axis=er*math.sin(a)+ez*math.cos(a);x=er*math.cos(a)-ez*math.sin(a)
        xr=math.cos(rho)*x+math.sin(rho)*et;yr=-math.sin(rho)*x+math.cos(rho)*et
        rear=r*er+z*ez;T=np.column_stack([xr,yr,axis,rear+dims[2]/2*axis]);m=padded.transform(T);bb=np.array(m.bounding_box())
        for name in ids:
            tb=target_boxes[name]
            if np.any(bb[:3]>tb[3:]) or np.any(tb[:3]>bb[3:]):continue
            v=max(0.,float((m^targets[name]).volume()))
            if v>1e-5:return dict(status='BLOCKED',index=idx,checked_positions=idx+1,phase_deg=phase,
                segment=segs[idx],obstacle=name,padded_intersection_mm3=v,rear_mm=rear.tolist(),transform_3x4=T.tolist())
    return dict(status='PASS',phase_deg=phase,checked_positions=len(p))
for r0 in (7.6,7.65,7.7,7.75,7.8,7.55,7.5):
    for roll in (0.,15.,30.,45.,60.,75.,90.):
        pre=check_path(r0,roll,45,['Yaw_Base','Pitch_Yoke','Yaw_Reaction_Link'])
        row=dict(guide_radius_mm=r0,contact_roll_deg=roll,prefilter=pre,full_source_cases=[],status=pre['status'])
        if pre['status']=='PASS':
            for phase in [45,135,225,315]:
                c=check_path(r0,roll,phase,list(targets));row['full_source_cases'].append(c)
                if c['status']!='PASS':row['status']='BLOCKED';break
        rows.append(row)
        if row['status']=='PASS':passed.append(row)
        print('LARGER_NECK_POSE',r0,roll,row['status'],pre.get('obstacle'),pre.get('index'),flush=True)
    if passed:break
report=dict(status='PASS' if passed else 'BLOCKED',scope='Finite contact-only alternative poses inside unchanged neck prints',
    script_sha256=sha(SEARCH_SCRIPT),helper_sha256=sha(SEARCH_HELPER),source_main_sha256=source_hash,
    source_consistency_sha256=sha(NECK/'screen.json'),protected_sources=protected,
    contact_dimensions_mm=dims.tolist(),contact_evidence='ASSUMED requested space, not maximum crimped dimensions',
    clearance_padding_mm=.3,rows=rows,passing_candidates=len(passed),
    trailing_wire_and_transition='NOT_TESTED',continuous_motion='NOT_TESTED',
    no_universal_impossibility_claim=True,geometry_changes=[],main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-started)
(SEARCH/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('LARGER_NECK_POSE_DONE',report['status'],len(rows),len(passed),round(time.time()-started,2),flush=True)
