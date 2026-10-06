"""Publish a review package from current native P5 files, with explicit limits.

Never writes mechanical-owned files, never exports fabrication data. Run the
recorded native checks and audits before this script. No invented test result.
"""
import json,csv,hashlib,collections,re,copy
from pathlib import Path
from datetime import datetime,timezone
import pcbnew as k
from layout_P5 import paths,xy,rect,box,F,B
H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P5';REV='V1.2-H0.5-P5'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def csvout(p,rows):
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with p.open('w',newline='',encoding='utf-8-sig')as f:
  w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(dict,list))else v for k,v in row.items()}for row in rows)
native={};boards={};pinrows=[];placements=[];exceptions=[];source_diffs=[];assembly=[]
prior=load(H/'handoff/mechanical_P4.json')
for kind in ['motion','imu','power','rear']:
 name,d,p,r=paths(kind);b=k.LoadBoard(str(p));j=load(r/'drc.json');erc=load(r/'erc.json');cmds=load(r/'check_commands.json')
 stale=sorted({f for cmd in cmds for f,h in cmd['input_sha256'].items()if not(ROOT/f).exists()or sha(ROOT/f)!=h})
 co=dict(ERC=sum(len(s['violations'])for s in erc['sheets']),DRC=len(j['violations']),unconnected=len(j['unconnected_items']),parity=len(j['schematic_parity']))
 assert not stale and not any(co.values()),(kind,co,stale)
 native[kind]=dict(**co,status='PASS',tool=j['kicad_version'],stale_inputs=stale,source_sha256=sha(p),report=str((r/'drc.json').relative_to(ROOT)))
 old=H/'kicad'/f'MORI_{kind}_P4'/f'MORI_{kind}_P4.kicad_pcb';oldb=k.LoadBoard(str(old))
 def pads(board):return sorted((f.GetReference(),q.GetNumber(),q.GetNetname())for f in board.GetFootprints()for q in f.Pads())
 assert pads(b)==pads(oldb),(kind,'pin/net mapping changed')
 shared={t.m_Uuid.AsString()for t in b.GetTracks()}&{t.m_Uuid.AsString()for t in oldb.GetTracks()}
 assert not shared,(kind,'old copper UUID reused')
 oldfp={f.GetReference():f for f in oldb.GetFootprints()};moved=[]
 for f in b.GetFootprints():
  oldf=oldfp[f.GetReference()]
  if xy(f.GetPosition())!=xy(oldf.GetPosition())or f.GetOrientationDegrees()!=oldf.GetOrientationDegrees()or f.GetLayer()!=oldf.GetLayer():moved.append(f.GetReference())
 source_diffs.append(dict(board=name,prior_board_sha256=sha(old),old_copper_UUIDs_reused=0,net_pin_map='PASS_UNCHANGED',position_or_rotation_changed_refs=moved,zero_copper_checkpoint=str((r/'zero_old_copper.json').relative_to(ROOT))))
 bod=load(r/'body_review_final.json');assert bod['source_sha256']==sha(p)
 assert not any(t['classification']=='FAIL_FOREIGN_NET'for t in bod['body_crossing_inventory'])
 groups=collections.defaultdict(list)
 for row in bod['body_crossing_inventory']:groups[row['reference']].append(row)
 for ref,rr in groups.items():
  reason=('既有可拆主控模块架高投影；载板的元件和走线位于其投影内，插座高度/底面净空未实测。此项不能算全部元件下方无走线。'if ref=='U100' else
    '实际端子焊盘到本器件外沿的局部引出；只开放逐针出口，双面本体核心及不相关网络仍受禁布区限制。')
  exceptions.append(dict(board=name,reference=ref,nets=sorted({v['net']for v in rr}),reason=reason,classification=rr[0]['classification'],track_records=rr))
 comps=load(d/'connectivity.json');fc={v['ref']:v for v in comps['components']};pp=[];holes=[];cc=[]
 oldcc={c['ref']:c for c in prior['boards'][f'MORI_{kind}_P4']['connectors']}
 for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
  ref=f.GetReference();side='B'if f.IsFlipped()else'F';pos=xy(f.GetPosition());ang=f.GetOrientationDegrees();fp=str(f.GetFPID())
  row=dict(board=name,reference=ref,xy_mm=pos,rotation_deg=ang,side=side,footprint=fp,fab_projection_mm=rect(f),native_body_and_pad_bounds_mm=box(f),vendor_full_height_mm=None,physical_tests='NOT_TESTED')
  placements.append(row);pp.append(row)
  if ref in fc:fc[ref].update(placed_at=[*pos,ang],side=side)
  if ref.startswith('H'):
   holes.extend(dict(reference=ref,xy_mm=xy(q.GetPosition()),drill_mm=xy(q.GetDrillSize()))for q in f.Pads());continue
  if not(ref.startswith('J')or ref in['SW1','USB1']):continue
  pin=[]
  for q in f.Pads():
   if not q.GetNumber()or q.GetNumber()=='MP':continue
   pr=dict(revision=REV,board=name,reference=ref,pin=q.GetNumber(),net=q.GetNetname(),xy_mm=xy(q.GetPosition()),component_side=side,view='Native component-side pad number; mating cable view is mirrored',status='NOT_TESTED')
   pinrows.append(pr);pin.append(pr)
  cn=copy.deepcopy(oldcc.get(ref,{}));cn.update(reference=ref,ref=ref,xy_mm=pos,rotation_deg=ang,side=side,footprint=fp,pins=pin,native_body_and_pad_bounds_mm=box(f),mating_clearance='NOT_TESTED',wire_bend_clearance_mm=None)
  # P4 rear projection is obsolete after its P5 rotation. Do not retain it.
  cn.pop('body_overhang_at_y25_mm',None)
  cc.append(cn)
 comps.update(revision=REV,layout_revision='P5',layers=b.GetCopperLayerCount(),pcb_status='PROTOTYPE_ROUTED_NOT_BENCH_VALIDATED');dump(d/'connectivity.json',comps)
 size=comps['size'];bb=b.GetBoardEdgesBoundingBox();actual=[round(k.ToMM(bb.GetWidth()),3),round(k.ToMM(bb.GetHeight()),3)]
 # Edge.Cuts stroke is part of the native bbox, so the declared centreline
 # outline is recorded separately; mechanical CAD must use Edge.Cuts itself.
 inner_tracks=[t.m_Uuid.AsString()for t in b.GetTracks()if not isinstance(t,k.PCB_VIA)and t.GetLayer()not in[F,B]];assert not inner_tracks
 boards[name]=dict(outline_mm=size,outline_from='Native Edge.Cuts centreline; unchanged authorized outline',native_edge_bbox_mm=actual,pcb_thickness_mm=k.ToMM(b.GetDesignSettings().GetBoardThickness()),copper_layers=b.GetCopperLayerCount(),nominal_copper_um=[70,35,35,70]if kind=='power'else[35]*b.GetCopperLayerCount(),stackup_status='DESIGN_INTENT_NOT_FAB_QUOTED',holes=holes,connectors=cc,placements=pp,full_populated_height_mm=None,mass_g=None,mechanical_fit='BLOCKED',physical_tests='NOT_TESTED',pcb_sha256=sha(p),native_project=str((d/(name+'.kicad_pro')).relative_to(ROOT)),bare_STEP=str((H/'mechanical'/(name+'_BARE_BOARD.step')).relative_to(ROOT)),bare_STEP_is_populated_assembly=False,inner_signal_tracks=0)
 for row in csv.DictReader((d/'assembly_bom.csv').open()):assembly.append(dict(board=name,**row))
 (d/'README.md').write_text(f'# {name}\n\nPROTOTYPE / 实物 NOT_TESTED。{size[0]}×{size[1]}×1.6 mm，{b.GetCopperLayerCount()}层。\n\nKiCad {j["kicad_version"]}：ERC 0、DRC 0、未连接 0、原理图一致性问题 0；报告与当前文件哈希匹配。\n\n这是从零铜线重新摆位和布线的 P5。原理图/PCB/工程原生文件均在此目录。完整说明及局部例外见 `../../layout_P5/README.md` 与 `../../layout_P5/routing_acceptance.md`。没有制造释放、采购或台架验证。\n')
