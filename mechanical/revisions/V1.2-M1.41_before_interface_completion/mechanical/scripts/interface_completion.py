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
        hm=hm-axial(pilot/2,depth+.02,e-axis*(depth-.02)/2,axis)
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
    for name in q['head_transmission_deferred_ids']:
        o=obj(name);o['interface_status']='BLOCKED: retain SCS0009; awaiting matching factory horn drawing. Existing geometry remains an allocation.'
    save_json(ROOT/'reports/interface_completion.json',{'revision':P['revision'],'status':'GENERATED_PENDING_VALIDATION','inserts':rows,'head_seam':q['head_seam'],'head_transmission':'BLOCKED: user retains SCS0009 and explicitly defers horn compatibility to manufacturer documentation','native_PCB_changed':False,'manufacturing_release':False})
    print('INTERFACE_COMPLETION',len(rows),'catalogue inserts',flush=True)
