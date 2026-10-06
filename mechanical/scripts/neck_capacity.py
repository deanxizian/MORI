"""M1.49 approved C5 neck; all design dimensions derive from geometry.json.

No study script, saved candidate mesh or scene is used to construct the prints.
The saved C5 solids are independent verification references only.
"""
from common import *
from validate import Solid
from camera_cam_completion import replace_exact
from neck_curve_geometry import family,rotate,radial
from neck_profile_geometry import make_neck

def cylinder(r,a,b,x=0,y=0):
    c=P['neck_harness_capacity']['construction']
    return manifold.Manifold.cylinder(b-a,r,r,c['segments']).translate((x,y,a))

def ring(ro,ri,a,b):
    return cylinder(ro,a,b)-cylinder(ri,a-.01,b+.01)

def box(a,b):
    return manifold.Manifold.cube(tuple(np.asarray(b)-a)).translate(a)

def sector(ri,ro,a0,a1,z0,z1):
    angles=np.radians(np.linspace(a0,a1,math.ceil((a1-a0)/.5)+1))
    polygon=[(ro*math.cos(a),ro*math.sin(a)) for a in angles]
    polygon +=[(ri*math.cos(a),ri*math.sin(a)) for a in reversed(angles)]
    return manifold.CrossSection([polygon]).extrude(z1-z0).translate((0,0,z0))

def local_curves(q):
    rows=family(**q['curve_family'])
    pack={'selected':q['wire_allocations']}
    data={f'wire{i}_y{r["yaw_deg"]}':rotate(r['points'],slot['angle_deg'])
          for i,slot in enumerate(pack['selected']) for r in rows}
    return pack,data,rows

def construct(original,q):
    c=q['construction'];p=q['candidate_parameters']
    base=original['Yaw_Base']-cylinder(*c['base_cut'])
    for dims in c['base_rings']:base+=ring(*dims)
    base+=box(*c['bridge_web_bounds'])-cylinder(*c['bridge_web_inner_cut'])
    base+=original['Yaw_Base']^box(*c['protected_web_bounds'])
    for w in p['windows']:
        base-=sector(*w['radii_mm'],*w['angles_deg'],*w['z_mm'])-box(*c['window_web_exclusion'])
    for side in [-1,1]:
        a,b,y0,y1=p['bolt_seat_xy_extent_mm'];x=sorted([side*a,side*b])
        base+=box((x[0],y0,p['bolt_seat_z_mm'][0]),(x[1],y1,p['bolt_seat_z_mm'][1]))
    fixed=[]
    for a0,a1 in p['fixed_sector_deg']:
        root=sector(*p['fixed_root_inner_outer_r_mm'],a0,a1,*p['fixed_root_z_mm'])
        stop=sector(*p['stop_inner_outer_r_mm'],a0,a1,*p['fixed_stop_z_mm'])
        fixed.append(root+stop);base+=root+stop
    ki,ko=p['keeper_inner_outer_r_mm']
    keeper=ring(ko,ki,*p['keeper_z_mm'])-box(*c['keeper_mouth_bounds'])
    for x,y in c['screw_xy_mm']:
        keeper-=cylinder(*c['keeper_through'],x,y)
        keeper-=cylinder(*c['keeper_counterbore'],x,y)
        base-=cylinder(*c['insert_pilot'],x,y)
    yoke=original['Pitch_Yoke']-cylinder(*c['yoke_cut'])
    yoke+=ring(*c['yoke_rings'][0])
    h,r0,r1,z=c['journal_chamfer']
    yoke+=manifold.Manifold.cylinder(h,r0,r1,c['segments']).translate((0,0,z))-cylinder(*c['journal_chamfer_bore'])
    yoke+=ring(*c['yoke_rings'][1])+ring(*c['yoke_rings'][2])
    collar=ring(p['collar_outer_r_mm'],p['journal_inner_r_mm'],*p['moving_collar_key_z_mm'])
    key=sector(*p['stop_key_inner_outer_r_mm'],*p['stop_key_sector_deg'],*p['moving_collar_key_z_mm'])
    yoke+=collar+key
    z0,zstart,zend,ztop=c['profile_bore_z_mm']
    zs=np.r_[z0,np.arange(zstart,zend,c['profile_bore_step_mm']),ztop]
    cf=q['curve_family']
    r=radial(zs,cf['r0'],cf['r1'],cf['flare_start'],cf['flare_radius'])[0]
    r=np.maximum(p['journal_inner_r_mm'],r+c['profile_bore_padding_mm'])
    bore=manifold.Manifold.batch_boolean([
        manifold.Manifold.cylinder(float(b-a),float(ra),float(rb),c['segments']).translate((0,0,float(a)))
        for a,b,ra,rb in zip(zs,zs[1:],r,r[1:])],manifold.OpType.Add)
    yoke-=bore
    pack,data,rows=local_curves(q)
    tube,outer,inner,params=make_neck(pack,data,q)
    yoke-=cylinder(*c['neck_cut']);yoke+=tube
    yoke+=cylinder(*c['lower_fill'])-inner
    d,D,b=q['bearing']['dimensions_mm']
    result={'Yaw_Base':base,'Pitch_Yoke':yoke,'Yaw_Anti_Lift_Keeper':keeper,
            'Yaw_Bearing':ring(D/2,d/2,*p['bearing_z_mm'])}
    result={n:m.simplify(c['simplify_mm']) for n,m in result.items()}
    features={'Collar':collar,'Key':key,'Fixed_-1':fixed[0],'Fixed_1':fixed[1]}
    return result,features,outer,inner,pack,data,rows