source=Path('/Users/dean/Documents/KiCad/Rules/pcb-rules.json');assert sha(source)==sha(O/'pcb-rules-source.json')
start=load(O/'restart_manifest.json');prior_changed=[v['source_project']for v in start if sha(ROOT/v['source_project']/(Path(v['source_project']).name+'.kicad_pcb'))!=v['source_pcb_sha256']];assert not prior_changed
load_audit=load(O/'reports/MORI_power_P5/load_path_audit.json');assert load_audit['status']=='PASS'and load_audit['pcb_sha256']==boards['MORI_power_P5']['pcb_sha256']
mech=ROOT/'contracts/mechanical_interfaces.json'
handoff=dict(revision=REV,generated_utc=datetime.now(timezone.utc).isoformat(),mechanical_revision_read=load(mech).get('revision'),mechanical_source_sha256=sha(mech),coordinates='Board +X right; +Y toward native drawing bottom; +Z front. Robot mounting transform remains mechanical-owned.',boards=boards,power_height_allocation_mm=dict(front=16,back=3,status='CONSTRAINT_NOT_COMPLETE_MATED_ENVELOPE'),power_change='80x55 remains; now4 layers, nominal70/35/35/70um copper. Signal and load tracks stay on outer layers; inner GND planes only.',rear_change='24x25 board exceeds old24x14 allocation. Connector bodies and mating cables overhang; use native coordinates, not P4 connector positions.',mass_and_height='Unknown full populated and mated dimensions remain null. Bare STEP is NOT a complete assembly fit.',owned_files_not_modified=['config/geometry.json','contracts/mechanical_interfaces.json','mechanical/','firmware/'],physical_tests='NOT_TESTED')
dump(H/'handoff/mechanical_P5.json',handoff);csvout(O/'connector_pinmap.csv',pinrows);csvout(O/'placements.csv',placements);csvout(O/'assembly_bom_all_boards.csv',assembly)
dump(O/'reports/zero_copper_and_pinmap_verification.json',source_diffs)
dump(O/'reports/body_escape_exceptions.json',exceptions)
report=dict(revision=REV,native_checks=native,P4_boards_preserved=not prior_changed,source_rules=dict(path=str(source),sha256=sha(source),enabled_count=sum(v['enabled']for v in load(source)['rules']),total_count=len(load(source)['rules']),complete_equivalence='NOT_TESTED',reference='routing_acceptance.md'),body_foreign_track_candidates=0,body_architecture_exception='MORI_motion_P5 U100 raised module; native detailed inventory is explicit',inner_signal_tracks=0,drawn_load_path_audit='PASS',physical_tests='NOT_TESTED',mechanical_fit='BLOCKED',manufacturing_release=False)
dump(O/'reports/verification.json',report)
print('P5 native checks / unchanged nets / zero inherited copper / load paths PASS')
