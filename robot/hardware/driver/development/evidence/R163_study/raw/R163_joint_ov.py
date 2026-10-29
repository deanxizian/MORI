"""Rotate the OV chain's last resistor to reuse its native bottom transfer.
Preserve all source GND vias, fixed interfaces and native guards. Replace the
whole obsolete OV trunk explicitly, and widen five existing HEAD_VM sense
segments to preserve the moved high-side pad's inherited 0.20 mm path screen.
This is an independent candidate, requiring complete refill/DRC/regression.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R163D-plan.json').read_text());p.update(revision='R163E',scope=__doc__)
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
for s in p['translations']:
 if s['reference']=='R1503':s['rotation_deg']=90
keep={'0fc707cc-95ab-4567-be33-db918adcae74','cff12765-4b6c-4f01-95db-d6b984f643c6'}
p['delete_copper']=[id_ for id_ in p['delete_copper'] if id_ not in keep]
for id_ in keep:p['deleted_copper_expected'].pop(id_)
p['remove_obsolete_vias']=[s for s in p['remove_obsolete_vias'] if s['uuid']!='f1a3f676-9cff-4b2d-a066-ac57c6f6faf7']
ov='Net-(U1501-INB-_{slash}_OV)';mid='Net-(R1502-~-Pad1)'
for r in p['routes']:
 if r['net']==mid and r['layer']=='B.Cu':r['points_mm']=[[57.5,33.325],[58.0,33.325],[58.5,32.825],[58.5,32.325],[58.9,31.925],[59.5,31.925]]
 if r['net']==ov and r['points_mm'][0]==[59.5,31.925]:r['points_mm']=[[60.425,30.575],[60.425,31.4],[60.1,31.725],[60.1,33.1],[59.625,33.575],[59.5,33.575]]
def delete(id_):
 t=c.by_id[id_];assert id_ not in p['delete_copper'];p['delete_copper'].append(id_)
 p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
for id_ in ['6941700c-59b2-4d55-a46b-f868f8ad8a3a','d29c1947-4ee9-4231-a599-049e3997a4a2']:delete(id_)
for id_ in ['c0905f41-23fe-4cba-9c6d-1a0941c977f8','e0d0eccd-','010030bb-4392-4fef-a869-afa4bbcdc184','607568c6-','53a78213-489c-4be7-80f8-da809184c9d0']:
 if id_.endswith('-'):id_=next(k for k in c.by_id if k.startswith(id_))
 t=c.by_id[id_];assert t.GetNetname()=='/HEAD_VM' and t.GetWidth()==200000;delete(id_)
 p['routes'].append({'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':.25,'points_mm':[list(xy(t.GetStart())),list(xy(t.GetEnd()))]})
p['routes'].append({'net':ov,'layer':'In2.Cu','width_mm':.2,'points_mm':[[54.4,31.8],[55,32.4],[55,32.8],[55.3,33.1],[58,33.1],[58.575,33.675],[58.575,34.15]]})
p['unfinished_connections']=['HEAD_UV_N original output','HEAD_UV_ENABLE original bias','all canonical remaining nets']
dest=b/'R163E-plan.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':p['revision'],'explicit_removed_tracks':len(p['delete_copper']),'source_ground_vias_preserved_by_plan':True}))
