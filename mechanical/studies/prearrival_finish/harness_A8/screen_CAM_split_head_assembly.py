"""Check the explicit body/bridge then yaw then pitch assembly split.

Current source hardware is unchanged. The latest unadopted neck candidate is
used only in memory. Every robot object is assigned; omitted stages remain
explicitly deferred. This finite diagnostic does not certify wiring or fits.
"""
from pathlib import Path
SPLIT_SCRIPT=Path(__file__).resolve();SPLIT_A8=SPLIT_SCRIPT.parent
SPLIT_HELPER=SPLIT_A8/'screen_CAM_complete_head_insertion.py'
__file__=str(SPLIT_HELPER)
exec(compile(SPLIT_HELPER.read_text().split('\nheadsets=',1)[0],str(SPLIT_HELPER),'exec'),globals())
__file__=str(SPLIT_SCRIPT)
SPLIT_OUT=OUT/'split_assembly';SPLIT_OUT.mkdir(exist_ok=True)
# Hidden validation proxies can retain unevaluated parent transforms. Bring
# the validation collections into the dependency graph before reading world
# vertices, just as the established harness bootstrap does. Never move CAD
# to correct a stale proxy. Preserve the comparison as part of this study.
stale_solids=ss
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[c].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={n:Solid(o) for n,o in source_objects.items()}
proxy_refresh=[]
for n,s in ss.items():
    old=stale_solids[n]
    if old.v.shape!=s.v.shape or not np.array_equal(old.v,s.v):
        proxy_refresh.append(dict(part=n,validation_proxy=s.o.get('validation_proxy'),
            previous_bounds_mm=list(old.m.bounding_box()),refreshed_bounds_mm=list(s.m.bounding_box()),
            previous_front_shell_overlap_mm3=max(0.,float((stale_solids['Head_Front'].m^old.m).volume())),
            refreshed_front_shell_overlap_mm3=max(0.,float((ss['Head_Front'].m^s.m).volume()))))
solids={n:s.m for n,s in ss.items()}
for n,p in replacements.items():
    a=np.load(p);solids[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
neck_dir=OUT/'larger_neck_candidate'
neck_report=json.loads((neck_dir/'publication.json').read_text())
assert neck_report['status']=='PASS' and neck_report['source_main_sha256']==source_hash
for n in ('Yaw_Base','Pitch_Yoke'):
    p=neck_dir/'cleaned'/(n+'.npz');a=np.load(p)
    solids[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
    replacements[n]=p

bridge={'Yaw_Base','Yaw_Bearing','Yaw_Base_-1_Nut','Yaw_Base_1_Nut','Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1'}
pitch={n for n,s in ss.items() if s.group=='pitch'}
keeper_screws={'Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1'}
reaction_retainer={'Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut'}
yaw=moving-bridge-pitch-keeper_screws-reaction_retainer
reaction={'Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut'}
assert reaction<=yaw
assert set.union(fixture,upper,bridge,pitch,yaw,keeper_screws,reaction_retainer,deferred)==set(solids)
groups={'body_core':fixture,'upper_shell':upper,'fixed_bridge':bridge,'yaw_unit':yaw,
        'pitch_unit':pitch,'keeper_screws_later':keeper_screws,'reaction_retainer_later':reaction_retainer,
        'other_deferred':deferred}
assert sum(len(x) for x in groups.values())==209
rows=[];started=time.time()

def check(label,poses,moved_groups,fixed_ids,notes):
    failures=[];checked=0;fixed=placed(fixed_ids,I)
    for i,ts in enumerate(poses):
        sets=[placed(ids,t) for ids,t in zip(moved_groups,ts)]
        hits=[]
        for a in sets:hits+=pairs(a,fixed)
        for a,b in itertools.combinations(sets,2):hits+=pairs(a,b)
        checked+=1
        if hits:
            failures=[dict(index=i,transforms=[x.tolist() for x in ts],hits=hits)];break
    r=dict(stage=label,status='BLOCKED' if failures else 'PASS',checked_positions=checked,
        planned_positions=len(poses),moving=[sorted(x) for x in moved_groups],fixed=sorted(fixed_ids),
        deferred=sorted(set(solids)-set.union(fixed_ids,*moved_groups)),notes=notes,failures=failures)
    rows.append(r);print('SPLIT_ASSEMBLY',label,r['status'],checked,failures[:1],round(time.time()-started,2),flush=True)

import itertools
# These are reverse withdrawal trajectories; time reversal defines insertion.
# All six fixed bridge members move, including both keeper inserts.
for stage,poses in [
 ('bridge_lift_shell_held',[(shellpose(15,0,14),trans(z=float(z))) for z in np.arange(0,18.01,.5)]),
 ('body_bridge_back',[(shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in np.linspace(0,-14,57)]),
 ('body_bridge_bench',[(shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in np.arange(14,140.01,.5)]),
 ('body_shell_settle',[(shellpose(15*float(u),0,14*float(u)),I) for u in np.linspace(0,1,61)]),
]:check(stage,poses,[upper,bridge],fixture,'Bridge screws fitted while shell held; yaw and pitch assemblies not yet present.')

check('full_yaw_from_above',[(trans(z=float(z)),) for z in np.arange(0,90.01,.5)],
      [yaw],fixture|upper|bridge,'Whole named yaw unit, reaction clamp and keeper included; pitch parts absent.')
check('yaw_after_reaction_first',[(trans(z=float(z)),) for z in np.arange(0,90.01,.5)],
      [yaw-reaction],fixture|upper|bridge|reaction,
      'Alternative only: reaction link fixed to bridge before shell seating; its own insertion is not proven here.')

# The optical/camera assembly and outer head shells are normally separate from
# the cradle at this point. Check this complete pitch unit as a diagnostic;
# a failed result requires explicit further subassembly, never hidden omission.
check('full_pitch_from_above',[(trans(z=float(z)),) for z in np.arange(0,90.01,.5)],
      [pitch],fixture|upper|bridge|yaw|keeper_screws|reaction_retainer,
      'All pitch-group pieces included, including shafts/fasteners. Failure diagnoses required staging; not an approved insertion path.')

report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite full-member rigid diagnostics for staged body/bridge/yaw/pitch installation; no wire or connector path approval',
    script_sha256=sha(SPLIT_SCRIPT),helper_sha256=sha(SPLIT_HELPER),source_main_sha256=source_hash,
    source_neck_publication_sha256=sha(neck_dir/'publication.json'),protected_sources=protected,
    substituted_unadopted_prints={n:dict(path=str(p.relative_to(PROJECT)),sha256=sha(p)) for n,p in replacements.items()},
    source_objects=len(solids),membership={k:sorted(v) for k,v in groups.items()},rows=rows,
    validation_proxy_pose_refresh=proxy_refresh,
    source_proxy_note='Validation collections evaluated before reading world vertices; main file and all CAD remain unchanged.',
    rigid_intersection_threshold_mm3=1e-5,continuous_motion='NOT_TESTED',mating_plugs='NOT_TESTED',
    full_wire_material='NOT_TESTED',hand_and_tool_space='NOT_TESTED',joint_fits='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(SPLIT_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SPLIT_ASSEMBLY_DONE',report['status'],round(time.time()-started,2),flush=True)
