"""Bounded independent part poses for the five-part group, not a routed layout."""
from R184_group_geometry import *
ref = sys.argv[1]; assert ref in ['D1602', 'C1602', 'R1601', 'C1603']
out = b/('R184-group-'+ref+'-poses.json'); assert not out.exists()
f = footprints[ref]; origin = xy(f.GetPosition()); angle0 = f.GetOrientationDegrees()
targets = {'D1602': {'1': ('U1601.6',5), '2': ('U1601.8',5)},
           'C1602': {'1': ('U1601.4',3), '2': ('U1601.5',3)},
           'R1601': {'1': ('U1601.6',5)},
           'C1603': {'1': ('U1601.6',8)}}[ref]
# C1603's 8 mm independent bound is only the 5+3 mm triangle inequality;
# exact R1601.2 -> C1603.1 <=3 mm is checked when pairing actual poses.
targets = {k:(xy(pads[n].GetPosition()),limit) for k,(n,limit) in targets.items()}
owned = [k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')]
tg = unary_union([k['shape'] for k in owned if k['tracks']])
vg = unary_union([k['shape'] for k in owned if k['vias']])
fixedcut = tg.difference(vg)
assert vg.difference(tg).area < 1e-8
foreign = {n:unary_union([s for (u,ly),s in c.shapes.items() if ly == 'B.Cu' and u not in mine|retired|released_vias and c.by_id[u].GetNetname()!=n]+[replacement]) for n in {p.GetNetname() for p in f.Pads()}}
positions = [(x/8,y/8) for x in range(248,361) for y in range(76,203)]+[origin]
rows=[]; reject=collections.Counter()
for angle in range(0,360,45):
    part=pcb.FOOTPRINT(f); part.SetOrientationDegrees(angle)
    body,yard=fab(part),outline(part,pcb.B_CrtYd)
    gd=rotate(tg,-(angle-angle0),origin=origin)
    pp0={p.GetNumber():(p.GetNetname(),shape(p,c.ids['B.Cu']),xy(p.GetPosition())) for p in part.Pads()}
    for pos in positions:
        dx,dy=pos[0]-origin[0],pos[1]-origin[1]
        points={k:(pt[0]+dx,pt[1]+dy) for k,(n,s,pt) in pp0.items()}
        distances={k:math.dist(points[k],pt) for k,(pt,limit) in targets.items()}
        if any(distances[k]>limit+1e-7 for k,(pt,limit) in targets.items()):
            reject['adjacency_or_derived_bound']+=1;continue
        pp={k:(n,translate(s,xoff=dx,yoff=dy),points[k]) for k,(n,s,pt) in pp0.items()}
        bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy)
        if bo.intersection(bodies).area>1e-8 or ya.intersection(yards).area>1e-8 or ya.intersection(mounts).area>1e-8:
            reject['body_courtyard_mount']+=1;continue
        if ya.intersection(pth).area>1e-8:reject['PTH_inside_courtyard']+=1;continue
        if bo.intersects(holes) or any(s.distance(holes)<.299999 for n,s,pt in pp.values()):
            reject['drill_clearance']+=1;continue
        if any(s.distance(vias)<.1999996-1e-9 or s.distance(foreign[n])<.1999996-1e-9 for n,s,pt in pp.values()):
            reject['pad_clearance']+=1;continue
        gg=translate(gd,xoff=dx,yoff=dy)
        if gg.difference(fixedcut).intersection(vias).area>1e-8 or gg.intersection(tracks).area>1e-8:
            reject['native_body_guard']+=1;continue
        if bo.difference(unary_union([s for n,s,pt in pp.values()])).intersection(tracks).area>1e-8:
            reject['same_face_body_trace']+=1;continue
        rows.append(dict(position_mm=list(pos),rotation_deg=angle,displacement_mm=math.dist(pos,origin),adjacency_distances_mm=distances,
                         pads={k:dict(net=n,position_mm=list(pt)) for k,(n,s,pt) in pp.items()}))
    print(json.dumps(dict(ref=ref,angle=angle,poses=sum(r['rotation_deg']==angle for r in rows))),flush=True)
rows.sort(key=lambda r:(max(r['adjacency_distances_mm'].values()),r['displacement_mm']))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,released_refs=sorted(released_refs),prospective_retired_tracks=sorted(retired),
                              prospective_released_non_ground_vias=sorted(released_vias),grid_mm=.125,angles_deg=list(range(0,360,45)),
                              reference=ref,targets={k:dict(position=pt,limit_mm=limit) for k,(pt,limit) in targets.items()},
                              candidates=rows,rejections=dict(reject),adopted=False),indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
print(json.dumps(dict(ref=ref,poses=len(rows),best=rows[:2])),flush=True)
