"""Joint HEAD_OE signal-transfer and C601 GND-return geometry screen.

Both original via UUIDs/padstacks retained; five exact terminal segments are
prospectively replaced. Preserves native keepouts and all other source copper.
This is only bounded geometry, not acceptance or a routability proof.
"""
import json,math,sys
from pathlib import Path
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R185-joint-return-moves.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
gv=c.by_id['2e7f36fc-97b4-4bdc-ac9d-b6a6321965ed'];sv=c.by_id['2ceba827-433b-44de-af01-ce89cb121093'];net=sv.GetNetname()
retired={'1e6e4d91-7a6d-45e9-b841-a86fe7e91a87','9c5adea9-2cc4-48c2-b27e-6f1e509908f4','0b73501d-5218-471d-b279-d5d0ec7a63a8','33e4355a-601b-4b18-a5d3-3898bad38203','c498f839-de08-4b3f-8baa-cfc725dc5d77'}
omit=retired|{uid(gv),uid(sv)};routeblocks={};via_blocks={}
for n in ['GND',net]:
    obs=[]
    for (u,ly),s in c.shapes.items():
        if u in omit:continue
        o=c.by_id[u]
        if isinstance(o,pcb.PAD) or o.GetNetname()!=n:obs.append(s.buffer(.457))
        elif isinstance(o,pcb.PCB_VIA):obs.append(Point(xy(o.GetPosition())).buffer(.607))
    obs.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
    obs.extend(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0)
    via_blocks[n]=prep(unary_union(obs))
    for ly in ['F.Cu','B.Cu','In3.Cu']:
        obs=[s.buffer(.305) for (u,l),s in c.shapes.items() if u not in omit and l==ly and c.by_id[u].GetNetname()!=n]
        obs.extend(k['shape'].buffer(.105) for k in c.keepouts if k['tracks'] and ly in k['layers'])
        obs.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.405) for v in c.vias if uid(v) not in omit and v.GetNetname()!=n)
        obs.extend(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.405) for p in c.pads if max(xy(p.GetDrillSize()))>0 and p.GetNetname()!=n)
        routeblocks[n,ly]=prep(unary_union(obs))
refstrokes=[c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(c.copper['GND',REFERENCE[c.board.GetLayerName(t.GetLayer())]]) for t in c.segments if uid(t) not in retired and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
refguard=prep(unary_union(refstrokes).buffer(.657))
gnd=prep(c.copper['GND','In1.Cu'].intersection(c.copper['GND','In4.Cu']).buffer(-.257))
transfers=unary_union([s.buffer(.405) for o in c.anchors(net) for ly in ['In1.Cu','In4.Cu'] for s in [reference_transfer_shape(c,o,ly)] if s is not None])
power=unary_union([g for n,ly,g in c.fills if n!='GND'])
def paths(a,z):
    dx,dy=z[0]-a[0],z[1]-a[1];d=min(abs(dx),abs(dy));sx=1 if dx>=0 else -1;sy=1 if dy>=0 else -1
    for mid in [(a[0]+sx*d,a[1]+sy*d),(z[0]-sx*d,z[1]-sy*d)]:
        pts=[list(a)]
        if math.dist(mid,a)>1e-7 and math.dist(mid,z)>1e-7:pts.append(list(mid))
        pts.append(list(z));yield pts
def select_routes(n,q,terminals):
    rs=[]
    for ly,a in terminals:
        options=[]
        for pts in paths(a,q):
            line=LineString(pts)
            if routeblocks[n,ly].intersects(line):continue
            if n!='GND':
                full=line.buffer(.1)
                own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==n])
                missing=full.difference(own).difference(c.copper['GND',REFERENCE[ly]]).difference(transfers.union(Point(q).buffer(.655)))
                if missing.area>1e-6:continue
            options.append((line.length,pts))
        if not options:return None
        length,pts=min(options);rs.append(dict(net=n,layer=ly,width_mm=.2,points_mm=pts,length_mm=length))
    return rs
grounds=[];signals=[]
for ix in range(2290,2331):
    for iy in range(296,341):
        q=(ix/40,iy/40);pt=Point(q)
        if math.dist(q,xy(gv.GetPosition()))>1 or via_blocks['GND'].intersects(pt) or not gnd.contains(pt):continue
        rs=select_routes('GND',q,[('B.Cu',(57.9,9.325))])
        if rs and sum(r['length_mm'] for r in rs)<=1.719975:
            grounds.append(dict(position_mm=q,routes=rs))
for ix in range(2360,2401):
    for iy in range(324,369):
        q=(ix/40,iy/40);pt=Point(q)
        if math.dist(q,xy(sv.GetPosition()))>1 or via_blocks[net].intersects(pt) or refguard.intersects(pt):continue
        rs=select_routes(net,q,[('F.Cu',(60.4,8.75)),('B.Cu',(59.45,8.45)),('In3.Cu',(59.1,9.4))])
        if rs:signals.append(dict(position_mm=q,routes=rs))
pairs=[]
oldvoid=unary_union([Point(xy(gv.GetPosition())).buffer(.655),Point(xy(sv.GetPosition())).buffer(.655)])
for g in grounds:
    gp=Point(g['position_mm'])
    for s in signals:
        sp=Point(s['position_mm']);dist=gp.distance(sp)
        if not .707<dist<=1.95:continue
        if any(LineString(r['points_mm']).distance(gp)<.557 for r in s['routes']):continue
        if any(LineString(r['points_mm']).distance(sp)<.557 for r in g['routes']):continue
        if any(LineString(r['points_mm']).distance(LineString(t['points_mm']))<.405 for r in g['routes'] for t in s['routes'] if r['layer']==t['layer']):continue
        newvoid=gp.buffer(.655).union(sp.buffer(.655))
        pairs.append(dict(ground=g,signal=s,transition_distance_mm=dist,added_power_projection_mm2=newvoid.difference(oldvoid).intersection(power).area))
pairs.sort(key=lambda r:(r['added_power_projection_mm2'],sum(x['length_mm'] for x in r['ground']['routes']+r['signal']['routes'])))
result=dict(scope=__doc__,source_sha256=c.sha,ground_uuid=uid(gv),signal_uuid=uid(sv),retired_tracks=sorted(retired),ground_pose_count=len(grounds),signal_pose_count=len(signals),pair_count=len(pairs),pairs=pairs,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['pairs','scope']}|{'best':pairs[:2]}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
