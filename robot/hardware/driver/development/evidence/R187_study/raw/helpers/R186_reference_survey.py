"""Whole-board mapped-reference survey of the unchanged R181C PCB.

Unlike a delta regression, inspect every existing non-GND track. Apply the same
native-pad and same-net plated-transfer exclusions used by audit_candidate.
This identifies inherited geometric review items, not measured signal failure.
"""
import collections,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R186-full-reference-survey.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
start=time.monotonic();rows=[];cache={};zone_clearance=inner_zone_clearance(c.path)
for t in c.segments:
 net=t.GetNetname();ly=c.board.GetLayerName(t.GetLayer())
 if net=='GND':continue
 ref=REFERENCE[ly];key=net,ly
 if key not in cache:
  lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  clearance=max([zone_clearance]+[z.GetLocalClearance()/1e6 for z in c.zones if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.IsOnLayer(c.ids[ref])])
  islands=[]
  for region in parts(c.copper[net,ly]):
   transfer_shapes=[];transfer_ids=[]
   for v in c.anchors(net):
    land=c.shapes.get((uid(v),ly));ground_land=reference_transfer_shape(c,v,ref)
    if land is not None and ground_land is not None and region.intersects(land):
     transfer_shapes.append(ground_land.buffer(clearance+.005));transfer_ids.append(uid(v))
   islands.append((region,unary_union(transfer_shapes),transfer_ids))
  cache[key]=lands,islands
 lands,islands=cache[key];stroke=c.shapes[uid(t),ly]
 exemptions=unary_union([ex for region,ex,ids in islands if region.intersects(stroke)])
 missing=stroke.difference(lands).difference(c.copper.get(('GND',ref),GeometryCollection())).difference(exemptions)
 rows.append(dict(uuid=uid(t),net=net,layer=ly,reference_layer=ref,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())),width_mm=t.GetWidth()/1e6,
                  missing_reference_mm2=missing.area,status='REVIEW_REQUIRED' if missing.area>1e-6 else 'PASS',
                  missing_bounds_mm=list(missing.bounds) if not missing.is_empty else []))
flags=[r for r in rows if r['status']=='REVIEW_REQUIRED'];nets=collections.defaultdict(list)
for row in flags:nets[row['net']].append(row)
summary=[dict(net=n,tracks=len(v),sum_missing_mm2=sum(r['missing_reference_mm2'] for r in v),layers=dict(collections.Counter(r['layer'] for r in v))) for n,v in nets.items()]
summary.sort(key=lambda r:-r['sum_missing_mm2'])
result=dict(scope=__doc__,source_sha256=c.sha,non_GND_tracks_reviewed=len(rows),flagged_tracks=len(flags),flagged_nets=len(summary),by_net=summary,tracks=rows,
            threshold_mm2=1e-6,elapsed_seconds=time.monotonic()-start,source_saved=False,physical='NOT_TESTED',manufacturing_release=False,
            interpretation='Inherited mapped-plane coverage gaps requiring location and circuit review. Not a native DRC result, measured noise level or global unroutability proof.')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['tracks','by_net','scope']}|{'largest_nets':summary[:8]}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
