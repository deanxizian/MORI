"""Approved M1.49 delta reversal for historical comparisons only."""
from common import *
from validate_thin_cleanup import load_reference
import hashlib
_cache=None

def references():
    global _cache
    if _cache is None:
        q=P['neck_harness_capacity'];p=PROJECT/q['baseline_blend']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==q['baseline_sha256']
        _cache=load_reference(p)
    return _cache

def approved(name):
    q=P['neck_harness_capacity'];correction=q.get('keeper_wall_correction',{})
    if correction.get('enabled') and name in correction['changed_existing_ids']:
        assert correction['approved']
        p=PROJECT/correction['candidate_directory']/(correction['reference_prefix']+name+'.npz')
        receipt=json.loads((PROJECT/correction['approval_record']).read_text())
        assert receipt['approval']=='USER_APPROVED'
        assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['source_geometry'][name]
        d=np.load(p)
        return manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
    p=PROJECT/q['approved_candidate_directory']/('C5_'+name+'.npz')
    receipt=json.loads((PROJECT/q['approval_record']).read_text())
    assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['candidate_sources'][str(p.relative_to(PROJECT))]
    d=np.load(p)
    return manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))

def saved_approved(name):
    d=approved(name).to_mesh64()
    v=np.array(d.vert_properties[:,:3],dtype=np.float32).astype(np.float64)
    f=np.array(d.tri_verts,dtype=np.uint64,copy=True,order='C')
    return manifold.Manifold(manifold.Mesh64(v,f))

def prior_solid(name,current):
    if name not in declared_neck_capacity_changes():return current
    a=references()[name]['solid'];b=saved_approved(name)
    return (current-(b-a))+(a-b)
