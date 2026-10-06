"""Independent route planning on received geometry. Never cuts a printed part.

Lengths are candidate cable centreline allocations, not released cut lengths.
Photo-derived endpoints and unknown mate shapes remain explicit blockers.
"""
import sys,json,math,heapq,hashlib,time,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
from mathutils.bvhtree import BVHTree
from interface_completion import axial
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
prior=PROJECT/'mechanical/studies/prearrival_preparation';mr=json.loads((prior/'mated_connector_review.json').read_text())
assert mr['sources']['inventory']==hashlib.sha256((PROJECT/'mechanical/sources/populated_P5/inventory.json').read_bytes()).hexdigest()
with bpy.data.libraries.load(str(prior/'mated_connector_review.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(PREFIX+'PREARRIVAL_Plug_')]
for o in dst.objects:
    if o:bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update()
plug={o.name.removeprefix(PREFIX+'PREARRIVAL_Plug_'):Solid(o) for o in dst.objects if o}
obstacles=dict(ss);obstacles.update({'Plug_'+k:v for k,v in plug.items()})
trees={n:BVHTree.FromPolygons([Vector(v) for v in s.v],s.f.tolist(),all_triangles=True) for n,s in obstacles.items()}
obs=list(obstacles);los=np.array([obstacles[n].lo for n in obs]);his=np.array([obstacles[n].hi for n in obs])
portrows={r['board']+'_'+r['ref']:r for r in mr['rows']}
def endpoint(key,radius):
    r=portrows[key];s=plug[key];a=np.array(r['axis']);c=np.array(r['center_mm'])
    # Exit face based on actual mating-housing envelope; do not replace a
    # physically unknown terminal/insulation shape with a verified dimension.
    exit=c+a*(max(s.v@a)-c@a)
    return exit,exit+a*(radius+1.),a

def free(p,clear):
    if not(-59<p[0]<59 and -71<p[1]<64 and 65<p[2]<150):return False
    cand=np.where(np.all(p>=los-clear,axis=1)&np.all(p<=his+clear,axis=1))[0]
    for i in cand:
        pos,norm,face,dist=trees[obs[i]].find_nearest(Vector(p))
        if dist<clear or (Vector(p)-pos).dot(norm)<-.0001:return False
    return True

def line_free(a,b,clear):
    return all(free(a+(b-a)*t,clear) for t in np.linspace(0,1,max(2,int(np.linalg.norm(b-a)/.6)+1)))

def solve(a,b,clear):
    step=2.;origin=np.array([-60.,-72.,64.]);cache={}
    def coord(k):return origin+np.array(k)*step
    def ok(k):
        if k not in cache:cache[k]=free(coord(k),clear)
        return cache[k]
    def anchor(p):
        k=np.rint((p-origin)/step).astype(int);choices=[]
        for x in range(-2,3):
            for y in range(-2,3):
                for z in range(-2,3):
                    q=tuple(k+np.array([x,y,z]))
                    if ok(q) and line_free(p,coord(q),clear):choices.append((np.linalg.norm(p-coord(q)),q))
        return min(choices)[1] if choices else None
    ka,kb=anchor(a),anchor(b)
    if ka is None or kb is None:return None,dict(reason='No clear connection from terminal exit to grid',start_anchor=ka,end_anchor=kb,visited=len(cache))
    neigh=[(np.array([x,y,z]),float(np.linalg.norm([x,y,z])*step)) for x in [-1,0,1] for y in [-1,0,1] for z in [-1,0,1] if x or y or z]
    queue=[(0,0,ka)];cost={ka:0};prev={};visited=0;goal=coord(kb)
    while queue and visited<140000:
        _,g,k=heapq.heappop(queue)
        if g>cost.get(k,1e99)+1e-8:continue
        visited+=1
        if k==kb:
            path=[k]
            while k!=ka:k=prev[k];path.append(k)
            pts=[a]+[coord(k) for k in reversed(path)]+[b]
            # Visibility simplification is checked against the same clearance.
            out=[pts[0]];j=0
            while j<len(pts)-1:
                nxt=j+1
                for q in range(len(pts)-1,j,-1):
                    if line_free(pts[j],pts[q],clear):nxt=q;break
                out.append(pts[nxt]);j=nxt
            return out,dict(visited=visited,grid_mm=step,clearance_radius_mm=clear)
        for delta,ln in neigh:
            q=tuple(np.array(k)+delta);ng=g+ln
            if ng>=cost.get(q,1e99) or not ok(q):continue
            # Midpoint rejects diagonal corner cutting through thin solids.
            if not free((coord(k)+coord(q))/2,clear):continue
            cost[q]=ng;prev[q]=k;heapq.heappush(queue,(ng+np.linalg.norm(coord(q)-goal),ng,q))
    return None,dict(reason='No path within finite grid/search bound; not a proof of impossibility',visited=visited,grid_mm=step)

def rounded(points,R):
    # Tangential circular bends with target radius. Reject short-leg cases
    # instead of silently accepting a smaller bend radius.
    trims=[0.]
    for i in range(1,len(points)-1):
        a,b,c=map(np.array,points[i-1:i+2]);u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b)
        trims.append(R*math.tan(math.acos(np.clip(u@v,-1,1))/2))
    trims.append(0.)
    if any(trims[i]+trims[i+1]>np.linalg.norm(np.array(b)-a)-.05 for i,(a,b) in enumerate(zip(points,points[1:]))):return None
    out=[points[0]];used=[]
    for i in range(1,len(points)-1):
        a,b,c=map(np.array,points[i-1:i+2]);u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b)
        th=math.acos(np.clip(u@v,-1,1))
        if th<1e-5:continue
        trim=R*math.tan(th/2)
        start=b-u*trim;end=b+v*trim;normal=np.cross(u,v);normal/=np.linalg.norm(normal)
        center=start+np.cross(normal,u)*R;w=start-center
        out.append(start)
        for t in np.linspace(0,th,max(3,int(R*th/.5)+1))[1:]:
            out.append(center+w*math.cos(t)+np.cross(normal,w)*math.sin(t))
        used.append(R)
    out.append(points[-1]);return out

