"""Isolate an unapplied three-area design candidate; original files stay intact."""
import json,shutil,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;M=H.parents[1];P=M.parent;C=H/'thin_candidate_workspace'
for d in ['config','contracts','mechanical/scripts','mechanical/reports']:
 (C/d).mkdir(parents=True,exist_ok=True)
for f in (P/'config').glob('*.json'):shutil.copy2(f,C/'config'/f.name)
for f in (P/'contracts').glob('*.json'):shutil.copy2(f,C/'contracts'/f.name)
shutil.copytree(M/'scripts',C/'mechanical/scripts',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','vendor'))
for name,target in [('hardware',P/'hardware'),('mechanical/sources',M/'sources'),('mechanical/revisions',M/'revisions'),('mechanical/studies',M/'studies'),('mechanical/scripts/vendor',M/'scripts/vendor')]:
 dst=C/name
 if not dst.exists():dst.symlink_to(target,target_is_directory=True)
for f in (M/'reports').glob('*.json'):
 if f.name.startswith('solid_'):continue
 shutil.copy2(f,C/'mechanical/reports'/f.name)
shutil.copy2(M/'mori_v1_2.blend',C/'mechanical/mori_v1_2.blend')
p=json.loads((C/'config/geometry.json').read_text());p['revision']='V1.2-M1.46-C1';p['drive_print_cleanup']['bearing_bar_depth_mm']=19.2
p['prearrival_thin_cleanup_proposal']={'adopted':False,'retired_gimbal_bores':'Do not generate retired Gimbal_Base bores; no current fasteners use them','reaction_collar_bottom_extension_mm':1,'reaction_split_root':'Open split into existing axial bore; remove0.4mm dead-end web','cap_saddle_depth_mm':19.2}
(C/'config/geometry.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
f=C/'mechanical/scripts/simple_modules.py';s=f.read_text();s=s.replace("    for target in [upper,lower]:boolean(target,cyl('M2_clear'", "    for target in ([] if name.startswith('Gimbal_Base_') else [upper,lower]):boolean(target,cyl('M2_clear'",1)
s=s.replace("    boolean(lower,cyl('M2_nut_access'", "    if not name.startswith('Gimbal_Base_'):boolean(lower,cyl('M2_nut_access'",1)
s=s.replace("    if name.startswith('Gimbal_Base_'):\n        boolean(lower,cyl('open_nut_channel'", "    if False: # retired Gimbal_Base channel suppressed in isolated candidate\n        boolean(lower,cyl('open_nut_channel'",1);f.write_text(s)
f=C/'mechanical/scripts/part_consolidation.py';s=f.read_text();a=s.index("        fill=cyl('retired_joint_hole'");b=s.index("        for kind in ['Screw','Nut']",a);s=s[:a]+s[b:];f.write_text(s)
f=C/'mechanical/scripts/belly_relayout.py';s=f.read_text();s=s.replace("(0,0,tip_z+.5),rc['collar_outer_radius_mm'] if rc else 10,7)","(0,0,tip_z),rc['collar_outer_radius_mm'] if rc else 10,8)",1);s=s.replace("(8,0,tip_z+1),(12,.8,8)","(7,0,tip_z+.5),(14,.8,9)",1);f.write_text(s)
(H/'thin_candidate_setup.json').write_text(json.dumps(dict(status='NOT_TESTED',applied_to_main=False,source_blend_sha256=hashlib.sha256((M/'mori_v1_2.blend').read_bytes()).hexdigest(),workspace=str(C),proposed=p['prearrival_thin_cleanup_proposal']),indent=2)+'\n')
print('THIN_CANDIDATE_PREPARED',C)
