"""Explicit current-main inputs for the outer harness studies.

No execution of prefixes from earlier study scripts. The only added objects
are the recorded mating-housing allocations loaded into this temporary scene.
The saved main, printed parts and hardware-owned sources remain read-only.
"""
from pathlib import Path
import hashlib,json,math,sys
PROJECT=Path(__file__).resolve().parents[2]
HERE=PROJECT/'mechanical/studies/prearrival_finish/neck_adoption'
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
from native_electronics import board_transform,source_mesh
from mathutils.bvhtree import BVHTree

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

class Context:
    def __init__(self):
        self.main=Path(bpy.data.filepath).resolve()
        assert self.main==PROJECT/'mechanical/mori_v1_2.blend'
        prior=PROJECT/'mechanical/reports/build_manifest.json'
        self.prior=json.loads(prior.read_text())
        self.source_hash=sha(self.main)
        assert P['neck_harness_capacity']['enabled'] and P['neck_harness_capacity']['approved']
        assert self.prior['input_sha256']['config/geometry.json']==sha(PROJECT/'config/geometry.json')
        self.sources={str(p.relative_to(PROJECT)):sha(p) for p in [self.main,prior,
            PROJECT/'config/geometry.json',PROJECT/'contracts/mechanical_interfaces.json',
            PROJECT/'contracts/components.json',Path(__file__)]}
        load_collections()
        # Hidden collision proxies can retain stale parent transforms when a
        # saved file is opened headlessly. Match validate.main(): activate the
        # proxy collection before establishing the assembled solid baseline.
        for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:
            COLS[name].hide_viewport=False
        assembled();bpy.context.view_layer.update()
        self.ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts()
                 if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
        assert len(self.ss)==(201 if P.get('body_front_rear_split',{}).get('enabled') else 209)
        self.print_fingerprints={n:self.fingerprint(s) for n,s in self.ss.items()}

        preparation=PROJECT/'mechanical/studies/prearrival_preparation'
        mating_path=preparation/'mated_connector_review.json'
        mate=json.loads(mating_path.read_text())
        assert mate['sources']['inventory']==sha(PROJECT/'mechanical/sources/populated_P5/inventory.json')
        library=preparation/'mated_connector_review.blend'
        with bpy.data.libraries.load(str(library),link=False) as (src,dst):
            dst.objects=[n for n in src.objects if n.startswith(PREFIX+'PREARRIVAL_Plug_')]
        for o in dst.objects:
            if o:bpy.context.scene.collection.objects.link(o)
        bpy.context.view_layer.update()
        self.plug={o.name.removeprefix(PREFIX+'PREARRIVAL_Plug_'):Solid(o) for o in dst.objects if o}
        assert len(self.plug)==29
        self.portrows={r['board']+'_'+r['ref']:r for r in mate['rows']}
        hand_path=PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json'
        hand=json.loads(hand_path.read_text())
        s=self.plug['rear_J3'];mid=(s.lo+s.hi)/2
        bb=hand['rear_J3']['nominal_screen']['plug_world_bounds_mm']
        center=(np.asarray(bb[:3])+bb[3:])/2
        tr=Matrix.Translation(Vector(center))@Matrix.Rotation(math.pi,4,'X')@Matrix.Translation(-Vector(mid))
        s.o.matrix_world=tr@s.o.matrix_world;bpy.context.view_layer.update()
        self.plug['rear_J3']=Solid(s.o)

        self.port_pins={};self.board_sources={}
        for kind,spec in P['native_electronics']['boards'].items():
            cache=source_mesh(spec['mesh']);rot,trans=board_transform(kind,cache)
            board=next(v for k,v in hand['boards'].items() if k.startswith('MORI_'+kind+'_'))
            assert board['pcb_sha256']==cache['source_native_sha256'],kind
            self.board_sources[kind]=dict(file=cache['source_native_file'],sha256=cache['source_native_sha256'])
            for c in board['connectors']:
                key=kind+'_'+c['ref']
                if key not in self.plug:continue
                pads={p['pin']:rot@np.array([p['xy_mm'][0],-p['xy_mm'][1],0])+trans for p in c['pins']}
                average=np.mean(list(pads.values()),axis=0)
                axis=np.array(self.portrows[key]['axis'],float)
                if key=='rear_J3':axis=-axis
                s=self.plug[key];mid=(s.lo+s.hi)/2
                face=mid+axis*(max(s.v@axis)-mid@axis)
                self.port_pins[key]=dict(axis=axis,exit_face=face,pins={
                    n:face+(v-average)-axis*((v-average)@axis) for n,v in pads.items()})

        A8=HERE.parent/'harness_A8'
        sys.path.insert(0,str(A8/'amass_mating'))
        from envelopes import rebuild
        self.amass=rebuild(self.plug,self.portrows,self.port_pins,globals(),'upper_with_thickness_allocation')
        fixed_path=HERE.parent/'harness_A2/assembly_safe_review/fourteen_wire_solids.json'
        fixed=json.loads(fixed_path.read_text())
        joint_path=A8/('cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/'
                       'complete_head/bridge_wire_stock/install_order/CAM_H02_joint_lift/wire_solids.json')
        joint=json.loads(joint_path.read_text());assert set(joint)=={'H02_1','H02_2'}
        fixed.update(joint);assert len(fixed)==14
        self.targets={n:self.target(s.m) for n,s in self.ss.items()}
        self.targets.update({'Plug_'+n:self.target(s.m) for n,s in self.plug.items()})
        for n,r in fixed.items():
            m=manifold.Manifold(manifold.Mesh64(np.asarray(r['vertices_mm']),np.asarray(r['triangles'],dtype=np.uint64)))
            assert m.status()==manifold.Error.NoError,n
            self.targets['fixed_wire_'+n]=self.target(m)
        for p in [mating_path,library,hand_path,fixed_path,joint_path,A8/'amass_mating/envelopes.py',
                  A8/'amass_mating/received_dimensions.json',A8/'h06_ports.json']:
            self.sources[str(p.relative_to(PROJECT))]=sha(p)
        old_port=json.loads((A8/'h06_ports.json').read_text())['body']
        for pin,v in self.port_pins['motion_J5']['pins'].items():
            assert np.linalg.norm(v-np.asarray(old_port['pins'][str(pin)]))<1e-8
        self.assert_unchanged()

    @staticmethod
    def fingerprint(s):
        return hashlib.sha256(s.v.tobytes()+s.f.tobytes()).hexdigest()

    @staticmethod
    def target(m):
        a=m.to_mesh64();v=np.asarray(a.vert_properties[:,:3]);f=np.asarray(a.tri_verts)
        return dict(m=m,lo=v.min(0),hi=v.max(0),tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True))

    def clear(self,points,chord_error=0.,ignore=(),radius=.6604/2,surface_gap=.3):
        p=np.asarray(points)
        bound=radius+surface_gap+np.linalg.norm(np.diff(p,axis=0),axis=1).max()/2+chord_error+1e-4
        for name,s in self.targets.items():
            if name in ignore:continue
            ids=np.flatnonzero(np.all(p>=s['lo']-bound,axis=1)&np.all(p<=s['hi']+bound,axis=1))
            for i in ids:
                d=float(s['tree'].find_nearest(Vector(p[i]))[3])
                if d<bound:return dict(object=name,point_mm=p[i].tolist(),surface_distance_mm=d,required_bound_mm=float(bound))
            starts=ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
            for i in starts:
                v=p[i]
                if np.all(v>=s['lo']) and np.all(v<=s['hi']):
                    q=manifold.Manifold.sphere(.005,12).translate(v.tolist())
                    if (q^s['m']).volume()>q.volume()/2:return dict(object=name,point_mm=v.tolist(),inside=True)
        return None

    def assert_unchanged(self):
        for n,h in self.print_fingerprints.items():
            assert self.fingerprint(Solid(self.ss[n].o))==h,n
        for p,h in self.sources.items():assert sha(PROJECT/p)==h,p

    def evidence(self):
        return dict(source_main_sha256=self.source_hash,sources=self.sources,
            native_parts=len(self.ss),substituted_prints=[],mating_allocations=len(self.plug),
            fixed_candidate_wires=14,board_sources=self.board_sources,AMASS_allocations=self.amass,
            limitations=['Native board/vendor proxy limitations remain; no physical fit claim.',
                '14 existing wire solids are candidates, not an adopted or proven-installed harness.',
                'Mating shapes, crimp exits and solder/heat-shrink still include explicit allocations.'])
