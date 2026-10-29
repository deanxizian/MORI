"""Preserve R167 grouped-layout trials, manufacturer reading and failed checks."""
import collections,gzip,hashlib,json,math,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';study=dev/'evidence/R167_study';board='MORI_Interface_C3.kicad_pcb'
old='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):
 with p.open('x') as f:json.dump(data,f,indent=2,ensure_ascii=False);f.write('\n')
assert not study.exists() and sha(source/board)==old
status=read(dev/'STATUS.json');assert status['revision']=='C3 R165M' and status['unconnected_items']==21
source_files={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
members={r['member']:r['sha256'] for r in read(dev/'evidence/R165M/adoption.json')['member_checks']};assert len(members)==77
for name,digest in members.items():assert sha(source/name)==digest
trials=[]
for rev,expected in [('R167A',(27,3)),('R167B',(27,3)),('R167C',(21,3)),('R167D',(22,1))]:
 d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'));i=read(b/(rev+'-inspection.json'));p=read(b/(rev+'-plan.json'))
 assert p['board_sha256']==old and (len(d['unconnected_items']),len(d['violations']))==expected
 assert not d['schematic_parity'] and i['source_ground_vias_preserved']==114
 trials.append(dict(revision=rev,board_sha256=sha(b/rev/board),native_completed=True,adopted=False,unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=0,DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),power_width_failures=[dict(net=r['net'],width_mm=r['width_mm'],lost_pairs=len(r['lost_pairs'])) for r in a['power_width'] if r['status']!='PASS'],old_connection_losses=[r['net'] for r in a['lost_pad_connections']],ground_pad_groups=a['GND_groups'],old_reference_losses=a['retained_trace_reference_loss'],new_reference_gaps=sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in a['new_copper_review']),source_ground_vias_preserved=114,new_same_face_nominal_body_hits=len(i['same_face_nominal_body_hits']),opposite_or_internal_body_hits=len(i['opposite_or_internal_body_hits']),planned_new_trace_length_mm=sum(math.dist(x,z) for r in p['routes'] for x,z in zip(r['points_mm'],r['points_mm'][1:])),enabled_ERC='NOT_RERUN_FOR_REJECTED_TRIAL'))
assert read(b/'R167D-audit.json')['GND_groups'][-1]==['U1702.2','U1702.4']
for rev in ['R167C','R167D']:
 assert all(r['result']['status']=='NO_RASTER_CONNECTION' for r in read(b/(rev+'-fault-without-in2')/'searches.json')['results'])
screen=read(b/'R167-joint-pose-screen.json')
assert len(screen['poses'])==78 and sum(bool(r['legal_port_grid_points']) for r in screen['poses'])==24
port_screens={rev:read(b/(rev+'-port-supply-screen.json')) for rev in ['R167A','R167B']}
assert len(port_screens['R167A']['direct_B_ports'])==16 and len(port_screens['R167B']['direct_B_ports'])==38
assert sum(r['result']['status']=='PROPOSAL' for r in port_screens['R167A']['results'])==1
assert all(r['result']['status']=='PROPOSAL' for r in port_screens['R167B']['results'])
vendor=b/'R167-vendor';pdf=b/'R164-vendor/TPS3700_SBVS187G.pdf';assert sha(pdf)=='3bb7daed20b154bf22ded78e23269c6437eb587400b89bce0f543813df94ebf0'
write(vendor/'review.json',dict(source_url='https://www.ti.com/lit/ds/symlink/tps3700.pdf',document='TI TPS3700 SBVS187G, revised February 2019',source_sha256=sha(pdf),printed_pages_actually_viewed=[2,18,19],sections=['8.3','9','10.1','10.2 / Figure 23'],facts_paraphrased=[
 'Section 8.3 recommends 0.1 uF VDD-to-GND decoupling and conditionally adds comparator input capacitors for noisy monitored rails.',
 'Divider bias-current error must be considered if divider current is less than 100 times comparator input current; output pull-up choice must respect the desired low output voltage.',
 'Section 10.1 asks for the 0.1 uF capacitor close to VDD. Figure 23 shows a local bypass connection and input/output resistor arrangement; no numeric 4 mm layout threshold is specified.'
 ],project_screen_boundary='The existing 4 mm pad-distance gate is an ASSUMED project screen. A/B nominal distances of 2.706618/1.755393 mm do not establish actual bypass path impedance or a short supply-return loop.',application_status='Full input accuracy, noise, bypass loop, output loading, thermal and coupling review remains NOT_TESTED. No schematic/value/capacitor changes were made from this reading.'))
