"""Catalogue insert interfaces and the approved paired head-seam relocation.

Dimensions live in geometry.json. This late construction phase replaces only
named generator-owned meshes, leaving hardware-owned/native PCB files untouched.
"""
from common import *
from validate import Solid
from layout_cleanup import mm_mesh
from monocoque_structure import obj,source_build
from structural_simplification import hardware
from purchased_geometry import remove_generated
import collections

def axial(radius,height,center,axis,segments=96):
    tr=Matrix.Translation(Vector(center))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
    return manifold.Manifold.cylinder(height,radius,radius,segments,center=True).transform(np.array(tr)[:3,:])

def replace_owned(name,m):
    o=obj(name)
    if o.get('mori_owner')!=OWNER:raise RuntimeError('Refusing to replace unowned '+name)
    mats=list(o.data.materials);temp=mm_mesh('interface_construction_mesh',m.simplify(.0005))
    o.data=temp.data.copy();o.data.materials.clear()
    for material in mats:o.data.materials.append(material)
    o.matrix_world=Matrix.Identity(4);SOLIDS.pop(o.name,None);bpy.data.objects.remove(temp,do_unlink=True)
    return o

def change_regions():
    """Bound every local edit independently from its Boolean construction."""
    q=P['interface_completion'];regions={}
    for r in q['inserts']:
        e=np.array(r['entry_mm']);a=np.array(r['outward'])
        radius=max(r.get('seat_width_mm',0)*.71,r['pilot_mm']/2+q['bore_restore_radial_overlap_mm'],r.get('blind_cap_extension',{}).get('radius_mm',0))+.02
        depth=max(r['restore_depth_mm'],r['pilot_depth_mm'],r.get('blind_cap_extension',{}).get('center_depth_mm',0)+r.get('blind_cap_extension',{}).get('height_mm',0)/2)+.04
        outward=r.get('pilot_mouth_extension_mm',.02)+.02
        zone=axial(radius,depth+outward,e-a*(depth-outward)/2,a)
        regions[r['host']]=regions.get(r['host'],manifold.Manifold())+zone
    h=q['head_seam']
    for n in ['Head_Front','Head_Rear']:
        for sign in [-1,1]:
            for x,z in [(h['old_abs_x_mm'],h['old_z_from_head_mm']),(h['abs_x_mm'],h['z_from_head_mm'])]:
                regions[n]=regions.get(n,manifold.Manifold())+axial(h['lug_radius_mm']+.02,85,[sign*x,-10,D['head_z']+z],[0,1,0])
    # Moving the seam lug intersects existing vertical counterbores. Reopen
    # the identical nominal radius/axis (96 facets vs historical64); bound
    # this local retessellation explicitly instead of waiving whole-shell drift.
    h=P['readiness_completion']['head_shell']
    for sign in [-1,1]:
        x,y=head_shell_mount_xy_mm(sign)
        regions['Head_Front']+=axial(h['counterbore_radius_mm']+.01,90,[x,y,D['head_z']+47],[0,0,1])
    # Subsequent approved repairs are bounded separately and independently
    # checked against the immutable M1.42 mesh by validate_assembly_issue_fixes.
    if P.get('assembly_issue_fixes',{}).get('enabled'):
        from assembly_issue_fixes import change_regions as later_regions
        for n,zone in later_regions().items():
            regions[n]=regions.get(n,manifold.Manifold())+zone
    if P.get('head_axial_retention',{}).get('enabled'):
        from head_axial_retention import change_region
        for n in P['head_axial_retention']['changed_existing_ids']:
            regions[n]=regions.get(n,manifold.Manifold())+change_region()
    return regions

def move_head_seam(q):
    b=source_build();o=b.sphere('interface_mother',(0,0,D['head_z']),D['head_radius']);mother=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True)
    o=b.sphere('interface_inner',(0,0,D['head_z']),D['head_radius']-P['shell_thickness_mm']);inner=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True);shell=mother-inner
    for sign in [-1,1]:
        old=np.array([sign*q['old_abs_x_mm'],0,D['head_z']+q['old_z_from_head_mm']]);new=np.array([sign*q['abs_x_mm'],0,D['head_z']+q['z_from_head_mm']])
        for name,y,depth in [('Head_Front',q['front_lug_y_mm'],q['front_lug_depth_mm']),('Head_Rear',q['rear_lug_y_mm'],q['rear_lug_depth_mm'])]:
            p=old+np.array([0,y,0]);pm=Solid(obj(name)).m;oldlug=axial(q['lug_radius_mm'],depth,p,[0,1,0])^mother
            oldbore=axial(q['restore_old_bore_radius_mm'],60,old+[0,-10,0],[0,1,0])
            half=manifold.Manifold.cube([200,100,200],True).translate([0,50.3 if name=='Head_Front' else -50.3,D['head_z']])
            pm=(pm+(oldbore^shell^half))-(oldlug^inner)
            pm=pm+(axial(q['lug_radius_mm'],depth,new+[0,y,0],[0,1,0])^mother)
            if name=='Head_Rear':
                pm=pm-axial(q['rear_clearance_radius_mm'],30,new+[0,-10,0],[0,1,0])
                pm=pm-axial(q['rear_head_recess_radius_mm'],45,new+[0,-35,0],[0,1,0])
            else:
                h=P['readiness_completion']['head_shell'];x,y2=head_shell_mount_xy_mm(sign);seat=D['head_z']+h['head_seat_z_from_head_mm']
                pm=pm-axial(h['clearance_radius_mm'],60,[x,y2,D['head_z']+47],[0,0,1])
                pm=pm-axial(h['counterbore_radius_mm'],50,[x,y2,seat+25],[0,0,1])
            replace_owned(name,pm)

