"""Approved M1.53 C6 relief; dimensions come only from geometry.json."""
from common import *
from validate import Solid
from camera_cam_completion import replace_exact


def construct(original, settings, neck):
    window = neck['candidate_parameters']['windows'][settings['window_index']]
    _, old_radius = window['radii_mm']
    new_radius = old_radius + settings['outward_extension_mm']
    a0, a1 = window['angles_deg']; z0, z1 = window['z_mm']
    angles = np.radians(np.linspace(a0, a1, math.ceil((a1-a0)/settings['sector_step_deg'])+1))
    inner = old_radius-settings['boolean_overlap_mm']
    outline = np.vstack([new_radius*np.c_[np.cos(angles),np.sin(angles)],
                         inner*np.c_[np.cos(angles[::-1]),np.sin(angles[::-1])]])
    cut = manifold.CrossSection([outline]).extrude(z1-z0).translate([0,0,z0])
    lo, hi = neck['construction']['window_web_exclusion']
    cut -= manifold.Manifold.cube(tuple(np.asarray(hi)-lo)).translate(lo)
    raw = original-cut
    assert (raw-original).volume()<1e-7
    # Remove sub-float32 triangulation slivers before Blender storage. This
    # 1e-7 mm numerical tolerance is not a design clearance or print allowance;
    # the saved solid is independently compared with the approved reference.
    result = raw.simplify(1e-7)
    assert result.status()==manifold.Error.NoError and len(result.decompose())==1
    assert (result-raw).volume()+(raw-result).volume()<1e-6
    return result


def apply_neck_entry_relief():
    settings=P.get('neck_entry_relief',{})
    if not settings.get('enabled'):return
    assert settings['approved']
    assembled();bpy.context.view_layer.update()
    original=Solid(bpy.data.objects[PREFIX+'Yaw_Base']).m
    result=construct(original,settings,P['neck_harness_capacity'])
    removed=original-result
    assert removed.volume()>0
    o=replace_exact('Yaw_Base',result)
    o['neck_entry_revision']=settings['revision']
    o['interface_status']='Approved C5/K1 plus C6 left-entry outer relief. Full harness BLOCKED; PA12 fit and strength NOT_TESTED.'
    vertices=np.asarray(removed.to_mesh64().vert_properties[:,:3])
    save_json(ROOT/'reports/neck_entry_relief_geometry.json',dict(
        revision=P['revision'],geometry_source='config/geometry.json#/neck_entry_relief',
        changed_existing_ids=['Yaw_Base'],new_ids=[],retired_ids=[],
        removed_volume_mm3=removed.volume(),removed_bounds_mm=[vertices.min(0).tolist(),vertices.max(0).tolist()],
        added_volume_mm3=(result-original).volume(),approved=True,
        full_harness='BLOCKED',physical_strength='NOT_TESTED',manufacturing_release=False))
    print('C6_ENTRY_APPLIED',removed.volume(),flush=True)
