"""Independent final34 insert checks and bounded M1.41 geometry comparison."""
from common import *
from validate import Solid,rigidtr,broad
from export import topology
import itertools

def run():
    load_collections();
    for name in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[name].hide_viewport=False
    assembled();bpy.context.view_layer.update()
    q=P['interface_completion'];c={'rows':q['inserts']};f={r['id']:r for r in json.loads((ROOT/'studies/interface_completion/fastener_current.json').read_text())};out=[]
    ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']};changed={r['host'] for r in c['rows']}|{'Head_Rear'}|({q['socket_screw']['id']} if q.get('socket_screw') else set())
    for r in c['rows']:
     s=ss[r['host']];b=s.bvh();e=np.array(r['entry_mm']);a=np.array(r['outward']);u=np.cross(a,[1,0,0] if abs(a[0])<.9 else [0,1,0]);u/=np.linalg.norm(u);v=np.cross(a,u);walls=[];broken=0
     for z in np.linspace(.25,r['length_mm']+.15,5):
      for th in np.arange(0,360,5):
       d=u*math.cos(math.radians(th))+v*math.sin(math.radians(th));origin=e-a*z
       hits=s.m.ray_cast(origin.tolist(),(origin+d*300).tolist());clean=[]
       for hit in hits:
        if not clean or abs(hit.distance-clean[-1].distance)>1e-7:clean.append(hit)
       if len(clean)<2 or np.dot(clean[0].normal,d)>=0 or np.dot(clean[1].normal,d)<=0:broken+=1;continue
       walls.append((clean[1].distance-clean[0].distance)*300)
     fh=s.m.ray_cast((e+a*.01).tolist(),(e-a*100).tolist());fdist=fh[0].distance*100.01-.01 if fh else None;bottom=[]
     if fh:
      for x,y in [(0,0),(.7,0),(-.7,0),(0,.7),(0,-.7)]:
       pos=np.array(fh[0].position)+u*x+v*y-a*.01
       bh=s.m.ray_cast(pos.tolist(),(pos-a*100).tolist())
       if bh:bottom.append(float(bh[0].distance*100+.01))
     fd=f[r['screw']];face=np.array(fd['tool_start_mm'])-np.array(fd['extracted_axis_outward'])*fd['nominal_head_height_mm'];length=fd['nominal_shank_length_mm'];tip=face-a*length
     if 'screw_length_mm' in r:face=np.array(r['screw_head_bearing_mm']);length=r['screw_length_mm'];tip=face-a*length
     if r.get('head_seam_move_pending',False) and 'screw_length_mm' not in r:face[0]=e[0];face[2]+=2;tip=face-a*length
     penetration=float(np.dot(e-tip,a));engagement=max(0,min(penetration-.2,r['length_mm']))
     minwall=min(walls) if walls else 0;mincap=min(bottom) if bottom else None
     mouth_blocks=[]
     for fraction in [0,.5,.95]:
      for th in range(0,360,5):
       offset=(u*math.cos(math.radians(th))+v*math.sin(math.radians(th)))*r['pilot_mm']/2*fraction
       origin=e+a*.6+offset;end=e-a*(r['pilot_depth_mm']+1)+offset
       hs=s.m.ray_cast(origin.tolist(),end.tolist())
       if hs:
        depth=hs[0].distance*(r['pilot_depth_mm']+1.6)-.6
        if depth<r['pilot_depth_mm']-.01:mouth_blocks.append({'radius_fraction':fraction,'angle':th,'first_material_depth_mm':depth})
     row={'id':r['id'],'host':r['host'],'min_sampled_pilot_wall_mm':minwall,'required_wall_mm':1.6 if r['OD_mm']==4.6 else 1.3,'radial_samples':len(walls),'broken_radial_samples':broken,'first_axial_material_depth_mm':fdist,'sampled_blind_end_wall_mm':mincap,'screw_insertion_below_seating_face_mm':penetration,'nominal_thread_engagement_mm':engagement,'screw_tip_to_first_axial_material_mm':fdist-penetration if fdist is not None else None,'entry_blocked_rays':mouth_blocks,'entry_axial_samples':216}
     row['status']='PASS' if minwall>=row['required_wall_mm']-.01 and not broken and not mouth_blocks and (mincap is None or mincap>=1.0) and engagement>=2.4 and (row['screw_tip_to_first_axial_material_mm'] is None or row['screw_tip_to_first_axial_material_mm']>=.15) else 'FAIL'
     out.append(row)
    tops=[]
    for n in sorted(changed):
     s=ss[n];t=topology(s.v.tolist(),s.f.tolist());t.update(id=n,positive_components=sum(p.volume()>.001 for p in s.m.decompose()));tops.append(t)
    collisions=[]
    for n in changed:
     for k,s in ss.items():
      if k==n:continue
      if 'Insert' in k:
       own=next((r for r in c['rows'] if r['id']==k),None)
       if own and own['host']==n:continue # Only specified installed knurl/host interference.
      v=max(0,(ss[n].m^s.m).volume()) if broad(ss[n],s) else 0
      if v>.02:collisions.append({'a':n,'b':k,'volume_mm3':v})
    motion=[]
    for yaw in range(-60,61,10):
     ys={n:Solid(s.o,s,rigidtr(yaw,0)) if s.group=='yaw' else s for n,s in ss.items() if s.group!='pitch'}
     for pitch in range(-20,26,5):
      poses={**ys,**{n:Solid(s.o,s,rigidtr(yaw,pitch)) for n,s in ss.items() if s.group=='pitch'}}
      for n in changed:
       for k,s in poses.items():
        if k==n or s.group==poses[n].group:continue
        if broad(poses[n],s):
         v=max(0,(poses[n].m^s.m).volume())
         if v>.02:motion.append({'yaw':yaw,'pitch':pitch,'a':n,'b':k,'overlap_mm3':v})
     print('INSERT_MOTION',yaw,flush=True)
    report={'status':'PASS' if all(r['status']=='PASS' for r in out) and not collisions and not motion and all(r['positive_components']==1 for r in tops) else 'FAIL','main_updated':False,'rows':out,'topology':tops,'collisions':collisions,'poses':130,'motion_collisions':motion,'limits':'Finite nominal rigid geometry, manufacturer pilot-wall guideline only; strength, PA12 interference, creep and screw torque require coupon/physical tests. Own installed insert/host crest interference explicitly excluded only for each named pair.'}
    from validate_head_cleanup import geometry_record
    from interface_completion import change_regions
    baseline=json.loads((PROJECT/q['baseline_geometry']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changes=sorted(n for n in now if n in baseline['parts'] and now[n]!=baseline['parts'][n])
    scope={'changed':changes,'unexpected_changed':sorted(set(changes)-set(q['changed_existing_ids'])),'declared_but_unchanged':sorted(set(q['changed_existing_ids'])-set(changes)),'added':sorted(set(now)-set(baseline['parts'])),'retired':sorted(set(baseline['parts'])-set(now))}
    deltas=[]
    for n,zone in change_regions().items():
     b=baseline[n];old=manifold.Manifold(manifold.Mesh64(np.array(b['vertices_mm']),np.array(b['triangles'],dtype=np.uint64)))
     new=ss[n].m;add=new-old;remove=old-new
     deltas.append({'id':n,'added_mm3':max(0,add.volume()),'removed_mm3':max(0,remove.volume()),'outside_declared_region_mm3':max(0,(add-zone).volume())+max(0,(remove-zone).volume())})
    tool={'status':'NOT_APPLICABLE'}
    if q.get('socket_screw'):
        from interface_completion import axial
        r=q['socket_screw'];p=np.array(r['bearing_mm'])+np.array(r['outward'])*(r['head_height_mm']-.7);a=np.array(r['outward'])
        # PB210.1,5 published50x14mm envelope; circumscribed0.87 radius
        # bounds the1.5AF hex shaft. Use long leg in the screw before yaw assembly.
        m=axial(.87,50,p+a*25,a)+axial(.87,14,p+a*50+[0,7,0],[0,1,0])+manifold.Manifold.sphere(.87,32).translate((p+a*50).tolist())
        bench={n:ss[n] for n in ss if n.startswith(('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_')) and n!=r['id']};hits=[]
        for angle in range(-120,121,2):
            tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-Vector(p));shape=m.transform(np.array(tr)[:3,:]);bb=np.array(shape.bounding_box())
            for n,t in bench.items():
                if np.any(bb[3:]<t.lo) or np.any(t.hi<bb[:3]):continue
                v=max(0,(shape^t.m).volume())
                if v>.02:hits.append({'angle':angle,'part':n,'mm3':v})
        good=[angle for angle in range(-120,121,2) if not any(h['angle']==angle for h in hits)];longest=0;run=0
        for angle in range(-120,121,2):
            run=run+2 if angle in good else 0;longest=max(longest,run)
        tool={'status':'PASS' if longest>=60 else 'FAIL','screw':r['id'],'source_url':r['tool_source_url'],'published_key_mm':[1.5,50,14],'method':'Long leg inserted0.7mm; finite2deg sweep; conservative circular shaft. Require at least60deg continuous sampled clear interval for hex reindexing. Detached yoke only. Hand/torque and actual bend NOT_TESTED.','clear_sampled_span_deg':longest,'hits':hits}
    report.update(main_updated=True,revision=P['revision'],scope=scope,local_deltas=deltas,lower_pitch_tool=tool)
    if tool['status']=='FAIL':report['status']='FAIL' 
    if any(scope[k] for k in ['unexpected_changed','declared_but_unchanged','added','retired']) or any(r['outside_declared_region_mm3']>.02 for r in deltas):report['status']='FAIL'
    save_json(ROOT/'reports/interface_validation.json',report)
    print('INTERFACE_CHECK',report['status'],scope,flush=True)
    return report

if __name__=='__main__':run()
