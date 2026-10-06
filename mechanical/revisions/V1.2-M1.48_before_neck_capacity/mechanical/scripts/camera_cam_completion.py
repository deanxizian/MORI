"""M1.48: two approved local changes, derived from the shared parameters."""
from common import *
from validate import Solid
from interface_completion import axial
from monocoque_structure import obj
from optics_mount import camera_transform, camera_pupil

def replace_exact(name, solid):
    o=obj(name)
    assert o.get('mori_owner')==OWNER
    mats=list(o.data.materials); data=solid.to_mesh64()
    me=bpy.data.meshes.new('M1_48_'+name)
    me.from_pydata(data.vert_properties[:,:3].tolist(),[],data.tri_verts.tolist());me.update()
    o.data=me; o.matrix_world=Matrix.Identity(4)
    for m in mats:me.materials.append(m)
    SOLIDS.pop(o.name,None)
    return o

def camera_cut():
    q=P['assembly_completion']['camera'];a=P['camera_cam_completion']['camera']
    rc=np.array(camera_transform().to_3x3())@np.array([[1.,0,0],[0,0,1.],[0,-1.,0]])
    tr=np.column_stack([rc,np.array(camera_pupil())]);wx,vy=q['pocket_outer_xy_mm']
    lo=np.array([-wx/2-.001,-vy/2-2,q['pocket_back_w_mm']-.001])
    hi=np.array([wx/2+.001,-vy/2+a['outside_top_trim_mm'],q['pocket_wall_front_w_mm']+.001])
    return manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist()).transform(tr)

def socket_solid(r):
    q=P['camera_cam_completion']['cam_screws'];a=np.array(r['outward']);b=np.array(r['screw_head_bearing_mm'])
    assert r['screw_length_mm']==q['length_mm'] and np.allclose(a,[0,1,0])
    h=q['head_height_mm'];length=q['length_mm']
    # 0.01mm internal overlap prevents coincident end faces; tip/bearing unchanged.
    m=axial(q['head_diameter_mm']/2,h,b+a*h/2,a)+axial(q['diameter_mm']/2,length+.01,b-a*(length-.01)/2,a)
    hole=manifold.Manifold.cylinder(q['socket_depth_mm']+.1,q['socket_AF_mm']/math.sqrt(3),q['socket_AF_mm']/math.sqrt(3),6)
    hole=hole.rotate([-90,0,0]).translate((b+a*(h-q['socket_depth_mm'])).tolist())
    return m-hole

def apply_camera_cam_completion():
    q=P.get('camera_cam_completion',{})
    if not q.get('enabled'):return
    assert q['approved']
    assembled();bpy.context.view_layer.update()
    o=replace_exact('Display_Frame',Solid(obj('Display_Frame')).m-camera_cut())
    o['camera_top_clearance']='M1.48 approved continuous 0.6mm outside-top trim; nominal wall1.2mm; inner capture surfaces preserved.'
    rows=[]
    for r in P['interface_completion']['inserts']:
        if r.get('screw') not in q['cam_screws']['ids']:continue
        o=replace_exact(r['screw'],socket_solid(r))
        o['label_zh']='CAM固定 DIN912 M2×5 内六角'
        o['data_status']='VENDOR_DOCUMENTED';o['model_fidelity']='CATALOGUE_OUTER_ENVELOPE; socket depth assumed, thread helix omitted'
        o['source_receipt']=q['cam_screws']['source_receipt'];o['measured_unit']=False
        o['source_url']='https://bossard.partcommunity.com/3d-cad-models/?info=bossard%2F01%2F01_100%2F01_100_100%2F01_100_100_10%2Fbn_610_612_31101%2Fbn_610.prj&languageIso=de'
        o['assembly_tool']='Wera950PKLS05022040001,1.5mm hex,90/4.5mm; Display_Frame/front shell fitted later'
        rows.append({'id':r['screw'],'axis':r['outward'],'head_bearing_mm':r['screw_head_bearing_mm'],'length_mm':q['cam_screws']['length_mm']})
    assert len(rows)==4
    report=ROOT/'reports/interface_completion.json'
    data=json.loads(report.read_text());data['current_CAM_screw_override']=q['cam_screws']
    for r in data['inserts']:
        if r.get('screw') in q['cam_screws']['ids']:
            r['head_diameter_mm']=q['cam_screws']['head_diameter_mm'];r['head_height_mm']=q['cam_screws']['head_height_mm'];r['screw_specification']=q['cam_screws']['specification']
    save_json(report,data)
    save_json(ROOT/'reports/camera_cam_completion_geometry.json',{'revision':P['revision'],'changed_existing_ids':q['changed_existing_ids'],'screws':rows,'camera_trim_mm':q['camera']['outside_top_trim_mm'],'physical_validation':'NOT_TESTED','manufacturing_release':False})
    print('CAMERA_CAM_COMPLETION',q['changed_existing_ids'],flush=True)
