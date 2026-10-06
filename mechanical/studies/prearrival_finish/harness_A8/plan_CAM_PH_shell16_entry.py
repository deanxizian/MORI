"""Check a late body-connector entry with the upper shell held open.

Read-only alternative sequence. The bridge stays seated; upper-shell members
and their rear plugs move as a group. Four attached CAM wires are excluded
from this first rigid-housing screen, so no whole-assembly claim is possible.
"""
from pathlib import Path
OPENPH_SCRIPT=Path(__file__).resolve()
OPENPH_HELPER=OPENPH_SCRIPT.parent/'plan_CAM_PH_rotated_entry_fast.py'
marker="\nexec(compile('started=time.time();expanded=0;'+run"
__file__=str(OPENPH_HELPER)
exec(compile(OPENPH_HELPER.read_text().split(marker,1)[0],str(OPENPH_HELPER),'exec'),globals())
__file__=str(OPENPH_SCRIPT)
ROT_SCRIPT=OPENPH_SCRIPT
ROT_OUT=STOCK_OUT/'PH_shell16_entry';ROT_OUT.mkdir(exist_ok=True)
JOINT_DATA=STOCK_OUT/'install_order/CAM_H02_joint_lift/wire_solids.json'
JOINT_REPORT=STOCK_OUT/'install_order/CAM_H02_joint_lift/screen.json'
joint_data=json.loads(JOINT_DATA.read_text())
assert set(joint_data)=={'H02_1','H02_2'}
for name,row in joint_data.items():
    v=np.asarray(row['vertices_mm']);f=np.asarray(row['triangles'],dtype=np.uint64)
    m=manifold.Manifold(manifold.Mesh64(v,f))
    assert m.volume()>0
    targets['fixed_wire_'+name]=m
shell_t=shellpose(16.,0.,14.)
for name in targets:
    if target_group[name]=='upper':targets[name]=targets[name].transform(shell_t[:3,:4])
target_data={}
for name,m in targets.items():
    a=m.to_mesh64();v=np.asarray(a.vert_properties[:,:3]);f=np.asarray(a.tri_verts)
    target_data[name]=(m,v.min(0),v.max(0),BVHTree.FromPolygons(v,f.tolist(),all_triangles=True))
target_vertices={n:np.asarray(m.to_mesh64().vert_properties[:,:3]) for n,(m,*_) in target_data.items()}
initial=collision(manifold.Manifold.batch_hull([shapes[0],shapes[0].translate([0,0,8])]),True)
# A connector held outside the right side of the body can be connected after
# seating the bridge. This does not require the PH housing to pass the neck.
# Its four free wire ends must still be threaded/formed separately.
run=run.replace('goal=np.array([-18,44,60])','goal=np.array([84,0,16])')
run=run.replace('-48<=q[0]<=48 and -24<=q[1]<=64 and 8<=q[2]<=80','-48<=q[0]<=88 and -48<=q[1]<=64 and 8<=q[2]<=80')
run=run.replace('time.time()-started<150','time.time()-started<180')
run=run.replace('time_budget_s=150','time_budget_s=180')
run=run.replace('expanded%250==0','expanded%100==0')
exec(compile('started=time.time();expanded=0;'+run,str(FAST_BASE),'exec'),globals())
report.update(optimizer_base_sha256=sha(FAST_BASE),search_helper_sha256=sha(OPENPH_HELPER),
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [JOINT_DATA,JOINT_REPORT]},
    scope='Rigid PH allocation from native body header to exterior side workspace while shell held at 16 degrees / +14 mm and bridge seated',
    shell_transform=shell_t.tolist(),transformed_upper_members=sorted(n for n in targets if target_group[n]=='upper'),
    fixed_wire_replacements=sorted(joint_data),bridge_pose='native/seated',
    collision_method='Unchanged convex containment and BVH screening with sampled exact Boolean checks',
    exact_boolean_audits=exact_audits,convex_queries=convex_queries,
    proposal_only=True,attached_four_wire_entry='NOT_TESTED',neck_feed_and_later_head_install='NOT_TESTED',
    hand_access='NOT_TESTED',main_applied=False,whole_harness='BLOCKED')
(ROT_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/n)==h for n,h in protected.items())
print('OPEN_SHELL_PH_DONE',report['status'],report['expanded_nodes'],len(exact_audits),flush=True)