def resample(points,step=1.2):
    pts=np.array(points);ds=np.linalg.norm(np.diff(pts,axis=0),axis=1);cum=np.r_[0,np.cumsum(ds)]
    goals=np.linspace(0,cum[-1],max(3,int(cum[-1]/step)+1))
    return np.array([np.interp(goals,cum,pts[:,i]) for i in range(3)]).T

def bend_radius(points):
    p=np.array(points);a=p[1:-1]-p[:-2];b=p[2:]-p[1:-1];c=p[2:]-p[:-2]
    doublearea=np.linalg.norm(np.cross(a,b),axis=1)
    rad=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)*np.linalg.norm(c,axis=1)/(2*np.maximum(doublearea,1e-12))
    return float(min(rad))

def relax(points,clear,target):
    pts=resample(points)
    for iteration in range(360):
        for i in range(1,len(pts)-1):
            q=pts[i]*.55+(pts[i-1]+pts[i+1])*.225
            if free(q,clear):pts[i]=q
        if iteration%30==29:pts=resample(pts)
        if iteration>60 and bend_radius(pts)>=target and all(line_free(a,b,clear) for a,b in zip(pts,pts[1:])):return [p for p in pts]
    return None

def waypoint_candidates(hid,a,b,aa,ab):
    # Reviewable route corridors using existing open edges. All points are
    # candidate controls; the actual tangent arcs, not the corners, are checked.
    if hid=='H01':
        for za,zb,yback in itertools.product([138,140,142,144],[140,143,146,150],[-34,-39,-44,-50]):
            yield [a,np.array([a[0],a[1],za]),np.array([a[0],yback,za]),np.array([b[0],yback,zb]),np.array([b[0],b[1],zb]),b]
    if hid=='H05':
        for up,x,y in itertools.product([5,6,7,8,10],[16,20,24,28],[-12,-18,-24]):
            yield [a,a+aa*up,np.array([x,y,141]),np.array([20,b[1],b[2]+8]),b+ab*8,b]
    if hid=='H04':
        for xx,ys,zs,zb in itertools.product([54,55,56,57,58],[-20,-25,-30,-35],[127,130,133,136],[86,88,90]):
            yield [a,np.array([38,-47,136]),np.array([xx,ys,zs]),np.array([xx,ys,104]),np.array([xx,-46,96]),np.array([b[0],b[1],zb]),b]
        for xx,yback,ztop,zbottom in itertools.product([16,18,20,22],[-64,-65,-66,-67,-68],[132,133,134,136],[86,88,90,92]):
            yield [a,np.array([xx,a[1]-5,ztop]),np.array([xx,yback,ztop]),np.array([xx,yback,zbottom]),np.array([b[0],yback,zbottom]),np.array([b[0],b[1],zbottom]),b]
        for xx,yback,ztop,zbottom in itertools.product([18,10,0,-10,-22],[-63,-66,-69],[136,140,144],[92,96,100]):
            yield [a,a+aa*10,np.array([xx,a[1],ztop]),np.array([xx,yback,ztop]),np.array([xx,yback,zbottom]),np.array([b[0],b[1],zbottom]),b]

def solid_hits(points,radius):
    hs=[]
    for a,b in zip(points,points[1:]):
        a=np.array(a);b=np.array(b);ln=np.linalg.norm(b-a)
        if ln<1e-5:continue
        m=axial(radius,ln,(a+b)/2,(b-a)/ln);bb=np.array(m.bounding_box())
        for n,s in obstacles.items():
            if np.any(bb[3:]<s.lo)or np.any(s.hi<bb[:3]):continue
            v=max(0,(m^s.m).volume())
            if v>.02:hs.append(dict(part=n,overlap_mm3=v,segment=[a.tolist(),b.tolist()]))
    return hs

