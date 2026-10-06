"""Independent C6 study: relieve only the outer edge of the existing left slot.

Not approved or adopted. The bearing seat (R20..21.05), keeper, fasteners and
rotor remain unchanged. This widens an existing opening, not its angular span.
"""
import math
import numpy as np
import manifold3d as manifold

def build(original,parameters,new_outer_radius=12.5):
    window=parameters['candidate_parameters']['windows'][1]
    ri,old_ro=window['radii_mm'];a0,a1=window['angles_deg'];z0,z1=window['z_mm']
    assert [ri,old_ro]==[9.55,11.7] and [a0,a1]==[113.,200.]
    a=np.radians(np.linspace(a0,a1,math.ceil((a1-a0)/.5)+1))
    outline=np.vstack([new_outer_radius*np.c_[np.cos(a),np.sin(a)],ri*np.c_[np.cos(a[::-1]),np.sin(a[::-1])]])
    cut=manifold.CrossSection([outline]).extrude(z1-z0).translate([0,0,z0])
    lo,hi=parameters['construction']['window_web_exclusion']
    exclude=manifold.Manifold.cube(tuple(np.asarray(hi)-lo)).translate(lo)
    cut-=exclude
    candidate=original-cut;removed=original-candidate
    assert candidate.status()==manifold.Error.NoError and len(candidate.decompose())==1
    assert (candidate-original).volume()<1e-7
    m=removed.to_mesh64();bounds=np.asarray(m.vert_properties[:,:3])
    return candidate,dict(status='PASS',scope='Candidate construction only; not structural qualification',approved=False,
        changed_existing_ids=['Yaw_Base'],old_outer_radius_mm=old_ro,new_outer_radius_mm=new_outer_radius,
        opening_angles_deg=[a0,a1],opening_z_mm=[z0,z1],removed_volume_mm3=removed.volume(),
        removed_bounds_mm=[bounds.min(0).tolist(),bounds.max(0).tolist()],connected_solids=len(candidate.decompose()),
        bearing_seat_changed=False,fasteners_changed=False,main_changed=False,physical_strength='NOT_TESTED')
