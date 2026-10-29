"""Read-only ground-stitch screening for the two actual R178D ground islands.

Through-via checks preserve all original keepouts, physical copper and the fifty
source power-width reservations. Candidate sites need native refill and full
regression; this is neither an adopted board nor physical qualification.
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from shapely import from_wkb
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import mask

b=Path('robot/.state/c3-completion/trials');out=b/'R178-ground-sites.json';assert not out.exists()
c=Copper(str(b/'R178D/MORI_Interface_C3.kicad_pcb'))
anchors=c.anchors('GND');parent={uid(a):uid(a) for a in anchors};regions={}
def root(k):
    parent.setdefault(k,k)
    while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
    return k
def join(a,z):parent[root(a)]=root(z)
for ly in LAYERS:
    for i,g in enumerate(parts(c.copper.get(('GND',ly),GeometryCollection()))):
        key=(ly,i);regions[key]=g;root(key)
        for a in anchors:
            s=c.shapes.get((uid(a),ly))
            if s is not None and s.intersects(g):join(uid(a),key)
obstacles=[s.buffer(.453) for (u,ly),s in c.shapes.items()
           if isinstance(c.by_id[u],pcb.PAD) or c.by_id[u].GetNetname()!='GND']
obstacles += [k['shape'].buffer(.253) for k in c.keepouts if k['vias']]
obstacles += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.303) for v in c.vias]
obstacles += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.553)
              for p in c.pads if max(xy(p.GetDrillSize()))>0]
rdir=b/'R177-supply-reservations-v3';reservations=json.loads((rdir/'result.json').read_text())
assert len(reservations['roundtrip_checks'])==50 and all(r['status']=='PASS' for r in reservations['roundtrip_checks'])
for row in reservations['files']:
    payload=(rdir/row['path']).read_bytes();assert hashlib.sha256(payload).hexdigest()==row['sha256']
    obstacles.append(from_wkb(payload).buffer(.653 if row['layer'].startswith('In') else .453))
blocked=unary_union(obstacles)
plane=c.copper['GND','In1.Cu'].intersection(c.copper['GND','In4.Cu']).buffer(-.253)
xs=np.arange(.8,69.201,.025);ys=np.arange(.8,34.201,.025);xx,yy=np.meshgrid(xs,ys)
clear=~mask(blocked,xx,yy)&mask(plane,xx,yy,True)
rows=[]
for name in ['C909.2','R714.1']:
    pad=next(p for p in c.pads if c.pad_name(p)==name);r=root(uid(pad))
    own={ly:unary_union([g for key,g in regions.items() if key[0]==ly and root(key)==r]) for ly in LAYERS}
    sites=[]
    for ly in ['F.Cu','B.Cu']:
        acceptable=clear&mask(own[ly].buffer(-.253),xx,yy,True)
        for yi,xi in zip(*np.where(acceptable)):
            pt=(round(float(xs[xi]),6),round(float(ys[yi]),6))
            sites.append(dict(position_mm=pt,contact_layer=ly,pad_distance_mm=Point(pt).distance(Point(xy(pad.GetPosition())))))
    sites.sort(key=lambda r:r['pad_distance_mm'])
    rows.append(dict(pad=name,position_mm=xy(pad.GetPosition()),face=c.pad_faces[uid(pad)],
                     isolated_regions=[dict(layer=ly,area_mm2=g.area,bounds_mm=g.bounds) for ly,g in own.items() if not g.is_empty],
                     candidate_count=len(sites),candidates=sites[:30]))
result=dict(scope=__doc__,board_sha256=c.sha,source_reservations_sha256=reservations['source_sha256'],grid_mm=.025,rows=rows,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(rows,indent=2))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
