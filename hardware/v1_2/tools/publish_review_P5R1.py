#!/usr/bin/env python3
"""Publish routing-only P5R1 motion revision; preserve mechanics/firmware and other boards."""
from pathlib import Path
from datetime import datetime,timezone
import json,csv,hashlib,copy
H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P5R1';R=O/'reports/MORI_motion_P5R1';N='MORI_motion_P5R1';D=H/'kicad'/N;REV='V1.2-H0.5-P5R1';OLD='V1.2-H0.5-P5'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def up(v):
 if isinstance(v,str):
  if v==OLD:return REV
  return v.replace('layout_P5/reports/MORI_motion_P5','layout_P5R1/reports/MORI_motion_P5R1').replace('MORI_motion_P5R1','_CURRENT_MOTION_').replace('MORI_motion_P5',N).replace('_CURRENT_MOTION_',N)
 if isinstance(v,list):return [up(x)for x in v]
 if isinstance(v,dict):return {up(k):up(x)for k,x in v.items()}
 return v
native=load(R/'drc.json');erc=load(R/'erc.json');checks=load(R/'check_commands.json');delta=load(R/'delta.json');body=load(R/'body_review_final.json')
counts=dict(ERC=sum(len(s['violations'])for s in erc['sheets']),DRC=len(native['violations']),unconnected=len(native['unconnected_items']),parity=len(native['schematic_parity']))
assert not any(counts.values())
assert all(sha(ROOT/p)==s for log in checks for p,s in log['input_sha256'].items())
assert body['source_sha256']==sha(D/(N+'.kicad_pcb'))
assert delta['pad_net_map_identical'] and not delta['drc_exclusions']
assert not any(x['classification']=='FAIL_FOREIGN_NET'for x in body['body_crossing_inventory'])
summary={'revision':REV,'scope':'Motion board user-marked A–G routing review only; other three native PCBs unchanged','circuit_revision':OLD,'outline_mm':[70,35,1.6],'native_checks':dict(**counts,status='PASS',tool=native['kicad_version'],source_sha256=sha(D/(N+'.kicad_pcb')),report=str((R/'drc.json').relative_to(ROOT))),'pad_net_map_identical':True,'before':delta['before'],'after':delta['after'],'changed_placements':delta['changed_placements'],'foreign_body_crossing_candidates':0,'DRC_exclusions':0,'inner_signal_tracks':0,'marked_regions_reworked':list('ABCDEFG'),'user_visual_acceptance':'NOT_TESTED','full_source_rule_equivalence':'NOT_TESTED','physical_tests':'NOT_TESTED','manufacturing_release':False,'retained_exceptions':['U100 raised-module architecture and documented own-pin housing escape remain; no blanket under-body clearance claim','Other three P5 boards and their documented exceptions remain unchanged'],'comparison':'hardware/v1_2/layout_P5R1/index.html'}
save(O/'reports/verification.json',summary)
# Local native metadata; no net, footprint or schematic modifications.
j=load(D/'connectivity.json');j['revision']=REV;j['layout_revision']='P5R1';j['circuit_revision']=OLD
for c in j['components']:
 if c['ref']=='C2':c['placed_at']=[24.25,22.75,0]
save(D/'connectivity.json',j)
save(D/'layout_notes.json',summary)
# Snapshot source documents before metadata publication, not a replacement of vendor facts.
backup=H/'revisions/before_P5R1_contracts';backup.mkdir(parents=True,exist_ok=True)
for file in ['contracts/components.json','contracts/electrical_interfaces.json','hardware/pinmap.csv','hardware/harness.csv','hardware/bom.csv','hardware/v1_2/bom.csv','hardware/v1_2/assembly_parts.csv']:
 p=ROOT/file;target=backup/file
 if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
c=load(ROOT/'contracts/components.json');e=load(ROOT/'contracts/electrical_interfaces.json');assert c['revision']==OLD and e['revision']==OLD,'Read fresh concurrent contract changes before publishing'
c=up(c);e_original=e;e=up(e)
# Keep historical project snapshots exactly as previously recorded.
if 'historical_pcb_projects'in e_original:e['historical_pcb_projects']=e_original['historical_pcb_projects']
e['pcb_projects'][N]['native_checks']=summary['native_checks'];e['pcb_projects'][N]['circuit_revision']=OLD
e['hardware_schematic_revision']=OLD;e['gpio_change']=False
e['pcb_revision_relationship']='Motion P5R1 is a routing-only correction of P5; 70x35 outline, holes, connector poses, BOM and pad/net assignments unchanged. IMU/power/rear remain native P5.'
e['layout_P5R1_marked_review']=summary;c['layout_P5R1_marked_review']=summary
for contract in [c,e]:
 contract['pcb_routing_style_review']['P5R1_marked_review']=str((O/'reports/verification.json').relative_to(ROOT))
 contract['pcb_routing_style_review']['status']='NOT_TESTED' # no automatic full style/user acceptance
