"""M1.44 approved A5 C keeper. All current dimensions derive from geometry.json.

Earlier phases retain a construction datum; this final phase moves only the
bearing/stop interface. Documented bearing boundaries are not full vendor CAD.
"""
from common import *
from interface_completion import replace_owned

S=P.get('head_axial_retention',{})

def cylinder(r,z0,z1,x=0,y=0):
    return manifold.Manifold.cylinder(z1-z0,r,r,192).translate((x,y,z0))

def annulus(ro,ri,z0,z1):
    return cylinder(ro,z0,z1)-cylinder(ri,z0-.01,z1+.01)

def cube(a,b):
    return manifold.Manifold.cube(tuple(np.array(b)-a)).translate(a)

def change_region():
    # Approved annular interface only, below all servo mounting seats.
    return cube((-36,-36,146.9),(36,36,173.6))

def apply_head_axial_retention():
    if not S.get('enabled'):return
    from validate import Solid
    assembled()
    original={n:Solid(bpy.data.objects[PREFIX+n]).m for n in S['changed_existing_ids']}
    oldbz=D['yaw_bearing_construction_z'];bz=D['yaw_bearing_z'];shift=bz-oldbz
    bearing=S['bearing'];k=S['keeper'];f=S['fasteners'];support=S['support']
    bb=bz-bearing['d_D_B_mm'][2]/2;bt=bz+bearing['d_D_B_mm'][2]/2
    kb=bz+k['bottom_from_bearing_mm'];kt=kb+k['thickness_mm']
    helper_names=['Collar','Key','Fixed_-1','Fixed_1']
    helpers={n:Solid(bpy.data.objects[PREFIX+'DATUM_Compact_Yaw_'+n]).m for n in helper_names}
    # Reconstruct the journal without moving the head's servo seats or frame.
    oldlo,oldhi=[oldbz+v for v in P['compact_yaw_stops']['moving_z_from_bearing_mm']]
    yoke=original['Pitch_Yoke']-annulus(20.1,9.7,oldlo-.01,oldhi+.01)
    yoke+=annulus(9.8,7.7,bb,oldbz+16.51)
    yoke+=helpers['Collar'].translate((0,0,shift))+helpers['Key'].translate((0,0,shift))
    jr=bearing['trial_journal_d_mm']/2;sr=bearing['shaft_abutment_d_mm']/2
    yoke+=annulus(jr,7.7,bb+.4,bt)+annulus(sr,7.7,bt,bt+.85)
    yoke+=manifold.Manifold.cylinder(.4,9.7,jr,192).translate((0,0,bb))-cylinder(7.7,bb-.01,bb+.41)
    base=original['Yaw_Base']
    for n in ['Fixed_-1','Fixed_1']:base-=helpers[n]
    br=bearing['trial_housing_bore_d_mm']/2;hr=bearing['housing_abutment_D_max_mm']/2
    base-=cylinder(20.31,bt+.3,oldhi+.01)
    base-=cylinder(hr,oldbz-10,bt+.31)
    base+=annulus(27,br,bb,bt+.3)+annulus(27,hr,oldbz-10,bb)
    base+=annulus(support['outer_r_mm'],support['inner_r_mm'],bz+support['bottom_from_bearing_mm'],kb)
    base-=cylinder(br,bb,bt+.3)
    base-=cylinder(support['rim_inner_r_mm'],kb,oldbz+7.01)
    base+=annulus(support['outer_r_mm'],support['rim_inner_r_mm'],kb-.1,bz+support['rim_top_from_bearing_mm'])
    for n in ['Fixed_-1','Fixed_1']:base+=helpers[n].translate((0,0,shift))
    keeper=annulus(k['outer_radius_mm'],k['inner_radius_mm'],kb,kt)-cube((-k['inner_radius_mm'],-40,kb-.1),(k['inner_radius_mm'],0,kt+.1))
    fasteners={};headbase=kt-k['counterbore_depth_mm']
    for i,(x,y) in enumerate(k['screw_xy_mm']):
        keeper-=cylinder(k['through_d_mm']/2,kb-.1,kt+.1,x,y)
        keeper-=cylinder(k['counterbore_d_mm']/2,headbase,kt+.1,x,y)
        base-=cylinder(f['trial_pilot_d_mm']/2,bz+f['pilot_bottom_from_bearing_mm'],kb+.1,x,y)
        screw=cylinder(f['shank_d_mm']/2,headbase-f['length_mm'],headbase,x,y)+cylinder(f['head_d_mm']/2,headbase,headbase+f['head_h_mm'],x,y)
        screw-=cylinder(1,headbase+.55,kt+.05,x,y)
        ib=bz+f['insert_bottom_from_bearing_mm']
        insert=cylinder(f['insert_OD_mm']/2,ib,ib+f['insert_length_mm'],x,y)-cylinder(1.5,ib-.1,ib+f['insert_length_mm']+.1,x,y)
        fasteners['Yaw_Keeper_Screw_'+str(i)]=screw
        fasteners['Yaw_Keeper_Insert_'+str(i)]=insert
    for n,m in [('Yaw_Base',base),('Pitch_Yoke',yoke),('Yaw_Bearing',original['Yaw_Bearing'].translate((0,0,shift)))]:
        replace_owned(n,m)
        if n in ['Yaw_Base','Pitch_Yoke']:
            # Float32 Blender readback can leave coincident Boolean triangles.
            # Re-simplify those saved coordinates at0.0005mm; independently
            # bound the solid difference against the approved A5 candidate.
            replace_owned(n,Solid(bpy.data.objects[PREFIX+n]).m)
        bpy.data.objects[PREFIX+n]['head_retention_revision']=P['revision']
    for n,m in helpers.items():replace_owned('DATUM_Compact_Yaw_'+n,m.translate((0,0,shift)))
    for n,m in {'Yaw_Anti_Lift_Keeper':keeper,**fasteners}.items():
        d=m.simplify(.0005).to_mesh64();o=mesh(n,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist())
        printed=n=='Yaw_Anti_Lift_Keeper';category='PRINTABLE' if printed else 'PURCHASED_REFERENCE'
        move_collection(o,category)
        o.data.materials.append(MATS['frame' if printed else 'metal'])
        for face in o.data.polygons:face.use_smooth=False
        o['role']='part';o['category']=category;o['group']='body';o['data_status']='ASSUMED'
        o['stage']='PROTOTYPE';o['verification_status']='UNVALIDATED';o['export_candidate']=printed
        o['measured_unit']=False;o['head_retention_revision']=P['revision']
        o['label_zh']='Yaw防脱C压板' if printed else 'Yaw压板M3×8螺钉' if 'Screw' in n else 'Yaw压板SL-M3×4嵌件'
        o['material_suggestion']='PA12 nylon; first structural trial, strength unqualified' if printed else 'Purchased metal hardware, nominal envelope'
        o['model_fidelity']='DESIGN_GEOMETRY' if printed else 'NOMINAL_FASTENER_ENVELOPE'
        o['interface_status']='Nominal0.4mm capture clearance; not bearing preload' if printed else f['screw'] if 'Screw' in n else f['insert']+'; catalogue envelope; PA12 pilot trial only'
        o['functional_purpose']='Removable axial anti-lift stop; fitted before pitch head; separate fixed and rotating groups' if printed else 'Retains removable keeper to fixed bridge'
        o['explode_offset_mm']=[0,0,55 if printed else 70]
        if printed:
            o['selected_print_material']='PA12';o['physical_material_status']='NOT_TESTED';o['print_process_recommendation']='MJF; supplier acceptance pending'
            o['simple_support_module']=True;o['print_orientation_candidate']='Broad flat face parallel to build bed; PA12 service to review orientation'
    bo=bpy.data.objects[PREFIX+'Yaw_Bearing']
    bo['candidate_product']=bearing['model'];bo['source_url']=bearing['source_url'];bo['model_fidelity']='BOUNDARY_ENVELOPE_ONLY'
    bo['category']='PURCHASED_REFERENCE';move_collection(bo,'PURCHASED_REFERENCE');bo['data_status']='VENDOR_DOCUMENTED'
    bo['documented_fields']=bearing['evidence'];bo['measured_unit']=False
    bo['interface_status']='NSK6804ZZ boundary/abutments documented; envelope only;19.9/32.1 trial fits require PA12 coupons'
    bo['label_zh']='Yaw轴承 NSK6804ZZ（边界参考）'
    save_json(ROOT/'reports/head_axial_retention_build.json',{'revision':P['revision'],'status':'PROTOTYPE / UNVALIDATED','source':'config/geometry.json#/head_axial_retention','changed_existing':S['changed_existing_ids'],'added':S['new_ids'],'bearing_center_z_mm':bz,'construction_center_z_mm':oldbz,'bearing_shift_mm':shift,'keeper_z_mm':[kb,kt],'assembly':S['assembly'],'limits':S['limits']})
    print('HEAD_AXIAL_RETENTION_APPLIED',shift,flush=True)