def apply_interface_completion():
    q=P.get('interface_completion',{})
    if not q.get('enabled'):return
    assembled();bpy.context.view_layer.update();move_head_seam(q['head_seam'])
    from assembly_issue_fixes import relocate_body_seam
    relocate_body_seam()
    rows=[]
    for r in q['inserts']:
        host=obj(r['host']);hm=Solid(host).m;e=np.array(r['entry_mm']);axis=np.array(r['outward']);depth=r['pilot_depth_mm'];pilot=r['pilot_mm'];length=r['length_mm']
        if r.get('seat_width_mm'):
            width=r['seat_width_mm'];tr=Matrix.Translation(Vector(e-axis*depth/2))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
            seat=manifold.Manifold.cube([width,width,depth],True) if r['seat_shape']=='square' else manifold.Manifold.cylinder(depth,width/2,width/2,96,center=True)
            hm=hm+seat.transform(np.array(tr)[:3,:])
        hm=hm+axial(pilot/2+q['bore_restore_radial_overlap_mm'],r['restore_depth_mm'],e-axis*r['restore_depth_mm']/2,axis)
        if r.get('blind_cap_extension'):
            c=r['blind_cap_extension'];hm=hm+axial(c['radius_mm'],c['height_mm'],e-axis*c['center_depth_mm'],axis)
        # A seam lug begins at Y0.30 but adjacent spherical skin begins at
        # Y0.20. Extend the cutter through that entry skin, without changing
        # the insert seating plane or the blind bottom depth.
        mouth=r.get('pilot_mouth_extension_mm',.02)
        hm=hm-axial(pilot/2,depth+mouth,e-axis*(depth-mouth)/2,axis)
        replace_owned(r['host'],hm)
        mid=e-axis*(length/2+q['insert_recess_mm']);remove_generated(r['id']);m=axial(r['OD_mm']/2,length,mid,axis)-axial(r['thread_major_mm']/2,length+.1,mid,axis)
        o=mm_mesh(r['id'],m);hardware(o,r['sku']+' / 目录尺寸基准',host.get('group'))
        o['data_status']='VENDOR_DOCUMENTED';o['model_fidelity']='CATALOGUE_MAXIMUM_ENVELOPE; knurl and thread helix omitted';o['source_url']=q['insert_source'];o['measured_unit']=False
        source_build().contact(r['id'],r['host'],'Selected insert knurl/pilot interference: catalogue nominal envelope, actual heat-set process and pull-out NOT_TESTED')
        if r.get('screw_length_mm'):
            face=np.array(r['screw_head_bearing_mm']);sl=r['screw_length_mm'];radius=r['head_diameter_mm']/2;hh=r['head_height_mm']
            bolt=axial(r['thread_major_mm']/2,sl,face-axis*sl/2,axis)+axial(radius,hh,face+axis*hh/2,axis)
            o=replace_owned(r['screw'],bolt);o['label_zh']='GB/T823 M2×'+str(sl);o['data_status']='VENDOR_DOCUMENTED';o['model_fidelity']='DIMENSIONED_ENVELOPE; drive recess and thread helix omitted';o['source_url']=q['M2_screw_source']
        rows.append(r)
    r=q.get('socket_screw')
    if r:
        e=np.array(r['bearing_mm']);a=np.array(r['outward']);h=r['head_height_mm'];length=r['length_mm']
        # Extend the shank 0.02 mm inside its own head so independently
        # transformed coincident end faces cannot split the reference screw.
        # The documented shank tip, head bearing plane and outer bounds stay put.
        bolt=axial(1,length+.02,e-a*(length-.02)/2,a)+axial(r['head_diameter_mm']/2,h,e+a*h/2,a)
        socket=axial(r['drive_AF_mm']/math.sqrt(3),r['drive_depth_mm']+.02,e+a*(h-r['drive_depth_mm']/2+.01),a,segments=6)
        o=replace_owned(r['id'],bolt-socket);o['label_zh']=r['specification'];o['data_status']='VENDOR_DOCUMENTED';o['model_fidelity']='Documented nominal outer envelope and1.5AF socket; thread helix omitted';o['source_url']=r['source_url']
    for name in q['head_transmission_deferred_ids']:
        o=obj(name);o['interface_status']='BLOCKED: retain SCS0009; awaiting matching factory horn drawing. Existing geometry remains an allocation.'
    cleanup=[]
    for name in {r['host'] for r in rows}|{'Head_Rear'}:
        o=obj(name);m=Solid(o).m.set_tolerance(.00005).simplify(.00005);d=m.to_mesh64()
        v=np.asarray(d.vert_properties[:,:3],dtype=np.float32).astype(float);f=np.array(d.tri_verts,dtype=np.int64)
        v,f,operations,bad=repair_quantized_triangles(v,f)
        if bad:raise RuntimeError('Unrepaired mesh degeneracy: '+name)
        m=manifold.Manifold(manifold.Mesh64(np.array(v,dtype=np.float64,order='C'),np.array(f,dtype=np.uint64,order='C')))
        if m.status()!=manifold.Error.NoError:raise RuntimeError('Invalid cleanup: '+name)
        mats=list(o.data.materials);temp=mm_mesh('interface_export_mesh',m);o.data=temp.data.copy();o.data.materials.clear()
        for material in mats:o.data.materials.append(material)
        o.matrix_world=Matrix.Identity(4);SOLIDS.pop(o.name,None);bpy.data.objects.remove(temp,do_unlink=True)
        cleanup.append({'id':name,'operations':operations,'max_edge_collapse_mm':max([r.get('length_mm',0) for r in operations] or [0]),'kernel_simplification_tolerance_mm':.00005})
    save_json(ROOT/'reports/interface_mesh_cleanup.json',cleanup)
    from readiness_completion import paint_integral_rim
    paint_integral_rim()
    path=ROOT/'reports/readiness_geometry.json';report=json.loads(path.read_text())
    for row in report['head']:
        r=next((v for v in rows if v['screw']==row['id']),None)
        if r and r.get('screw_head_bearing_mm'):
            row['head_bearing_mm']=r['screw_head_bearing_mm'];row['axis']=(-np.array(r['outward'])).tolist()
            row['interface_revision']=P['revision']
    save_json(path,report)
    save_json(ROOT/'reports/interface_completion.json',{'revision':P['revision'],'status':'GENERATED_PENDING_VALIDATION','inserts':rows,'head_seam':q['head_seam'],'head_transmission':'BLOCKED: user retains SCS0009 and explicitly defers horn compatibility to manufacturer documentation','native_PCB_changed':False,'manufacturing_release':False})
    print('INTERFACE_COMPLETION',len(rows),'catalogue inserts',flush=True)


