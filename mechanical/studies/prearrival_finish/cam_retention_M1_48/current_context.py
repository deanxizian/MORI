"""Explicit M1.48 plus the two named channel candidates. No legacy init code."""
from pathlib import Path
import sys, json, hashlib
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context, np, manifold, sha
from validate import rigidtr
from mathutils import Vector

def stored(path):
    data=np.load(path)
    m=manifold.Manifold(manifold.Mesh64(data['vertices_mm'],data['triangles'].astype(np.uint64)))
    assert m.status()==manifold.Error.NoError and m.volume()>0, str(path)
    return m

def cache(path,m):
    a=m.to_mesh64()
    np.savez_compressed(path,vertices_mm=np.asarray(a.vert_properties[:,:3]),triangles=np.asarray(a.tri_verts))

def overlap_boxes(a,b,pad=0.):
    aa=np.asarray(a.bounding_box());bb=np.asarray(b.bounding_box())
    return not (np.any(aa[:3]>bb[3:]+pad) or np.any(bb[:3]>aa[3:]+pad))

def pose(group,yaw,pitch):
    return np.eye(4) if group not in ['yaw','pitch'] else np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0))

def move(m,group,yaw,pitch):
    return m if group not in ['yaw','pitch'] else m.transform(pose(group,yaw,pitch)[:3,:])

class RetentionContext:
    def __init__(self):
        self.ctx=Context();self.inputs={}
        self.base={n:s.m for n,s in self.ctx.ss.items()}
        self.groups={n:s.group for n,s in self.ctx.ss.items()}
        self.channel_review=HERE.parent/'yaw_service_M1_48'
        check=json.loads((self.channel_review/'refined_adaptive_all.json').read_text())
        assert check['status']=='PASS' and check['source_main_sha256']==self.ctx.source_hash
        for r in check['substituted_prints']:
            p=PROJECT/r['source'];assert sha(p)==r['source_sha256']
            self.base[r['name']]=self.read(p)
        self.targets={**self.base, **{n:t['m'] for n,t in self.ctx.targets.items() if n not in self.base}}
        self.groups.update({n:'body' for n in self.targets if n not in self.groups})
        self.curvefile=self.channel_review/'internal_full_curves.npz'
        assert sha(self.curvefile)==check['curve_source_sha256']
        self.curves=np.load(self.curvefile)
        self.inputs[str(self.curvefile.relative_to(PROJECT))]=sha(self.curvefile)
        self.inputs[str((self.channel_review/'refined_adaptive_all.json').relative_to(PROJECT))]=sha(self.channel_review/'refined_adaptive_all.json')
    def read(self,path):
        self.inputs[str(path.relative_to(PROJECT))]=sha(path)
        return stored(path)
    def assert_unchanged(self):
        self.ctx.assert_unchanged()
        for p,h in self.inputs.items():assert sha(PROJECT/p)==h,p
    def evidence(self):
        return dict(source_main_sha256=self.ctx.source_hash,native_context=self.ctx.evidence(),
                    explicit_inputs=self.inputs,base_channel_substitutions=['Yaw_Base','Pitch_Yoke'],
                    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
