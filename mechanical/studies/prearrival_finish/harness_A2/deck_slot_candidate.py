# -*- coding: utf-8 -*-
"""Pure independent candidate. Never invoked by the main model generator."""
from pathlib import Path
import json, hashlib

PARAMETERS = dict(center_xy_mm=[22.,-39.],width_mm=7.,length_mm=22.,long_axis='X',
    region='Load_Frame top deck only',status='ASSUMED_CANDIDATE_NOT_ADOPTED')

def apply_to_study(ns,parameters=None):
    """Replace only the in-memory solid/BVH, without editing scene or files."""
    np=ns['np'];mm=ns['manifold'];axial=ns['axial'];P=ns['P']
    spec=PARAMETERS if parameters is None else parameters
    x,y=spec['center_xy_mm'];w=spec['width_mm'];ln=spec['length_mm']
    z=P['layout']['deck_z_mm'];th=P['layout']['deck_thickness_mm'];h=th+.02
    along_x=spec.get('long_axis')=='X'
    cut=mm.Manifold.cube([ln-w,w,h] if along_x else [w,ln-w,h],center=True).translate([x,y,z])
    for sign in [-1,1]:
        cc=[x+sign*(ln-w)/2,y,z] if along_x else [x,y+sign*(ln-w)/2,z]
        cut+=axial(w/2,h,cc,[0,0,1])
    old=ns['ss']['Load_Frame'];candidate=old.m-cut
    assert candidate.status()==mm.Error.NoError and len(candidate.decompose())==1
    md=candidate.to_mesh64()
    from types import SimpleNamespace
    s=SimpleNamespace(o=old.o,name=old.name,group=old.group,m=candidate,
        v=md.vert_properties[:,:3],f=md.tri_verts)
    s.lo=s.v.min(0);s.hi=s.v.max(0)
    ns['ss']['Load_Frame']=s;ns['obstacles']['Load_Frame']=s
    ns['trees']['Load_Frame']=ns['BVHTree'].FromPolygons([ns['Vector'](v) for v in s.v],s.f.tolist(),all_triangles=True)
    ns['los']=np.array([ns['obstacles'][n].lo for n in ns['obs']])
    ns['his']=np.array([ns['obstacles'][n].hi for n in ns['obs']])
    doc=dict(spec,deck_bottom_top_z_mm=[z-th/2,z+th/2],
        removed_mm3=(old.m-candidate).volume(),added_mm3=(candidate-old.m).volume(),
        source_blend_sha256=ns['source_hash'],frame_connected_components=1,
        main_geometry_changed=False,adopted=False)
    return doc