def repair_quantized_triangles(v,faces):
 v=np.array(v);faces=np.array(faces,dtype=np.int64);history=[]
 for it in range(1000):
  bad=[]
  for i,ids in enumerate(faces):
   a,b,c=[Vector(v[j]) for j in ids]
   if (b-a).cross(c-a).length<1e-8 or len(set(ids))<3:bad.append(i)
  if not bad:break
  edgefaces=collections.defaultdict(list);neighbors=collections.defaultdict(set)
  for i,ids in enumerate(faces):
   for j in range(3):
    a,b=ids[j],ids[(j+1)%3];edgefaces[tuple(sorted([a,b]))].append(i);neighbors[a].add(b);neighbors[b].add(a)
  changed=False
  for idx in bad:
   t=faces[idx];edges=sorted([(np.linalg.norm(v[t[j]]-v[t[(j+1)%3]]),t[j],t[(j+1)%3],t[(j+2)%3]) for j in range(3)])
   length,a,b,c=edges[0]
   if length<.00051 and len(neighbors[a]&neighbors[b])==2:
    faces[faces==b]=a;faces=np.array([f for f in faces if len(set(f))==3]);history.append({'kind':'edge_collapse','length_mm':float(length)});changed=True;break
   length,a,b,c=edges[-1];adj=edgefaces[tuple(sorted([a,b]))]
   if len(adj)!=2:continue
   k=next(k for k in adj if k!=idx);d=next((x for x in faces[k] if x not in [a,b]),None)
   if d is None or d==c or tuple(sorted([c,d])) in edgefaces:continue
   # C lies on AB. Replace the zero-area triangle and its neighbour by AC-D and CB-D.
   old=np.array([faces[idx],faces[k]]);faces[idx]=[c,d,b];faces[k]=[d,c,a];history.append({'kind':'zero_area_diagonal_flip','old':old.tolist(),'new':[faces[idx].tolist(),faces[k].tolist()]});changed=True;break
  if not changed:break
 return v,faces,history,bad