specs=[('H01','power_J17','motion_J1',1.6,6),('H02','motion_J2','power_J13',1.35,6),('H03','motion_J3','power_J14',1.35,6),('H04','motion_J4','imu_J1',2.5,8),('H05','motion_J7','power_J10',2.5,8),('H04_splitA','motion_J4','imu_J1',1.4,6),('H04_splitB','motion_J4','imu_J1',1.4,6),('H05_splitA','motion_J7','power_J10',1.4,6),('H05_splitB','motion_J7','power_J10',1.4,6)]
rows=[]
for hid,pa,pb,r,R in specs:
    exa,a,aa=endpoint(pa,r);exb,b,ab=endpoint(pb,r)
    if '_split' in hid:
        shift=-4. if hid.endswith('A') else 4.
        exa=exa+np.array([shift,0,0]);a=a+np.array([shift,0,0])
        ofs=np.array([0,shift,0]) if hid.startswith('H05') else np.array([shift,0,0])
        exb=exb+ofs;b=b+ofs
    raw,stats=solve(a,b,r+.6)
    row=dict(id=hid,from_port=pa,to_port=pb,bundle_diameter_allocation_mm=r*2,bend_radius_requirement_mm=R,required_solid_margin_mm=.6,data_status='ASSUMED cable envelope; board endpoints from native received geometry',exit_faces_mm=[exa.tolist(),exb.tolist()],search=stats)
    if raw:
        curve=rounded(raw,R);row['curve_construction']='Analytic tangent circular arcs'
        row['polyline_mm']=[p.tolist() for p in raw]
        row['polyline_length_mm']=sum(float(np.linalg.norm(b-a)) for a,b in zip(raw,raw[1:]))
        if curve is None or not all(free(p,r+.3) for p in curve):
            curve=relax(raw,r+.6,R);row['curve_construction']='Relaxed sampled path'
        if curve is None:
            for controls in waypoint_candidates(hid.split('_')[0],a,b,aa,ab):
                candidate=rounded(controls,R)
                if candidate is not None and all(free(p,r+.3) for p in resample(candidate,.6)):
                    if all(line_free(p,q,r+.3) for p,q in zip(candidate,candidate[1:])):
                        curve=candidate;row['refined_controls_mm']=[p.tolist() for p in controls];row['method']='Tangential radius-preserving corridor refinement';row['curve_construction']='Analytic tangent circular arcs';break
        if curve:
            hs=solid_hits(curve,r);row.update(curve_mm=[p.tolist() for p in curve],solid_hits=hs,status='PASS' if not hs else 'FAIL',length_mm=sum(float(np.linalg.norm(b-a)) for a,b in zip(curve,curve[1:])))
            row['sampled_min_bend_radius_mm']=bend_radius(resample(curve,.5))
            row['analytic_arc_radius_mm']=R if row['curve_construction']=='Analytic tangent circular arcs' else None
            row['bend_note']='Resampled polyline circumradius is a tessellation diagnostic. Use analytic_arc_radius_mm for designed circular bends; terminal fanout and actual wire qualification remain open.'
            row['scope']='Static nominal cable envelope versus rigid parts only; no terminal fanout, anchoring, wire-to-wire or dynamic qualification.'
        else:row.update(status='BLOCKED',reason='Clear raw corridor found, but target bend radius cannot yet be retained; hand refine waypoints before release.')
    else:row.update(status='BLOCKED',reason=stats['reason'])
    if '_split' in hid:row['proposal_note']='Two4-wire sub-bundles within the same PHR-8; no new connector or changed pin map. These four-pin-zone exits and OD2.8 allocation are candidate only; exact pin ordering, endpoint fanout, strain relief and wire-to-wire clearance must still be checked.'
    rows.append(row);print(hid,row['status'],row.get('length_mm'),row.get('reason',''),flush=True)

# Record all circuits, including branching harnesses, without inventing lengths
# for missing components or new physical connector orientations.
electrical=json.loads((PROJECT/'contracts/electrical_interfaces.json').read_text());branches={}
for h in electrical['harness']:
    a=h['from_'];b=h['to'];key=' | '.join(str(v) for v in [h['harness_id'],a['board'],a['connector'],b['board'],b['connector']])
    branches.setdefault(key,dict(id=h['harness_id'],from_=a['board']+'/'+str(a['connector']),to=b['board']+'/'+str(b['connector']),pins=[],wire_gauges=set()))
    branches[key]['pins'].append(dict(from_pin=a['pin'],from_signal=a['signal'],to_pin=b['pin'],to_signal=b['signal']))
    branches[key]['wire_gauges'].add(h['wire_gauge'])
for b in branches.values():b['wire_gauges']=sorted(b['wire_gauges']);b['status']='BLOCKED';b['length_mm']=None
out=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),electrical_contract_sha256=hashlib.sha256((PROJECT/'contracts/electrical_interfaces.json').read_bytes()).hexdigest(),static_routes=rows,circuit_branches=list(branches.values()),status='BLOCKED',limits=['No source geometry, connector pose or electrical pin map changed.','All bundle diameters, insulation sizes and bend radii are requirements to qualify, not measured cable properties.','These candidate routes omit terminal strain relief and wire-to-wire crowding; cut lengths are NOT released.','Moving-head loops, speaker pair, LCD18p FFC and camera FPC require separate explicit routing.','Charging module, braking resistors, pack/fuse leads and issue7 have unresolved physical endpoints.'])
(HERE/'harness_routes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
