"""Service checks on the isolated candidate; never adopt or save the main.

Historical accepted-shape identity is deliberately kept separate from service
checks: an unapplied geometry proposal cannot match the earlier approved shape.
"""
from pathlib import Path
import sys, json, hashlib

HERE = Path(__file__).resolve().parent
MAIN_MECHANICAL = HERE.parents[1]
CANDIDATE = HERE / 'thin_candidate_workspace/mechanical'
sys.path.insert(0, str(CANDIDATE / 'scripts'))
from common import *
from validate import Solid, intersect_volume
from validate_wheel_interfaces import validate_wheel_interfaces
from validate_head_retention import run as retention_run, hit
from interface_completion import axial

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
main_before = sha(MAIN_MECHANICAL / 'mori_v1_2.blend')
candidate_before = sha(CANDIDATE / 'mori_v1_2.blend')
assert Path(bpy.data.filepath).resolve() == (CANDIDATE / 'mori_v1_2.blend').resolve()
assert ROOT == CANDIDATE
provenance = json.loads((HERE / 'thin_candidate_check.json').read_text())
assert main_before == provenance['source_blend_sha256']
assert candidate_before == provenance['candidate_blend_sha256']
assert provenance['status'] == 'PASS' and not provenance['applied_to_main']
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled(); bpy.context.view_layer.update()
ss = {o.name.removeprefix(PREFIX): Solid(o) for o in parts()
      if o.type == 'MESH' and o.get('group') not in ['dock', 'coupon']}
checks = []


def emit(id, status, summary, measurement=None, method=None):
    checks.append(dict(id=id, status=status, summary=summary,
                       measurement=measurement, method=method))
    print('CANDIDATE_SERVICE', id, status, flush=True)


validate_wheel_interfaces(ss, Solid, intersect_volume, emit)
head = retention_run()
# Preserve the complete raw result, including its expected historical scope
# mismatch, rather than changing the accepted-shape verifier for a proposal.
head_functions = {
    'head_static': not head['static_hits'],
    'head_motion': not head['motion']['hits'],
    'axial_capture': head['capture']['status'] == 'PASS',
    'keeper_side_entry': not head['bench_plate_side_entry']['hits'],
    'yoke_keeper_vertical_entry': not head['paired_vertical_insertion']['hits'],
    'keeper_tools': not head['tool_hits'],
    'keeper_screw_entry': not head['screw_entry_hits'],
    'keeper_pilots': head['pilot_status'] == 'PASS',
    'head_connected': all(v == 1 for v in head['connected_components'].values()),
    'yaw_stops': all(v is not None and 64 <= abs(v) <= 64.5
                     for v in head['mechanical_stop_onsets_deg']),
    'bearing_abutment': min(head['nominal_abutment_contact_areas'].values()) > 30,
}
emit('head_retention_functional_checks', 'PASS' if all(head_functions.values()) else 'FAIL',
     'Candidate service, capture and tool checks; historical shape identity is not waived', head_functions)

# The modified reaction link travels with the detached yaw subassembly after
# its lower cross-retainer is removed. Check the complete modified link against
# the installed body fixture throughout the same 90 mm extraction path.
geom = {n:s.m for n,s in ss.items()}
q = P['head_axial_retention']
yaw_set = {n for n,s in ss.items() if s.group == 'yaw'} | {
    'Yaw_Anti_Lift_Keeper', 'Yaw_Reaction_Link', 'Yaw_Reaction_Clamp_Screw',
    'Yaw_Reaction_Clamp_Nut', 'Yaw_Horn', 'Yaw_Output', 'Yaw_Lock_Screw'}
fixture = set(geom) - yaw_set - {n for n,s in ss.items() if s.group == 'pitch'} - set(q['new_ids']) - {
    'Yaw_Reaction_Retainer_Screw', 'Yaw_Reaction_Retainer_Nut'}
link_path = []
for dz in np.arange(0, 90.01, .5):
    moving = geom['Yaw_Reaction_Link'].translate((0,0,float(dz)))
    for other in fixture:
        v = hit(moving, geom[other])
        if v: link_path.append(dict(z_mm=float(dz), fixed=other, overlap_mm3=v))
emit('reaction_link_extraction', 'PASS' if not link_path else 'FAIL',
     'Modified link rises 90 mm with yaw subassembly, lower retaining screw removed',
     dict(samples=181, fixed_parts=sorted(fixture), hits=link_path),
     '0.5 mm finite translation samples; cables disconnected; no hand-grip qualification')

