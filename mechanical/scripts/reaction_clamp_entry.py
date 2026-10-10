"""M1.55 approved R2 neck, derived only from current geometry.json.

The immutable R2 mesh is a verification reference, never a construction input.
The C5 parameters remain historical; this explicit late phase modifies only
Pitch_Yoke. Bearing fit skin, servos and every other native part are preserved.
"""
import copy
from common import *
from validate import Solid
from camera_cam_completion import replace_exact
from neck_capacity import construct as construct_neck

def quantize(m,cleanup):
    def once(m):
        d=m.to_mesh64();v=np.array(d.vert_properties[:,:3],dtype=np.float32).astype(np.float64)
        return manifold.Manifold(manifold.Mesh64(v,np.array(d.tri_verts,dtype=np.uint64)))
    return once(once(m).simplify(cleanup))

def construct(original,settings,neck):
    q=copy.deepcopy(neck);p=settings['parameters'];c=settings['construction']
    q['candidate_parameters']['neck_profile']['reference_reaction_bore_r_mm']=p['reference_reaction_bore_r_mm']
    results,_,outer,inner,pack,curves,rows=construct_neck(original,q)
    cleanup=q['construction']['saved_float32_cleanup_mm'];full=quantize(results['Pitch_Yoke'],cleanup)
    z=p['rear_open_start_Z_mm'];height=p['rear_open_top_Z_mm']-z;r=p['rear_open_max_radius_mm']
    cut=manifold.Manifold.cylinder(height,r,r,c['segments']).translate([0,0,z])
    a,b=c['rear_cut_box_xy_mm'];box=manifold.Manifold.cube([b[0]-a[0],b[1]-a[1],height]).translate([a[0],a[1],z])
    assert b[1]==p['rear_open_max_Y_mm']
    cut^=box
    result=quantize((full-cut).simplify(cleanup),cleanup)
    assert result.status()==manifold.Error.NoError and result.volume()>0 and len(result.decompose())==1
    return result,dict(full=full,cut=cut,outer=outer,inner=inner,pack=pack,curves=curves,curve_rows=rows)

def apply_reaction_clamp_entry():
    settings=P.get('reaction_clamp_entry',{})
    if not settings.get('enabled'):return
    assert settings['approved']
    assembled();bpy.context.view_layer.update()
    original={n:Solid(bpy.data.objects[PREFIX+n]).m for n in P['neck_harness_capacity']['changed_existing_ids']}
    before=original['Pitch_Yoke'];result,_=construct(original,settings,P['neck_harness_capacity'])
    o=replace_exact('Pitch_Yoke',result)
    o['reaction_entry_revision']=settings['revision'];o['data_status']='ASSUMED'
    o['interface_status']='Approved R2 internal passage and open rear neck; bearing fit exterior and servo datums retained. Bare-print entry checked; actual horn/locking and full wired assembly BLOCKED; PA12 strength NOT_TESTED.'
    save_json(ROOT/'reports/reaction_clamp_entry_geometry.json',dict(
        revision=P['revision'],geometry_source='config/geometry.json#/reaction_clamp_entry',
        changed_existing_ids=['Pitch_Yoke'],new_ids=[],retired_ids=[],
        original_volume_mm3=float(before.volume()),volume_mm3=float(result.volume()),
        added_mm3=float((result-before).volume()),removed_mm3=float((before-result).volume()),
        parameters=settings['parameters'],approved=True,
        category='PRINTABLE',data_status='ASSUMED',actual_horn_and_locking='BLOCKED',full_harness='BLOCKED',
        physical_strength='NOT_TESTED',manufacturing_release=False))
    print('REACTION_ENTRY_R2_APPLIED',result.volume(),flush=True)