def apply_neck_capacity():
    q=P.get('neck_harness_capacity',{})
    if not q.get('enabled'):return
    assert q['approved']
    assembled();bpy.context.view_layer.update()
    original={n:Solid(bpy.data.objects[PREFIX+n]).m for n in q['changed_existing_ids']}
    solids,features,outer,inner,pack,data,rows=construct(original,q)
    correction=q.get('keeper_wall_correction',{})
    if correction.get('enabled'):
        assert correction['approved']
        for i,(new_xy,old_xy) in enumerate(zip(q['construction']['screw_xy_mm'],P['head_axial_retention']['keeper']['screw_xy_mm'])):
            delta=(*tuple(np.asarray(new_xy)-old_xy),0.)
            for kind in ['Screw','Insert']:
                n=f'Yaw_Keeper_{kind}_{i}'
                solids[n]=original[n].translate(delta)
    for n,m in solids.items():
        o=replace_exact(n,m)
        if n in ['Yaw_Base','Pitch_Yoke']:
            # Quantize before cleanup: reject collapsed float32 triangles,
            # preserving the approved geometry to a5nm numerical tolerance.
            saved=Solid(o).m.simplify(q['construction']['saved_float32_cleanup_mm'])
            o=replace_exact(n,saved)
        o['neck_capacity_revision']=q['revision']
        if n in ['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper']:
            o['data_status']='ASSUMED'
            o['interface_status']='Approved C5 neck with K1 keeper-wall correction; trial PA12 fits and strength NOT_TESTED; full wiring incomplete'
    for n,m in features.items():replace_exact('DATUM_Compact_Yaw_'+n,m)
    bo=bpy.data.objects[PREFIX+'Yaw_Bearing'];b=q['bearing']
    bo['candidate_product']=b['model'];bo['label_zh']='Yaw轴承 NSK6806ZZ（边界参考）'
    bo['source_url']=b['source_url'];bo['source_receipt']=b['source_receipt']
    bo['documented_mass_g']=b['mass_g'];bo['documented_fields']=b['evidence']
    bo['model_fidelity']='BOUNDARY_ENVELOPE_ONLY';bo['data_status']='VENDOR_DOCUMENTED'
    bo['interface_status']='30x42x7 boundary;29.9/42.1mm trial fits; physical fit and PA12 strength NOT_TESTED'
    report={'revision':P['revision'],'geometry_source':'config/geometry.json#/neck_harness_capacity',
        'changed_existing_ids':q['changed_existing_ids'],'new_ids':[],'retired_ids':[],
        'bearing':b,'source_of_curves':'config/geometry.json#/neck_harness_capacity',
        'local_wire_length_mm':rows[0]['length_mm'],'max_chord_error_mm':max(r['chord_error_mm'] for r in rows),
        'full_harness':'BLOCKED','physical_fit':'NOT_TESTED','strength':'NOT_TESTED','manufacturing_release':False}
    save_json(ROOT/'reports/neck_capacity_geometry.json',report)
    print('NECK_CAPACITY_APPLIED',q['changed_existing_ids'],flush=True)