# Clamp hardware is installed on the yaw subassembly before the pitch cradle,
# optics and shell. The current screw is a trial envelope, so the shank check
# below is explicitly an allocation, not a matched driver/recess qualification.
bench = yaw_set - {'Yaw_Anti_Lift_Keeper'}
entries = []
for n, direction in [('Yaw_Reaction_Clamp_Screw', 1), ('Yaw_Reaction_Clamp_Nut', -1)]:
    hits = []
    for d in np.arange(0, 30.01, .5):
        moving = geom[n].translate((0, direction*float(d), 0))
        for other in bench - {n}:
            v = hit(moving, geom[other])
            if v: hits.append(dict(travel_mm=float(d), fixed=other, overlap_mm3=v))
    entries.append(dict(id=n, direction_y=direction, samples=61, hits=hits))
emit('reaction_clamp_fastener_entry', 'PASS' if not any(x['hits'] for x in entries) else 'FAIL',
     'Unchanged trial screw/nut installation through the thicker collar', entries)

bolt = ss['Yaw_Reaction_Clamp_Screw']
center = (bolt.lo + bolt.hi)/2
start = np.array([center[0], bolt.hi[1]+.05, center[2]])
tool = axial(1.25,30,start+np.array([0,15,0]),np.array([0,1,0]))
tool_hits = []
for other in bench - {'Yaw_Reaction_Clamp_Screw'}:
    v = hit(tool, geom[other])
    if v: tool_hits.append(dict(fixed=other, overlap_mm3=v))
emit('reaction_clamp_driver_allocation', 'PASS' if not tool_hits else 'FAIL',
     'Assumed diameter2.5 x30 mm straight shank allocation on detached yaw assembly',
     dict(start_mm=start.tolist(), hits=tool_hits),
     'Final horn/fastener and driver selection remain BLOCKED; no assertion of matched bit')

# Do not cut a tool groove merely because late installation is blocked. Test
# the existing lower-complexity alternative: hardware enters the separate
# reaction link before the link is placed inside the yoke and before yaw servo
# installation. This is an explicit alternate stage, not a silent obstacle
# deletion. Final horn preload/order still needs the selected horn information.
early_bench = {'Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn'}
early_entries = []
for n, direction in [('Yaw_Reaction_Clamp_Screw',1),('Yaw_Reaction_Clamp_Nut',-1)]:
    hits = []
    for distance in np.arange(0,30.01,.5):
        for other in early_bench-{n}:
            v=hit(geom[n].translate((0,direction*float(distance),0)),geom[other])
            if v:hits.append(dict(travel_mm=float(distance),fixed=other,overlap_mm3=v))
    early_entries.append(dict(id=n,samples=61,hits=hits))
early_tool = [{'fixed':n,'overlap_mm3':v} for n in early_bench-{'Yaw_Reaction_Clamp_Screw'} if (v:=hit(tool,geom[n]))]
link_with_fasteners = {'Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn'}
preload_fixture = {n for n,s in ss.items() if s.group=='yaw'} - {'Yaw_Servo','Yaw_Output'}
preload_hits=[]
for dz in np.arange(0,90.01,.5):
    for n in link_with_fasteners:
        for other in preload_fixture-link_with_fasteners:
            v=hit(geom[n].translate((0,0,float(dz))),geom[other])
            if v:preload_hits.append(dict(travel_mm=float(dz),moving=n,fixed=other,overlap_mm3=v))
emit('reaction_clamp_early_stage_candidate',
     'PASS' if not any(x['hits'] for x in early_entries) and not early_tool and not preload_hits else 'FAIL',
     'Preassemble clamp hardware on separate link, then lower it into detached yaw yoke before yaw servo',
     dict(fastener_entries=early_entries,driver_allocation_hits=early_tool,link_insertion_hits=preload_hits,
          insertion_samples=181,fixture=sorted(preload_fixture),
          final_horn_preload_and_assembly_sequence='BLOCKED pending matching horn/locking details'))

source_unchanged = main_before == sha(MAIN_MECHANICAL/'mori_v1_2.blend') and candidate_before == sha(CANDIDATE/'mori_v1_2.blend')
emit('source_files_unchanged','PASS' if source_unchanged else 'FAIL','Read-only scene inspection; no .blend saved')
result = dict(status='FAIL' if any(c['status']=='FAIL' for c in checks) else 'PASS',
              applied_to_main=False, source_blend_sha256=main_before,
              candidate_blend_sha256=candidate_before, blender_version=bpy.app.version_string,
              checks=checks, historical_retention_scope=head['scope_status'],
              historical_scope_note='Expected mismatch: candidate modifies Pitch_Yoke away from M1.44 accepted geometry; no historical validator or approval was changed.',
              candidate_head_retention_report='thin_candidate_workspace/mechanical/reports/head_axial_retention_validation.json',
              limits=['Finite geometry samples only, no continuous sweep proof',
                      'Complete wiring, hand access, print strength and final horn-dependent interfaces remain unqualified',
                      'This report does not apply the candidate or release main STL files'])
(HERE/'thin_candidate_service.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('THIN_SERVICE_FINAL',result['status'],flush=True)
if result['status']!='PASS':raise SystemExit(1)
