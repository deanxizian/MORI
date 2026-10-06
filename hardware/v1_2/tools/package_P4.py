"""Read native P4 engineering state and publish a hardware-owned handoff.

Does not overwrite mechanical ownership, order fabrication, or assert bench PASS.
Native errors are retained in the report; export permission remains separate.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,hashlib,csv,re
import pcbnew as k
from audit_body_routes_P3 import rect
H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P4';REV='V1.2-H0.4-P4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
xy=lambda p:[round(k.ToMM(p.x),6),round(k.ToMM(p.y),6)]
boards={};counts={};pins=[];parts=[]
for kind in ['motion','imu','power','rear']:
 name=f'MORI_{kind}_P4';d=H/'kicad'/name;r=O/'reports'/name;p=d/(name+'.kicad_pcb');b=k.LoadBoard(str(p))
 drc=json.loads((r/'drc.json').read_text());erc=json.loads((r/'erc.json').read_text());cmds=json.loads((r/'check_commands.json').read_text())
 stale=sorted({f for cmd in cmds for f,digest in cmd.get('input_sha256',{}).items() if sha(ROOT/f)!=digest})
 co=dict(ERC=sum(len(v['violations']) for v in erc['sheets']),DRC=len(drc['violations']),unconnected=len(drc['unconnected_items']),parity=len(drc['schematic_parity']))
 counts[kind]=dict(**co,status='PASS' if not any(co.values()) and not stale else 'FAIL',stale_inputs=stale,tool=drc['kicad_version'],violations_by_type=dict(Counter(v['type'] for v in drc['violations'])),drc=str((r/'drc.json').relative_to(ROOT)),erc=str((r/'erc.json').relative_to(ROOT)))
 comps=json.loads((d/'connectivity.json').read_text());fc={c['ref']:c for c in comps['components']}
 connectors=[];holes=[];placements=[]
 for f in b.GetFootprints():
  ref=f.GetReference();pos=xy(f.GetPosition());ang=f.GetOrientationDegrees();side='B' if f.IsFlipped() else 'F';fp=str(f.GetFPID().GetLibItemName())
  if ref in fc:fc[ref].update(placed_at=pos+[ang],side=side)
  placements.append(dict(ref=ref,xy_mm=pos,rotation_deg=ang,side=side,footprint=fp,fab_outline_xy_mm=rect(f),outline_status='NATIVE_FOOTPRINT; not independent vendor full-envelope verification'))
  if ref.startswith('H'):
   holes.extend(dict(ref=ref,xy_mm=xy(q.GetPosition()),hole_mm=xy(q.GetDrillSize())) for q in f.Pads());continue
  if not (ref.startswith('J') or ref in ['SW1','USB1']):continue
  pp=[]
  for q in f.Pads():
   if not q.GetNumber() or q.GetNumber()=='MP':continue
   row=dict(revision=REV,board=name,ref=ref,pin=q.GetNumber(),net=q.GetNetname(),x_mm=xy(q.GetPosition())[0],y_mm=xy(q.GetPosition())[1],side=side,source='native KiCad PCB + schematic parity',bench_status='NOT_TESTED')
   pins.append(row);pp.append(row)
  cn=dict(ref=ref,value=f.GetValue(),xy_mm=pos,rotation_deg=ang,side=side,pins=pp,footprint=fp,mass_g=None,mating_clearance='NOT_TESTED; actual plug and wire exit must be reviewed')
  m=re.search(r'PH_B(\d)B',fp)
  if m:
   n=int(m[1]);cn.update(mpn=f'B{n}B-PH-K-S(LF)(SN)',mating=f'PHR-{n}',contact='SPH-002T-P0.5S',bare_height_from_board_face_mm=6,mated_height_from_board_face_mm=8,wire_bend_clearance_mm=None,height_status='VENDOR_DOCUMENTED, excludes lead/bend')
  elif 'PH_S5B' in fp:cn.update(mpn='S5B-PH-K-S(LF)(SN)',mating='PHR-5',contact='SPH-002T-P0.5S',bare_height_from_board_face_mm=4.8,mated_depth_mm=9.6,body_overhang_at_y25_mm=4.25,wire_bend_clearance_mm=None,height_status='VENDOR_DOCUMENTED, orientation from native footprint')
  elif 'XT30' in fp:cn.update(mpn='AMASS XT30UPB-M',mating='Matching AMASS XT30 cable half; exact drawing/plug height still to qualify',rating_note='Do not transfer connector nameplate rating to the PCB circuit')
  elif 'JST_XH' in fp:cn.update(pitch_mm=2.5,rating_note='Preserved existing selection; validate terminal/wire and peripheral mating end')
  connectors.append(cn)
 outline=comps['size'];assert outline=={'motion':[70,35],'imu':[20,16],'power':[80,55],'rear':[24,25]}[kind]
 comps.update(revision=REV,layout_revision='P4',layers=b.GetCopperLayerCount(),pcb_status='PROTOTYPE_ROUTED_NOT_BENCH_VALIDATED');(d/'connectivity.json').write_text(json.dumps(comps,ensure_ascii=False,indent=2)+'\n')
 boards[name]=dict(outline_mm=outline,pcb_thickness_mm=k.ToMM(b.GetDesignSettings().GetBoardThickness()),copper_layers=b.GetCopperLayerCount(),copper_nominal_um=70 if kind=='power' else 35,copper_status='DESIGN_INTENT; fabrication stack-up not quoted or measured',outline_status='DESIGN_GENERATED',holes=holes,connectors=connectors,placements=placements,full_populated_height_mm=None,mass_g=None,mechanical_fit='BLOCKED pending complete mated/lead/solder-height assembly review',pcb_sha256=sha(p),native_project=str((d/(name+'.kicad_pro')).relative_to(ROOT)),bare_STEP=str((H/'mechanical'/(name+'_BARE_BOARD.step')).relative_to(ROOT)),bare_STEP_is_populated_assembly=False)
 for row in csv.DictReader((d/'assembly_bom.csv').open()):parts.append(dict(board=name,**row))
 summary=counts[kind]
 (d/'README.md').write_text(f'# {name}\n\nPROTOTYPE / 实物 NOT_TESTED。尺寸 {outline[0]}×{outline[1]}×1.6 mm，{b.GetCopperLayerCount()} 层。\n\nKiCad {summary["tool"]}：ERC {summary["ERC"]}，DRC {summary["DRC"]}，未连接 {summary["unconnected"]}，原理图一致性 {summary["parity"]}。报告是否对应当前文件：{"否" if stale else "是"}。\n\n原生 `.kicad_pro`、`.kicad_sch`、`.kicad_pcb` 均在本目录。资料请看 `../../layout_P4/README.md` 和 `../../layout_P4/接插件与充电接口说明.md`。这是设计检查结果，不是热、电池、动态平衡、EMC 或生产认证。没有下单；没有制造数据导出。\n')
mech=ROOT/'contracts/mechanical_interfaces.json'
handoff=dict(revision=REV,date='2026-09-23',mechanical_revision_read=json.loads(mech.read_text()).get('revision'),mechanical_sha256=sha(mech),coordinates='Board +X right, +Y toward native drawing bottom, front +Z; robot mounting transform remains mechanical-owned',boards=boards,power_height_allocation_mm=dict(front=16,back=3,status='CONSTRAINT, not verified populated/mated envelope'),rear_changes=dict(old_allocation_mm=[24,14],new_prototype_outline_mm=[24,25],mount_holes_mm=[[3,11,2.2],[21,11,2.2]],seat_keepouts='top X0..6.5 and17.5..24, Y0..14; covered tracks permitted, parts/exposed vias/pins excluded; see per-item audit',USB_mouth_y_mm=-.65,switch_body_center_xy_mm=[12,12.9],switch_tip_y_mm=8.15,USB_bottom_body_height_mm=3.16,switch_top_body_height_mm=3.5,PH4_mated_top_height_mm=8,PH5_body_overhang_y_mm=4.25,required='Mechanical revise port axis, switch reach/linkage, ledges and plug/cable/removal clearance; no fit PASS'),motion_notes='70x35 unchanged. PH connectors now on top, mated8mm plus bend; WeAct native1:1 module and carrier standoff envelope remain to verify. J6 internal service input only, no shell button.',imu_notes='20x16 unchanged. PH8 8mm mated height may affect underside frame mounting. Two-hole mounting retained; manufacturer3-anchor guidance remains an unresolved mechanical deviation.',physical_tests='NOT_TESTED',owned_files_not_modified=['config/geometry.json','contracts/mechanical_interfaces.json','firmware/'])
(H/'handoff/mechanical_P4.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n')
for fn,rr in [('connector_pinmap.csv',pins),('assembly_bom_all_boards.csv',parts)]:
 keys=list(dict.fromkeys(k for r in rr for k in r))
 with (O/fn).open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rr)
baseline=json.loads((O/'P3R1_baseline.json').read_text());baselines=baseline.get('files',baseline)
changed=[]
if isinstance(baselines,dict):
 for pp,digest in baselines.items():
  if isinstance(digest,str) and len(digest)==64:
   full=Path(pp) if Path(pp).is_absolute() else ROOT/pp
   if not full.exists() or sha(full)!=digest:changed.append(pp)
report=dict(revision=REV,run_utc=datetime.now(timezone.utc).isoformat(),native_checks=counts,P3R1_changed_files=changed,physical_tests='NOT_TESTED',manufacturing_release=False,source_rule_conformance='Not all 47 source rules are natively expressible; R14 exact0.5mm setback remains unqualified/nonconforming; see body/source-rule review')
(O/'reports/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(counts,ensure_ascii=False,indent=2))
