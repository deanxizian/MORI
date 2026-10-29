"""Refine R184 poses with actual retained SOURCE/VCAP transfer lands and C1601 feed.

The source board is unchanged. Retaining a transfer also retains its original
F-side path, not just its drawn hole. UPS 5 V bridge remains a planning release
which must be restored. All ground vias and original acceptance criteria remain.
"""
from R184_power_group_geometry import *
out=b/'R185-retained-transfer-pairs.json';assert not out.exists()
keep_vias=['23acab6c-6b1d-4c9d-9d27-5582d4cb9302','64914fe0-694a-405e-a056-eb475d079543']
keep_tracks=['67996d44-7a90-467c-a2fa-0a0ab4436544','97f94d19-2206-41f1-86a3-a4a4f588e338',
 'd80f383a-f21e-46d2-b3b9-aaa3637e14ac','ab82b1cb-be22-4f90-a4ca-3be946bbf2ec','4e37213c-d558-462a-b1fe-290b06cd18d4',
 '6de6ad6f-d44f-4f16-9c8b-38fcca2c72e1','c78b5234-9e4b-45b7-b190-e0da0512cab0','e89da60e-fc99-4a2d-b1cd-7462a83db854']
assert set(keep_vias)<=released_vias and set(keep_tracks)<=retired
via_shape=unary_union([c.shapes[u,'B.Cu'] for u in keep_vias])
back_tracks=[(c.by_id[u].GetNetname(),c.shapes[u,'B.Cu']) for u in keep_tracks if (u,'B.Cu') in c.shapes]
reset=geometry('D301',dict(position_mm=list(xy(footprints['D301'].GetPosition())),rotation_deg=footprints['D301'].GetOrientationDegrees()))
clr=c.shapes['a64ead90-f8fb-47e5-9d8d-700e6f43096f','B.Cu']
sets={};rejected={}
for ref in ['D1602','C1602','R1601','C1603']:
    data=json.loads((b/('R184-power-group-'+ref+'-poses.json')).read_text());assert data['source_sha256']==c.sha
    f=footprints[ref];owned=[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')]
    tg=unary_union([k['shape'] for k in owned if k['tracks']]);vg=unary_union([k['shape'] for k in owned if k['vias']]);fixed=tg.difference(vg)
    rows=[];reject=collections.Counter()
    for row in data['candidates']:
        g=geometry(ref,row);pos=row['position_mm'];delta=[pos[i]-xy(f.GetPosition())[i] for i in range(2)]
        guard=translate(rotate(tg,-(row['rotation_deg']-f.GetOrientationDegrees()),origin=xy(f.GetPosition())),xoff=delta[0],yoff=delta[1])
        if any(s.distance(via_shape)<.1999996-1e-9 for n,s,pt in g['pads'].values()):reject['retained_transfer_pad_clearance']+=1;continue
        if guard.difference(fixed).intersection(via_shape).area>1e-8:reject['retained_transfer_body_guard']+=1;continue
        if any(s.distance(t)<.1999996-1e-9 for n,s,pt in g['pads'].values() for m,t in back_tracks if n!=m):reject['retained_C1601_feed_pad_clearance']+=1;continue
        if any(guard.intersection(t).area>1e-8 for m,t in back_tracks):reject['retained_C1601_feed_body_guard']+=1;continue
        if not compatible(g,reset) or g['body'].intersects(clr) or any(s.distance(clr)<.1999996-1e-9 for n,s,pt in g['pads'].values()):reject['retained_reset']+=1;continue
        rows.append(g)
    sets[ref]=rows;rejected[ref]=dict(reject)
pairs=[]
for d in sets['D1602']:
    for cap in sets['C1602']:
        if compatible(d,cap):pairs.append((d,cap))
novel=[(d,cap) for d,cap in pairs if d['row']['displacement_mm']>.5]
novel.sort(key=lambda dc:(max(dc[0]['row']['adjacency_distances_mm'].values())+max(dc[1]['row']['adjacency_distances_mm'].values()),dc[1]['row']['displacement_mm']))
fixed_c3=geometry('C1603',dict(position_mm=list(xy(footprints['C1603'].GetPosition())),rotation_deg=footprints['C1603'].GetOrientationDegrees(),displacement_mm=0.0))
solutions=[];visited=0;examined=0
for d,cap in novel:
    visited+=1
    if not compatible(d,fixed_c3) or not compatible(cap,fixed_c3):continue
    rs=sorted(sets['R1601'],key=lambda r:r['row']['displacement_mm'])
    for r in rs:
        if math.dist(r['pads']['2'][2],fixed_c3['pads']['1'][2])>3+1e-7:continue
        examined+=1
        if compatible(d,r) and compatible(cap,r) and compatible(r,fixed_c3):
            solutions.append(dict(D1602=d['row'],C1602=cap['row'],R1601=r['row'],C1603=fixed_c3['row']))
            break
    if len(solutions)>=12:break
result=dict(scope=__doc__,source_sha256=c.sha,retained_non_ground_vias=keep_vias,retained_tracks=keep_tracks,
    independent_counts={k:len(v) for k,v in sets.items()},rejections=rejected,clamp_cap_pairs=len(pairs),novel_clamp_pairs=len(novel),
    novel_pairs_visited=visited,RC_pairs_examined=examined,solution_count=len(solutions),bounded_stop_after_12_distinct_clamp_cap_pairs=True,
    solutions=solutions,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['solutions','scope']}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
