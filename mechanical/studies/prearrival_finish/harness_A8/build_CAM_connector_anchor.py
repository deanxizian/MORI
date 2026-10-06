"""Connect the local CAM departure clamp to the existing pitch cradle."""
from pathlib import Path
CC_SCRIPT=Path(__file__).resolve();CC_ROOT=CC_SCRIPT.parent
CC_HELPER=CC_ROOT/'screen_CAM_pitch_anchor_warp.py';__file__=str(CC_HELPER)
exec(compile(CC_HELPER.read_text().split('\npw_rows=[];',1)[0],str(CC_HELPER),'exec'),globals())
__file__=str(CC_SCRIPT);CC_OUT=CC_ROOT/'cam_pitch_anchor/connector_anchor';CC_Z=212.
cc_bed=pw_readsolid(CC_OUT/f'z{CC_Z}_bed.npz');cc_band=pw_readsolid(CC_OUT/f'z{CC_Z}_band.npz');cc_head=pw_readsolid(CC_OUT/f'z{CC_Z}_head.npz')
cc_host=next(r[2] for r in ob if r[0]=='Pitch_Cradle')
cc_raw=CC_HELPER.read_text().split('def pw_support_source',1)[1].split('\npw_rows=[];',1)[0]
exec(compile(('def cc_source'+cc_raw).replace("if name=='Display_Frame':continue","if name=='Pitch_Cradle':continue"),str(CC_SCRIPT),'exec'),globals())

def cc_wirefit(solid):
    bb=np.array(solid.bounding_box());a=solid.to_mesh64();tree=BVHTree.FromPolygons(a.vert_properties[:,:3],a.tri_verts.tolist(),all_triangles=True)
    counts=0
    # The only intended wire contact is the unchanged vertical CAM departure.
    for slot,x in enumerate(slots[:,0]):
        tube=manifold.Manifold.cylinder(5.,(OD/2+.001)/math.cos(math.pi/64),circular_segments=64).translate([float(x),float(slots[0,1]),float(slots[0,2]-5.)])
        volume=max(0.,float((tube^solid).volume()))
        if volume>1e-7:return {'status':'BLOCKED','type':'straight_overlap','slot':slot,'volume_mm3':volume}
    paths=[]
    for (slot,pitch),(samples,error) in loop_samples.items():
        inv=np.linalg.inv(np.asarray(rigidtr(0,pitch)));p=samples[0]@inv[:3,:3].T+inv[:3,3]
        paths.append((f'loop_{slot}_{pitch}',p,error,True))
    for pitch in range(-20,26,5):
        inv=np.linalg.inv(np.asarray(rigidtr(0,pitch)))
        for slot,sample in enumerate(pw_fans):paths.append((f'fan_{slot}_{pitch}',sample[0]@inv[:3,:3].T+inv[:3,3],pw_fan_errors[slot],False))
        for yaw in range(-60,61,10):
            invtotal=np.linalg.inv(np.asarray(rigidtr(yaw,pitch)))
            for pin in range(1,5):
                p=body_samples[pin,yaw][0];paths.append((f'body_{pin}_{yaw}_{pitch}',p@invtotal[:3,:3].T+invtotal[:3,3],body_error,False))
    for name,p,error,contact in paths:
        ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
        allowance=OD/2+.3+np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+error+1e-4
        ids=np.flatnonzero(np.all(p>=bb[:3]-allowance[:,None],axis=1)&np.all(p<=bb[3:]+allowance[:,None],axis=1))
        if contact:
            grip=(np.abs(p[:,1]-slots[0,1])<1e-5)&(p[:,2]>=slots[0,2]-5.-1e-5)&(p[:,2]<=slots[0,2]+1e-5)&(np.min(np.abs(p[:,0,None]-slots[:,0][None,:]),axis=1)<1e-5)
            ids=ids[~grip[ids]]
        for i in ids:
            distance=float(tree.find_nearest(Vector(p[i]))[3])
            if distance<allowance[i]:return {'status':'BLOCKED','type':'noncontact_gap','route':name,'point_mm':p[i].tolist(),'distance_mm':distance,'required_mm':float(allowance[i])}
        starts=ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
        for i in starts:
            tiny=manifold.Manifold.sphere(.01,16).translate(p[i].tolist())
            if (tiny^solid).volume()>tiny.volume()/2:return {'status':'BLOCKED','type':'inside','route':name}
        counts+=1
    return {'status':'PASS','routes_checked':counts,'grip_sweeps_checked':4,'contact_zone':'Original 5mm CAM departure only; subsequent curved portion has regular noncontact gap requirement',
        'physical_grip_and_pullout':'NOT_TESTED'}

cc_rows=[]
for cc_ymin in [-26.,-27.,-28.,-29.,-30.]:
    bb=np.array(cc_bed.bounding_box())
    root=box([bb[0],cc_ymin,bb[5]-.01],[bb[3],bb[4],216.2])
    addition=cc_bed+root;joined=cc_host+addition
    row={'root_y_min_mm':cc_ymin,'root_top_z_mm':216.2,'root_overlap_mm3':float((addition^cc_host).volume()),'combined_components':len(joined.decompose()),
       'bed_root_overlap_mm3':float((cc_bed^root).volume()),'tie_overlap_mm3':float(((cc_band+cc_head)^addition).volume())}
    if row['root_overlap_mm3']<1. or row['combined_components']!=1:row.update(status='BLOCKED',reason='no_structural_root')
    elif row['tie_overlap_mm3']>1e-5:row.update(status='BLOCKED',reason='tie_overlap')
    else:
        row['source']=cc_source(addition);row['status']=row['source']['status']
        if row['status']=='PASS':row['wires']=cc_wirefit(addition+cc_band+cc_head);row['status']=row['wires']['status']
    cc_rows.append(row);print('CONNECTOR_ROOT',row,flush=True)
    cache(CC_OUT/f'root_y{cc_ymin}_addition.npz',addition)
    if row['status']=='PASS':
        cache(CC_OUT/'addition.npz',addition);cache(CC_OUT/'Pitch_Cradle.npz',joined);break
cc_report={'status':'PASS' if any(r['status']=='PASS' for r in cc_rows) else 'BLOCKED',
    'scope':'Unapproved integral CAM straight-departure anchor and catalogue tie allocation; source/wire geometry only',
    'source_main_sha256':source_hash,'script_sha256':sha(CC_SCRIPT),'helper_sha256':sha(CC_HELPER),
    'source_clamp_report_sha256':sha(CC_OUT/'screen.json'),'rows':cc_rows,'source_part_count':len(ob),
    'changed_prints':['Pitch_Cradle'],'added_print_parts':0,'added_ties':1,'wires_relocated':False,
    'assembly':'NOT_TESTED','strength':'NOT_TESTED','physical_grip':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False}
(CC_OUT/'root_screen.json').write_text(json.dumps(cc_report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CONNECTOR_ROOT_DONE',cc_report['status'],flush=True)
