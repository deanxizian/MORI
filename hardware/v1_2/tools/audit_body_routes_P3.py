#!/usr/bin/env python3
"""Read-only P3 track/body screening, separate from native electrical DRC.

Bodies are conservative rectangles around native Fab shapes, excluding their
stroke. Samples inside that component's pads are excluded. This is a review
aid, not vendor mechanical qualification or an automatic exception approval.
"""
from pathlib import Path
import json, math, hashlib, csv
from collections import defaultdict
import pcbnew as k

H=Path(__file__).resolve().parents[1]
O=H/'layout_P3/body_route_review';O.mkdir(exist_ok=True)
xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y))

def rect(fp):
    shapes=[s for s in fp.GraphicalItems() if isinstance(s,k.PCB_SHAPE) and s.GetLayer() in [k.F_Fab,k.B_Fab]]
    if not shapes:return None
    boxes=[s.GetBoundingBox() for s in shapes]
    return [k.ToMM(min(b.GetX() for b in boxes))+.05,
            k.ToMM(min(b.GetY() for b in boxes))+.05,
            k.ToMM(max(b.GetRight() for b in boxes))-.05,
            k.ToMM(max(b.GetBottom() for b in boxes))-.05]

def clip(a,z,r):
    lo,hi=0.,1.
    for d,aa,mn,mx in zip([z[0]-a[0],z[1]-a[1]],a,r[:2],r[2:]):
        if abs(d)<1e-10:
            if not mn<aa<mx:return None
        else:
            t,u=sorted(((mn-aa)/d,(mx-aa)/d));lo=max(lo,t);hi=min(hi,u)
    return (lo,hi) if hi-lo>1e-5 else None

def audit(kind):
    name='MORI_'+kind+'_P3';p=H/'kicad'/name/(name+'.kicad_pcb');b=k.LoadBoard(str(p))
    records=[];bodies=[]
    for f in b.GetFootprints():
        ref=f.GetReference();r=rect(f)
        if not r or ref.startswith(('H','TP')):continue
        category='MEZZANINE' if ref=='U100' else 'CONNECTOR' if ref.startswith('J') else 'COMPONENT'
        body=dict(ref=ref,footprint=str(f.GetFPID()),rect_mm=r,side='B.Cu' if f.IsFlipped() else 'F.Cu',category=category)
        bodies.append(body);pads=list(f.Pads());padshapes=[p.GetEffectiveShape(f.GetLayer()) for p in pads]
        ownnets={p.GetNetname() for p in pads}
        for t in b.GetTracks():
            if isinstance(t,k.PCB_VIA):continue
            a,z=xy(t.GetStart()),xy(t.GetEnd());interval=clip(a,z,r)
            if interval is None:continue
            lo,hi=interval;length=math.dist(a,z);n=max(1,math.ceil(length*(hi-lo)/.025));hits=[]
            for i in range(n):
                u=lo+(hi-lo)*(i+.5)/n;x,y=a[0]+u*(z[0]-a[0]),a[1]+u*(z[1]-a[1]);v=k.VECTOR2I(k.FromMM(x),k.FromMM(y))
                if not any(s.Collide(v,0) for s in padshapes):hits.append([x,y])
            if not hits:continue
            covered=length*(hi-lo)*len(hits)/n
            if covered<.05:continue
            records.append(dict(board=name,reference=ref,category=category,side=body['side'],track_layer=b.GetLayerName(t.GetLayer()),same_side=t.GetLayer()==f.GetLayer(),net=str(t.GetNetname()),component_has_this_net=t.GetNetname() in ownnets,track_uuid=t.m_Uuid.AsString(),start_mm=a,end_mm=z,core_length_estimate_mm=round(covered,3),body_rect_mm=r,first_body_sample_mm=hits[0]))
    group=defaultdict(list)
    for q in records:group[q['same_side'],q['category']].append(q)
    summary={('same_side' if same else 'opposite_side')+'_'+cat:dict(track_body_pairs=len(rows),components=len({q['reference'] for q in rows}),reference_net_pairs=len({(q['reference'],q['net']) for q in rows})) for (same,cat),rows in group.items()}
    report=dict(board=name,pcb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),method='Native Fab rectangle core; centerline sampled at <=0.025mm, own-pad copper excluded. No zones counted. Conservative candidate screening, not all approved violations.',summary=summary,bodies=bodies,candidates=records)
    (O/(name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (O/(name+'.csv')).open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(records[0]) if records else ['board']);w.writeheader();w.writerows(records)
    print(name,json.dumps(summary),flush=True)
    same=[q for q in records if q['same_side'] and q['category']=='COMPONENT']
    by=defaultdict(set)
    for q in same:by[q['reference']].add(q['net'])
    print('SAME-SIDE COMPONENT CANDIDATES:',dict(sorted((r,sorted(n)) for r,n in by.items())),flush=True)
    return report

if __name__=='__main__':
    import sys
    for kind in sys.argv[1:] or ['motion','imu','power']:audit(kind)