study.mkdir();payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel;compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or len(data)>524288
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/rev for rev in ['R167A','R167B','R167C','R167D']]
for top in sorted(b.glob('R167*')):
 files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
 for p in files:
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161_power_aware_search.py','R161R_inspection.py','R162_inspection.py','R166_endpoint_diagnostics.py','R166E-plan.json','R166-power-spine.json']:
 preserve(b/name,Path('raw/helpers')/name)
for name in ['build_trial.py','copper_geometry.py','audit_candidate.py','footprint_side_change.py','zone_expansion.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
preserve(pdf,Path('raw/vendor')/pdf.name)
preserve(b/'R166E'/board,Path('raw/dependencies/R166E')/board)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R167.json'))
(study/'source_R165M.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
assert gzip.decompress((study/'source_R165M.kicad_pcb.gz').read_bytes())==(source/board).read_bytes()
viewed=[b/('R167A-'+ly+'-local.png') for ly in ['F.Cu','B.Cu']]+[b/('R167D-'+ly+'-local.png') for ly in ['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu']]
write(study/'visual_review.json',dict(scope='Eight actual local native-geometry views; rejected studies only. All are top-projection diagnostic renders, not photographs or whole-board qualification.',images_actually_viewed=[dict(path='raw/'+p.relative_to(b).as_posix(),source_sha256=sha(p)) for p in viewed],findings=[
 'A F/B views confirm the distinct faces of U1702 and Q1701 and the unchanged B C1702 bypass capacitor.',
 'D F view shows the U1702.2/U1702.4 ground island bounded by new input/output/VDD leads; exact native connectivity reports the isolated two-pad group.',
 'D In2/In3 views show the new FAULT clearance narrowing the source 3V3 via (55.2,15.05) connection. The 0.40/0.48 mm source pair losses are established by native filled-copper regression, not image measurement.',
 'D B view shows the original ACT_UV_N links restored around the Q1701 body with a 90 degree branch and the FAULT stub ending at its unconnected through via.',
 'D In1/In4 views show local reference holes; the exact audit finds no new or retained reference loss in D. C has a separately recorded tiny retained WHEEL_BUS reference loss and is not accepted.'
 ],new_nominal_same_face_hits=0,opposite_or_internal_full_review='NOT_TESTED',local_status='INCOMPLETE',whole_board_visual='NOT_TESTED',manufacturer_thermal_coupling='NOT_TESTED',physical='NOT_TESTED',adopted=False))
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),remote_main='aa94dddebcc8ca40cc4b63616147f81448ef087f',source_revision='C3 R165M',source_sha256=old,current_source_unchanged=True,adopted_revision=None,candidates=trials,remaining_unconnected_items=21,baseline_unconnected_items=40,remaining_connectivity_fraction=.525,connectivity_fraction_is_not_engineering_progress=True,progress=[
 'Joint U1702/Q1701 screening checks native courtyards, both-face pads, keepouts, old reference copper and source GND vias. It retains 78 U1702 poses, 24 with prospective Q1701 B escape ports; it is not a fully routed placement qualification.',
 'Native A keeps U1702 at 180 degrees and translates it to F (58.25,15.25). B rotates it to 90 degrees at F (57.75,15.25). Q1701 is B (57,14), 270 degrees; C1702 and all source vias stay fixed in both preparations. Each is 27 opens / 3 dangling / 0 parity.',
 'A native-geometry port-plus-supply screen has 16 direct B ports, but only (55.85,15.45) leaves a local referenced VDD proposal. B has 38 direct B ports and all retain a local old-via VDD proposal. These are raster screens with a prospective clearance hole, not native refill acceptance.',
 'Independent searches initially added unnecessary ACT_UV_N vias because orphaned old transfers were not group endpoints. Explicit old-via terminal searches recover short F and B proposals using original ACT via (58.1,17.7) and existing right-hand via (60.525,14.525), without new ACT holes.',
 'C combines exact restored original connections and the A FAULT port. All old pad connections return and all 155 GND pads stay together, but 3V3 width screens fail at 0.20/0.40/0.48 mm, one old WHEEL_BUS reference loss appears, and an acute ACT branch violates native R27. Its FAULT via remains dangling; C is rejected at 21 opens / 3 other.',
 'D uses the 90 degree U1702 pose, 0.25 mm VDD lead, a proper T branch and FAULT port (56.1,14.9). It removes the C branch-angle/reference failures but isolates U1702.2/U1702.4 from the other 153 ground pads. The original 3V3 via (55.2,15.05) still loses 0.40/0.48 mm connections. D is 22 opens / 1 dangling / 0 parity and is rejected.',
 'Short A/B FAULT main proposals still cut the source In2 3V3 corridor. Reserving it in A produces a 92.101176 mm / six-via weighted proposal with nine potential power-cut regions; it was not built or accepted. F/B/In3-only searches from C and D to all three other FAULT groups have no raster connection under unchanged constraints.',
 'Two C/D preflight failures and their corrected builds are retained. All four native trials keep the 114 source GND vias, source protection clamps and zero new nominal mounted-face body hits; that alone does not preserve ground-pad connectivity or qualify the layout.',
 'TPS3700 printed pages 18-19, including Figure 23, were actually inspected. The project 4 mm proximity test is not a vendor layout qualification. Actual bypass supply/return paths and input/output loading remain open.'
 ],next_actions=[
 'Continue from canonical R165M. R167D is a rejected study, not a replacement entry. Reuse its explicit route/placement plan only as a starting comparison and revalidate all source properties.',
 'Jointly compare Q1701/U1702/C1702, the non-ground ACT output transfer and source 3V3 feed. Give U1702 ground pads a short path to existing GND vias before placing an ACT output lead across that return. Preserve all 114 source GND vias.',
 'The source 3V3 transfer at (55.2,15.05) requires its wide connection restored or an explicitly justified non-ground transfer redesign with all old power functionality retained. Do not accept the new FAULT holes by reducing 0.40/0.48 mm checks.',
 'Re-screen each additional group movement against actual pads, both faces, native body/via guards and courtyards. Do not extrapolate the 38 B ports to an unbuilt shifted pose, or count an orphan-hole connection as a completed FAULT trunk.',
 'Continue joint planning of the FAULT trunk and the original (60.725,13.525)-(68.25,12.7) 0.48 mm In2 power corridor. Do not accept the 92 mm multi-power-cut workaround or infer global impossibility from bounded search failures.',
 'Full manufacturer bypass/input layout, all remaining 21 connections, whole-board style, historic reference flags, BOM/pins, mechanical/harness handoff and physical qualification remain open.'
 ],source_ground_vias_preserved=114,unchanged_canonical_non_PCB_members=77,whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary)
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,unchanged_native_members_omitted=omitted,source_non_PCB_members=members,source_board='source_R165M.kicad_pcb.gz',original_local_sources_preserved=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert source_files=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),native_trials=4,all_original_byte_hashes_match=True,canonical_source_unchanged=True,canonical_sha256=old,source_members_unchanged=77,original_local_trials_untouched=True,adopted=False))
status.update(last_followup_study='R167',latest_study_evidence='evidence/R167_study/summary.json',latest_study_adopted=False,latest_study_note='R167 A-D are not adopted. Joint U1702/Q1701 poses open local FAULT ports; C restores old pads but fails power/reference/branch-angle checks, while D isolates two U1702 ground pads and narrows the source 3V3 transfer. Continue jointly with ground/bypass and non-ground transfers; canonical R165M remains 21 opens / 52.5 percent by connection count.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(archived_payloads=len(payloads),native_trials=4,source_unchanged=True,adopted=False,remaining_unconnected_items=21)))
