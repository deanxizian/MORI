"""Actual joint ADC trial from the sequential virtual placement/route comparison.
R1022 uses the vacated C303 region; only its original footprint and BODY guards
are transformed. Delete the now-unused D2 inner stub and use deliberate pad/via
entry, preserving every native electrical and keepout rule.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143G-plan.json';assert not out.exists()
c=Copper(str(b/'R143D/MORI_Interface_C3.kicad_pcb'));assert c.sha=='c3c96f3533f00cfa936772bd6ed75650060b1b8653464ce949ed62dfd80d58ed'
a=json.loads((b/'R143F-virtual-route-checks.json').read_text())['attempts'][-1]
assert a['pose']['position_mm']==[23.5,16.2] and all(r['result']['status']=='PROPOSAL' for r in a['results'])
p={'revision':'R143G','board_sha256':c.sha,'purpose':__doc__,'translations':[{'reference':'R1022','from_mm':[41,15.6],'delta_mm':[-17.5,.6],'rotation_deg':180}],'delete_copper':[],'deleted_copper_expected':{},'routes':[],'vias':[]}
for t in c.segments:
 if t.GetNetname()=='Net-(U1001-D2_{slash}_WHEEL_ADC)' and t.GetLayer()==pcb.In3_Cu:
  u=uid(t);p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':'In3.Cu','width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
assert len(p['delete_copper'])==1
for r in a['results']:
 p['routes'].extend(dict(q,net=r['net']) for q in r['result']['routes'])
 p['vias'].extend(dict(q,net=r['net']) for q in r['result']['vias'])
p['routes'][0]['points_mm']=[[30.4,14],[30.15,14.25],[26.65,14.25],[25.8,15.1],[24.85,15.1],[24.5,15.45],[24.5,16.2]]
p['routes'][-1]['points_mm']=[[21.8,16.5],[22.1,16.2],[22.675,16.2]]
out.write_text(json.dumps(p,indent=2)+'\n')
