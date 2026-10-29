"""Exact mutual geometry for five-part scope, with original reset position retained.

First pair clamp and charge-pump cap; RC freedom cannot rescue an overlapping
clamp/cap pair. Only novel clamp pairs proceed to simultaneous RC comparison.
No native trial, electrical restoration, thermal or global feasibility claim.
"""
from R184_power_group_geometry import *
out=b/'R184-power-group-cardinal-pairs.json';assert not out.exists()
original=geometry('D301',dict(position_mm=list(xy(footprints['D301'].GetPosition())),rotation_deg=footprints['D301'].GetOrientationDegrees()))
clr=c.shapes['a64ead90-f8fb-47e5-9d8d-700e6f43096f','B.Cu']
sets={}
for ref in ['D1602','C1602','R1601','C1603']:
    d=json.loads((b/('R184-power-group-'+ref+'-poses.json')).read_text());assert d['source_sha256']==c.sha
    rows=[]
    for row in d['candidates']:
        if row['rotation_deg'] % 90 != 0:continue
        g=geometry(ref,row)
        if not compatible(g,original):continue
        if g['body'].intersects(clr) or any(s.distance(clr)<.1999996-1e-9 for n,s,pt in g['pads'].values()):continue
        rows.append(g)
    sets[ref]=rows
pairs=[]
for d in sets['D1602']:
    for cap in sets['C1602']:
        if compatible(d,cap):pairs.append((d,cap))
novel=[(d,cap) for d,cap in pairs if d['row']['displacement_mm']>.5]
solutions=[];examined=0;visited=0
# A bounded first pass keeps C1603 and its direct ground connection exactly in
# place; only R1601 is coordinated with the clamp/cap pair. Stop after 25 useful
# geometric combinations; this is not an exhaustive four-part feasibility test.
fixed_c3=geometry('C1603',dict(position_mm=list(xy(footprints['C1603'].GetPosition())),rotation_deg=footprints['C1603'].GetOrientationDegrees(),displacement_mm=0.0))
novel.sort(key=lambda dc:(max(dc[0]['row']['adjacency_distances_mm'].values())+max(dc[1]['row']['adjacency_distances_mm'].values()),dc[1]['row']['displacement_mm']))
for d,cap in novel:
    visited+=1
    if not compatible(d,fixed_c3) or not compatible(cap,fixed_c3):continue
    rset=[r for r in sets['R1601'] if compatible(d,r) and compatible(cap,r)]
    cset=[fixed_c3]
    for r in rset:
        for z in cset:
            dist=math.dist(r['pads']['2'][2],z['pads']['1'][2])
            if dist>3+1e-7:continue
            examined+=1
            if compatible(r,z):
                solutions.append(dict(D1602=d['row'],C1602=cap['row'],R1601=r['row'],C1603=z['row'],RC_distance_mm=dist))
                if len(solutions)>=25:break
        if len(solutions)>=25:break
    if len(solutions)>=25:break
solutions.sort(key=lambda q:(q['C1603']['displacement_mm']>0.1, sum(q[k]['displacement_mm'] for k in ['C1602','R1601','C1603'])))
data=dict(scope=__doc__,source_sha256=c.sha,D301_unchanged=True,
          filtered_independent_candidates={k:len(v) for k,v in sets.items()},
          clamp_cap_pair_count=len(pairs),max_clamp_displacement_mm=max((d['row']['displacement_mm'] for d,cap in pairs),default=None),
          novel_clamp_pairs=len(novel),RC_mutual_pairs_examined=examined,solution_count=len(solutions),
          novel_pairs_visited=visited,C1603_retained=True,cardinal_rotations_only=True,bounded_stop_after_25_solutions=True,
          solutions=solutions,adopted=False)
out.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({k:v for k,v in data.items() if k not in ['solutions','scope']}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
