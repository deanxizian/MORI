#!/usr/bin/env python3
"""Publish checked P3 hardware interfaces only; never alter mechanics/firmware."""
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
import hashlib,json,shutil
H=Path(__file__).resolve().parents[1];R=H.parents[1];O=H/'layout_P3';REV='V1.2-H0.3-P3'
read=lambda p:json.loads(p.read_text())
def put(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def publish():
 report=read(O/'reports/verification.json');assert report['native_cad_status']=='PASS'
 for board in report['boards'].values():
  for path,digest in board['input_hashes'].items():assert sha(R/path)==digest,('stale CAD report',path)
 owned=['contracts/components.json','contracts/electrical_interfaces.json','config/project_baseline.json']
 before=H/'revisions/before_layout_P3';before.mkdir(exist_ok=True)
 for pp in owned:
  dst=before/Path(pp).name
  if not dst.exists():shutil.copy2(R/pp,dst)
 mechanical_hash=sha(R/'contracts/mechanical_interfaces.json');geometry_hash=sha(R/'config/geometry.json')
 cat=read(R/owned[0]);e=read(R/owned[1]);base=read(R/owned[2]);oldrev=cat['revision']
 cat['revision']=REV;cat['status']='PROTOTYPE_UNVALIDATED';cat['physical_tests']='NOT_TESTED';cat['manufacturing_release']=False
 for c in cat['components']:
  if c['id']=='carrier_pcb':
   c.update(full_model='MORI_motion_P3 + MORI_imu_P3 + MORI_power_P3',board_revision='P3',specification='Three routed two-layer prototypes,1.6mm; motion/IMU35um and power70um nominal copper. Not released for fabrication.',interface='Native Edge.Cuts/holes/connectors in hardware/v1_2/handoff/mechanical_P3.json',dimensions_mm={'motion_xy':[70,35],'imu_xy':[20,16],'power_xy':[80,55],'board_thickness':1.6,'power_thickness':1.6,'full_installed_height':None},selection_status='ROUTED_PROTOTYPE_NOT_RELEASED',missing=['装配/线缆/插头净空复核','制造规则例外与钢网','新PCB打样/装配报价','实物电气和温升验证'],notes='P3 incorporates S3 dual TPS54302 circuits. Power expanded to80x55 by explicit user authorization; bare board dimensions do not qualify a populated mechanical fit. P2/S3 retained.')
  elif c['id']=='body_imu':
   c['full_model']='TDK ICM-42688-P / MORI_imu_P3 daughterboard';c['board_revision']='P3'
  elif c['id']=='logic_power':
   c['board_revision']='P3 routed prototype following S3 schematic';c['selection_status']='SELECTED_ROUTED_PROTOTYPE_NOT_BENCH_VALIDATED';c['missing']=[x for x in c['missing'] if x!='PCB布局与热设计'];c['missing'].append('实际铜厚/纹波/瞬态/温升台架验证')
  elif c.get('board_revision')=='S3 schematic; PCB pending':c['board_revision']='P3 routed prototype; assembly/bench pending'
  if c['full_model']=='SRP7050TA-100M':
   c['interface']='MORI_Custom:Bourns_SRP7050TA_8p4_span_2p5_gap';c['dimensions_mm']={'vendor_body_xyz_max':[7,6.9,5],'pcb_land_outer_span':8.4,'pcb_land_gap':2.5,'pad_xy':[2.95,3.5],'pad_centres_x':[-2.725,2.725],'installed_height_including_solder':None};c['data_status']='VENDOR_DOCUMENTED';c['notes']=c.get('notes','')+'; P3 corrects the previously mistaken land width using Bourns SRP7050TA drawing. These are vendor dimensions, not measurements.'
 cat['engineering_revision_note']='P3: all three boards re-laid out; power80x55 incorporates both S3 TPS54302 converters. Circuit membership/GPIO unchanged. Native ERC/DRC/parity PASS only; source-rule exceptions, mechanical assembly and bench gates remain explicit. '+str(O.relative_to(R)/'README.md')
 e['revision']=REV;e['status']='PROTOTYPE_ROUTED_UNVALIDATED';e['hardware_schematic_revision']=REV;e['gpio_change']=False;e['physical_tests']='NOT_TESTED'
 for section in ['pinmap','harness']:
  for row in e[section]:row['revision']=REV
 historic=e.setdefault('historical_pcb_projects',{})
 for name,board in e.get('pcb_projects',{}).items():
  if name.endswith('_P2'):historic[name]=board
 e['pcb_projects']={}
 for kind,size in [('motion',[70,35]),('imu',[20,16]),('power',[80,55])]:
  name='MORI_'+kind+'_P3';e['pcb_projects'][name]=dict(path='hardware/v1_2/kicad/'+name,dimensions_mm=size,board_thickness_mm=1.6,layers=2,copper_nominal_um=70 if kind=='power' else 35,status='PROTOTYPE_ROUTED_NOT_BENCH_VALIDATED',native_checks=report['boards'][name]['counts'],fabrication_release=False)
 e['active_schematics']={kind:'hardware/v1_2/kicad/MORI_'+kind+'_P3/MORI_'+kind+'_P3.kicad_sch' for kind in ['motion','imu','power']}
 e['pcb_revision_relationship']=dict(existing='P3',power_schematic='P3 (same electrical design as S3)',synchronized=True,reason='Explicit user re-layout authorization; native pin/net comparison and schematic-parity checks pass. P3 corrects inductor lands and changes placement/routing only.')
 e['engineering_review']='hardware/v1_2/layout_P3/README.md';e['schematic_validation']='hardware/v1_2/layout_P3/reports/verification.json';e['layout_validation']=e['schematic_validation'];e['mechanical_handoff']='hardware/v1_2/handoff/mechanical_P3.json';e['manufacturing_outputs_allowed']=False;e['procurement_release']=False
 base['hardware_revision']=REV;base['hardware_entry']='hardware/v1_2/README.md';base['manufacturing_release']=False
 sources=read(H/'sources/index.json')
 for s in sources['sources']:
  if s['id']=='HW12-S3-03':s['local_path']='hardware/v1_2/sources/parts/Bourns_SRP7050TA.pdf';s['notes']+='; P3 land pattern read from source: outer span8.4/gap2.5/pads2.95x3.5mm.'
 for pp,j in zip(owned,[cat,e,base]):put(R/pp,j)
 put(H/'sources/index.json',sources)
 assert sha(R/'contracts/mechanical_interfaces.json')==mechanical_hash and sha(R/'config/geometry.json')==geometry_hash
 put(O/'reports/publication.json',dict(revision=REV,previous_revision=oldrev,utc=datetime.now(timezone.utc).isoformat(),owned_files_updated=owned,mechanical_contract_sha256=mechanical_hash,geometry_sha256=geometry_hash,mechanical_contract_modified=False,formal_firmware_modified=False,purchases=0,manufacturing_orders=0))
 from build_reports import main
 main()
if __name__=='__main__':publish()
