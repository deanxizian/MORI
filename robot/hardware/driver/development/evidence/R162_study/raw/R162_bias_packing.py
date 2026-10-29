"""Nominal bias pair packing near ENABLE, without claiming its connection.
The strict direct B-link search had no eligible R1311 pose. Preserve all its
physical/copper/common-node screens, expand the search region, and leave the
ENABLE link explicitly unfinished for a separate via/layer routing trial.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R162_bias_near_enable.py').read_text().split('"""',2)[2]
s=s.replace("out=b/'R162-bias-near-enable.json'","out=b/'R162-bias-packing.json'")
s=s.replace("[((255,307),(47,68)),((315,345),(24,48))]","[((245,345),(24,82))]")
s=s.replace("if not ep:continue\n    enable_paths[ident]=sorted(ep,key=lambda r:r[0])[:4]","enable_paths[ident]=sorted(ep,key=lambda r:r[0])[:4]")
old="""    for elen,eps in enable_paths[a['id']]:
     if not legal_route(enable,eps,pa['2'][1],body,mid_lands.union(pz['1'][1])) or LineString(eps).distance(LineString(ps))<.402:continue
     pairs.append({'score':LineString(ps).length+elen,'poses':[a,z],'common_node_route_B_mm':ps,'enable_route_B_mm':eps,'mid_length_mm':LineString(ps).length,'enable_length_mm':elen})"""
new="""    distance=Point(pa['2'][2]).distance(target)
    pairs.append({'score':LineString(ps).length+distance,'poses':[a,z],'common_node_route_B_mm':ps,'enable_route_B_mm':None,'mid_length_mm':LineString(ps).length,'distance_to_existing_enable_copper_mm':distance,'enable_connection':'UNFINISHED'})"""
assert s.count(old)==1;s=s.replace(old,new)
exec(compile(s,'R162_bias_packing_preserved_geometry','exec'))
