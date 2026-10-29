"""Native-source positive and refusal cases for explicit isolated-zone contacts."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R171-isolated-contact-checks.json';assert not out.exists();c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');v=c.by_id['aa3ea505-081f-4d12-a9a9-b7d9b2cf4e57'];deleted=['35011640-47d5-43d9-aa07-7c7e24d3d8e5','bc3e9793-b9cd-54b1-b44c-64b91f6e9a06'];base=dict(remaining_contact_layers=via_contact_layers(c.board,v,deleted),reason='Explicit replacement of source VS transfer',isolated_zone_layers=['In2.Cu']);rows=[]
cases=[('isolated_In2_only',base,True),('legacy_no_exclusion',{k:x for k,x in base.items() if k!='isolated_zone_layers'},False),('real_In3_distribution',dict(base,isolated_zone_layers=['In3.Cu']),False),('both_layers',dict(base,isolated_zone_layers=['In2.Cu','In3.Cu']),False),('wrong_contact_snapshot',dict(base,remaining_contact_layers=['In3.Cu']),False),('duplicate_declaration',dict(base,isolated_zone_layers=['In2.Cu','In2.Cu']),False),('outer_layer_exclusion',dict(base,isolated_zone_layers=['F.Cu']),False),('missing_reason',dict(base,reason=''),False),('malformed_declaration',dict(base,isolated_zone_layers='In2.Cu'),False)]
for name,spec,expected in cases:
 r=obsolete_via_removal_check(c.board,v,spec,deleted);assert r['allowed']==expected,(name,r);rows.append(dict(name=name,expected_allowed=expected,result=r));print(name,'PASS',flush=True)
g=next(v for v in c.vias if v.GetNetname()=='GND');r=obsolete_via_removal_check(c.board,g,dict(base,remaining_contact_layers=via_contact_layers(c.board,g)),[]);assert not r['allowed'];rows.append(dict(name='ground_via_refused',expected_allowed=False,result=r))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,checks=rows,status='PASS'),indent=2)+'\n');print('PASS',len(rows))