save(ROOT/'contracts/components.json',c);save(ROOT/'contracts/electrical_interfaces.json',e)
# Version labels/board project references only. MPNs, prices and GPIO assignments unchanged.
for file in ['hardware/pinmap.csv','hardware/harness.csv','hardware/bom.csv','hardware/v1_2/bom.csv','hardware/v1_2/assembly_parts.csv']:
 p=ROOT/file
 with p.open(encoding='utf-8-sig',newline='')as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
 new=[{k:up(v)for k,v in row.items()}for row in rows]
 with p.open('w',encoding='utf-8-sig',newline='')as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(new)
for src,dst in [('hardware/pinmap.csv','hardware/v1_2/interfaces/pinmap_'+REV+'.csv'),('hardware/harness.csv','hardware/v1_2/interfaces/harness_'+REV+'.csv'),('hardware/v1_2/bom.csv','hardware/v1_2/bom_'+REV+'.csv')]:
 (ROOT/dst).write_bytes((ROOT/src).read_bytes())
# Mechanical handoff inherits documented envelopes and unknowns, updates actual artwork/placement only.
handoff=up(load(H/'handoff/mechanical_P5.json'));handoff['revision']=REV;handoff['generated_utc']=datetime.now(timezone.utc).isoformat();handoff['change_scope']='Only motion C2 translated 0.25 mm toward U2; no outline/hole/connector changes; other board files P5 unchanged.'
handoff['boards'][N]['pcb_sha256']=sha(D/(N+'.kicad_pcb'))
handoff['boards'][N]['bare_STEP']='hardware/v1_2/mechanical/MORI_motion_P5_BARE_BOARD.step';handoff['boards'][N]['bare_STEP_note']='P5 bare outline reused: Edge.Cuts and drill positions unchanged; not a populated assembly.'
for row in handoff['boards'][N]['placements']:
 if row['reference']=='C2':
  row['xy_mm']=[24.25,22.75]
  for key in ['fab_projection_mm','native_body_and_pad_bounds_mm']:
   if row.get(key):row[key][0]-=.25;row[key][2]-=.25
save(H/'handoff/mechanical_P5R1.json',handoff)
e=load(ROOT/'contracts/electrical_interfaces.json');e['mechanical_handoff']='hardware/v1_2/handoff/mechanical_P5R1.json';save(ROOT/'contracts/electrical_interfaces.json',e)
for file in ['connector_pinmap.csv','placements.csv','assembly_parts_with_mpn.csv']:
 src=H/'layout_P5'/file;dst=O/file
 with src.open(encoding='utf-8-sig',newline='')as f:rd=csv.DictReader(f);fields=rd.fieldnames;rows=[{k:up(v)for k,v in x.items()}for x in rd]
 if file=='placements.csv':
  for row in rows:
   if row.get('board')==N and row.get('reference')=='C2':
    row['xy_mm']=json.dumps([24.25,22.75])
    for key in ['fab_projection_mm','native_body_and_pad_bounds_mm']:
     if row.get(key):coords=json.loads(row[key]);coords[0]-=.25;coords[2]-=.25;row[key]=json.dumps(coords)
 with dst.open('w',encoding='utf-8-sig',newline='')as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
save(O/'harness.json',up(load(H/'layout_P5/harness.json')))
save(O/'reports/publication.json',{'revision':REV,'status':'PASS','hardware_metadata_only':True,'mechanical_and_firmware_files_modified':False,'source_P5_preserved':sha(H/'kicad/MORI_motion_P5/MORI_motion_P5.kicad_pcb')==delta['source_pcb_sha256'],'pin_and_net_changes':False,'procurement_or_fabrication':False})
print(json.dumps({'published':REV,'native':counts,'source_preserved':True},ensure_ascii=False))
