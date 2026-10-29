"""Record source-bound endpoint and causal native evidence; no board acceptance."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from shapely import from_wkb
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):
 with p.open('x') as f:json.dump(data,f,indent=2,ensure_ascii=False);f.write('\n')
c=Copper(dev/'native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
assert len(read(b/'R189-R1304-pose-screen.json')['candidates'])==12
access=read(b/'R189-R1304-exact-access/result.json');assert not any(x['signal_access_count']==2 for x in access['poses'])
trials={rev:read(b/(rev+'-audit.json')) for rev in ['R189A','R189B','R189C','R189D']}
assert all(a['baseline_sha256']==c.sha for a in trials.values())
assert all(sum(r['status']=='PASS' for r in trials[rev]['power_width'])==48 for rev in ['R189A','R189B','R189C'])
assert all({r['net'] for r in trials[rev]['power_width'] if r['status']!='PASS'}=={'/07 {slash} CAM_Protection_Start/CAM_BAT_OUT'} for rev in ['R189A','R189B','R189C'])
assert [len(g) for g in trials['R189A']['GND_groups']]==[154,1]
assert [len(g) for g in trials['R189D']['GND_groups']]==[155]
assert sum(r['status']=='PASS' for r in trials['R189D']['power_width'])==50
assert not trials['R189D']['lost_pad_connections'] and not trials['R189D']['retained_trace_reference_loss']
d=read(b/'R189D-drc.json');assert len(d['violations'])==1 and d['violations'][0]['type']=='starved_thermal'
power_net='/07 {slash} CAM_Protection_Start/CAM_BAT_OUT'
branch={}
for name,board in [('source',c),('B',Copper(b/'R189B/MORI_Interface_C3.kicad_pcb'))]:
 branch[name]=[g['pads'] for g in groups(board,power_net)]
assert sorted(map(len,branch['B']))==[2,2]
rdir=b/'R188-supply-reservations';res=read(rdir/'result.json');assert res['source_sha256']==c.sha
ports=[]
for pt in [(59,17.975),(59.6,17.55),(59.6,17.65),(59.65,18.3),(59.65,18.35),(61.1,18.1)]:
 hits=[]
 for row in res['files']:
  payload=(rdir/row['path']).read_bytes();assert hashlib.sha256(payload).hexdigest()==row['sha256']
  distance=from_wkb(payload).distance(Point(pt))
  if distance<.652:hits.append(dict(net=row['net'],layer=row['layer'],distance_mm=distance))
 ports.append(dict(position_mm=list(pt),source_planning_reservations_within_0_652_mm=hits))
write(b/'R189-causal-review.json',dict(source_sha256=c.sha,
 source_power_branch_groups=branch,port_reservation_diagnostics=ports,
 C_omits_RAW_hole_but_still_loses_CAM=True,
 D_restores_wheel_transfer_and_recovers_CAM=True,
 D_sole_remaining_DRC=d['violations'][0],
 conclusion='Within this controlled B/C/D comparison, moving the wheel transfer to (59,17.975) causes the CAM supply split; the OV F-only change independently produces the J401.3 F-ground thermal defect. A separately introduces ground isolation and two reference gaps. No variant is accepted.',
 limitations='Reservation-free sample points are not cleared holes or legal component poses. Full simultaneous routing, refill, original connections and supply/reference/native requirements remain mandatory.',
 source_saved=False,adopted=False,physical='NOT_TESTED',manufacturing_release=False))
images=[]
for folder,layers in [('R189-source-views',LAYERS),('R189D-views',['F.Cu','B.Cu'])]:
 for ly in layers:
  p=b/folder/(ly+'.png');images.append(dict(local_path=p.relative_to(b).as_posix(),sha256=sha(p)))
assert len(images)==8
write(b/'R189-visual-review.json',dict(source_sha256=c.sha,trial_D_sha256=trials['R189D']['board_sha256'],
 images_actually_viewed=images,
 scope='All six source copper layers and D F/B local native projections viewed. A/B/C were rejected by native evidence without a complete visual qualification. These are geometry renders, not GUI screenshots.',
 observations=['R1304 lies between R404 and the fixed J401 terminals. A visibly open B-face patch is not an all-layer via site.',
 'D removes the OV front detour and keeps the B-face layout, but the vertical F route separates part of J401.3 ground fill; the native starved-thermal defect remains.',
 'The source In3 region involved in the failed port is CAM_BAT_OUT, identified by actual net data. Render colour alone does not identify a power rail.'],
 local_decision='FAIL',whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False))
write(b/'R189-decision.json',dict(previous_goal_turn='PROGRESS: R188C received and committed with one reference repair.',
 adopted=False,status_note='No R189 PCB adopted. Twelve R1304 poses have no complete two-terminal access under retained copper. A/B/C lose CAM supply; A isolates a ground pad; D restores source connections and 50 power checks but retains one J401 front thermal failure. Current R188C remains nineteen opens.',
 next_step='Expand the connected placement scope to R402, its WHEEL_BUS/R404 paths, R1304 input and the OV transfer. Before choosing a replacement port, screen complete all-layer supply reservations, J401 four-spoke/actual thermal connections, both wheel-signal tails and the analog path. R402 up-shift is only an unbuilt direction, not a cleared pose or route. Do not repeat A/B/C or accept D on connectivity alone.',
 space='Specific local congestion established; no full-board unroutability proof. Keep the 70x35 outline. The existing R182 70x40 direction question remains unanswered; no expansion adopted.',
 initial_script_corrections=['A source return list was initially reversed; validation rejected it before creating a plan. Corrected source order and original failure logs retained.',
 'B first build omitted the required move rationale; build rejected before saving the edited board. Initial copied source project, script and logs retained, then the explicit reason was added.'],
 remaining_unconnected_items=19,newly_completed_connections=0,goal_complete=False))
assert sha(Path(c.path))==c.sha
print(json.dumps(dict(source_unchanged=True,completed_native_trials=4,adopted=False,images_viewed=8)))
