"""Targeted searches on native R175 alternatives, with verified supply guards.

Each source is a refilled independent candidate. Ground vias retain native
geometry restrictions; only the foreign-via antipad proxy is inapplicable to
GND. Acceptance checks are unchanged. No PCB is written by this search.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_guarded_loops_expanded.py').read_text()
src=src.replace("rev+'-R175-guarded-loops'", "rev+'-R175-followup'")
old="data=json.loads((b/file).read_text()); assert data['source_sha256']==c.sha"
new="data=json.loads((b/file).read_text()); assert data['source_sha256']==hashlib.sha256((b/'R174B/MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest()"
assert src.count(old)==1;src=src.replace(old,new)
old="reserves=[(r,LineString(r['points_mm']).buffer(r['preserved_width_mm']/2)) for r in reserve_rows]"
new=old+"\nassert all(g.difference(c.copper[r['net'],r['layer']]).area<1e-6 for r,g in reserves)"
assert src.count(old)==1;src=src.replace(old,new)
start=src.index('tasks=[');end=src.index('\nrows=[]',start)
src=src[:start]+"tasks=([('ina_input_plus','R1706.2','U1701.1')] if rev=='R175B' else [('supervisor_gnd','C1304.2','U1302.2'),('supervisor_ct','R1310.1','U1302.4'),('supervisor_vdd','C1304.1','U1302.5'),('supervisor_sense','U1302.5','U1302.6')])"+src[end:]
old=' if net not in geometries:geometries[net]=p.geometry(net)'
new='''
 if net not in geometries:
  saved_common=p.via_common
  if net=='GND':
   common=[s.buffer(.457) for (u,_),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD)]
   common.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
   common.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias)
   common.extend(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0)
   p.via_common=unary_union(common)
  geometries[net]=p.geometry(net);p.via_common=saved_common
'''
assert src.count(old)==1;src=src.replace(old,new)
src=src.replace(" if net=='GND':vf=np.zeros_like(vf)", " # Additional GND transfers are possible if all geometric constraints pass.")
src=src.replace("  assert not actual or net!='GND'", "  assert all(v['diameter_mm']==.5 and v['drill_mm']==.3 for v in actual)")
exec(compile(src,str(__file__),'exec'))
