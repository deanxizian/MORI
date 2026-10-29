"""Isolate the redundant moved 3V3 via after removing the bad new sampling hole.

This proves only which original width anchors are lost. The source control
already has an open UPS sampling branch and is not an acceptable layout.
"""
import json,sys,shutil,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');root=b/'R158-fill-cause';source=root/'remove_new_sampling_via';dest=root/'remove_sampling_and_3V3_vias';shutil.copytree(source,dest)
script='''import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
p=Path(sys.argv[1]);c=Copper(p);v=c.by_id['9fc6be27-25b2-4bce-8f44-98f39ccd1aa1'];assert v.GetNetname()=='MOTION_3V3';assert via_contact_layers(c.board,v)==['In3.Cu'];c.board.Remove(v);pcb.SaveBoard(str(p),c.board)
'''
helper=root/'remove_redundant_control.py';helper.write_text(script);py=str(Path(sys.executable).absolute());cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';name='remove_sampling_and_3V3_vias';records=[]
commands=[[py,str(helper),str(dest/'MORI_Interface_C3.kicad_pcb')],[cli,'pcb','drc','--format','json','--schematic-parity','--refill-zones','--save-board','--severity-all','--exit-code-violations','-o',str(root/(name+'-drc.json')),str(dest/'MORI_Interface_C3.kicad_pcb')],[py,'robot/hardware/driver/development/scripts/audit_candidate.py','robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',str(dest/'MORI_Interface_C3.kicad_pcb'),str(root/(name+'-audit.json'))]]
for i,argv in enumerate(commands):
 r=subprocess.run(argv,text=True,capture_output=True);records.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});(root/(name+'-commands.json')).write_text(json.dumps(records,indent=2)+'\n');assert r.returncode in ((0,5) if i==1 else (0,)),r.stderr
report=json.loads((root/(name+'-audit.json')).read_text());id_='9fc6be27-25b2-4bce-8f44-98f39ccd1aa1';power=[x for x in report['power_width'] if x['net']=='MOTION_3V3'];checks=[{'width_mm':x['width_mm'],'lost_pair_count':len(x['lost_pairs']),'losses_only_removed_anchor':all(id_ in pair for pair in x['lost_pairs'])} for x in power]
result={'scope':__doc__,'board_sha256':report['board_sha256'],'MOTION_3V3_width_checks':checks,'MOTION_3V3_lost_pad_connections':[x for x in report['lost_pad_connections'] if x['net']=='MOTION_3V3'],'all_other_MOTION_3V3_anchor_width_pairs_preserved':all(x['losses_only_removed_anchor'] for x in checks),'engineering_status':'FAIL','adopted':False}
(root/'redundant-via-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
