import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
c=Copper('robot/.state/c3-completion/trials/R129D/MORI_Interface_C3.kicad_pcb');m=json.loads(Path('robot/.state/c3-completion/trials/R129D/edit_manifest.json').read_text());v=c.by_id[m[0]['uuid']];r=json.loads(Path('robot/.state/c3-completion/trials/R129D-step-regression.json').read_text());old=json.loads(Path('robot/hardware/driver/development/evidence/R127B/step-regression.json').read_text());target='4580bf19-ce85-45c8-b5d5-9e819c18a1fd'
report={'board_sha256':c.sha,'added_ground_via':{'uuid':uid(v),'position_mm':xy(v.GetPosition()),'diameter_mm':v.GetWidth(c.ids['F.Cu'])/1e6,'drill_mm':v.GetDrillValue()/1e6},'reference_contacts':[],'before':next(x for x in old['reference_transitions'] if x['uuid']==target),'after':next(x for x in r['reference_transitions'] if x['uuid']==target),'GND_pad_count':sum(p.GetNetname()=='GND' for p in c.pads),'GND_groups_count':len(c.pad_groups()['GND']),'power_width_checks':len(r['power_width']),'power_width_failures':sum(x['status']!='PASS' for x in r['power_width']),'limits':'Project 2 mm return-stitch screen only; not EMC or impedance qualification; power current and physical validation remain NOT_TESTED.'}
for ly in ['In1.Cu','In4.Cu']:
 land=c.shapes[uid(v),ly];fill=unary_union([g for net,l,g in c.fills if net=='GND' and l==ly]);report['reference_contacts'].append({'layer':ly,'land_area_mm2':land.area,'fill_overlap_mm2':land.intersection(fill).area,'connected':land.intersects(fill)})
assert all(x['connected'] for x in report['reference_contacts']) and report['after']['status']=='PASS' and report['GND_groups_count']==1 and report['power_width_failures']==0
Path('robot/.state/c3-completion/trials/R129D-stitch-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
