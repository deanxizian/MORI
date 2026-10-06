"""Append independent upper routing evidence without adopting C6 geometry."""
from pathlib import Path
import datetime,hashlib,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
reports=[OUT/'upper_departure_review/departure_review.json',OUT/'upper_departure_review/plot_manifest.json',OUT/'upper_flare_review/flare_screen.json',OUT/'cam_rearward_loops/loop_screen.json',OUT/'cam_rearward_loops/refined_pairs.json']
for p in reports:
    d=read(p)
    for name,h in {**d.get('sources',{}),**d.get('inputs',{})}.items():assert sha(ROOT/name)==h,name
refined=read(reports[-1]);assert refined['status']=='PASS'
source=read(OUT/'cam_rearward_loops/loop_screen.json')
assert max(r['maximum_vertex_delta_mm'] for r in source['helper_baseline_replay'])<1e-5
assert all(r['status']=='PASS' for r in refined['results'])
gap=min(r['minimum_gap_bound_mm'] for r in refined['results'])
html=f'''<!-- UPPER_ROUTE_DIAGNOSTIC --><section id="upper-diagnosis"><h2>上部走线：冲突位置与新的余量圈候选</h2>
<p>旧俯仰余量圈位于第3、4根CAM信号线出口上方。R7、45°起始弯的72个方向均未找到通过方案；这是该局部路径族的结果，不代表所有路线都不可行。两种外扩颈部曲线又碰到Pitch_Yoke，未采用。</p>
<figure><img src="upper_departure_review/upper_exit_conflicts.png" alt="实际路径坐标中的上段冲突" style="width:100%"><figcaption>中心线诊断视图；间隙结论来自三维距离计算，不能仅凭投影判断。</figcaption></figure>
<p>独立的新候选把原尾段的平直部分缩短3／5／7mm，并把临时线圈起点同步后移。连接器端点保持。三个候选分别通过600次实体检查、40次自身检查、60组线间检查，并检查了与现有11条颈部曲线的关系；最小保守线间间隙约{gap:.3f}mm。旧数据较疏时的保守界不足记录保留；仅细分同一条折线后重新求界，要求仍为0.3mm，几何未改变。</p>
<p>这三个是余量圈局部候选：上部汇合、完整端部连续性、应力释放及带线装配仍未完成。主模型未修改，C6开口仍待确认。</p>
<p><a href="upper_departure_review/departure_review.json">起始方向检查</a> · <a href="upper_flare_review/flare_screen.json">外扩颈部失败记录</a> · <a href="cam_rearward_loops/loop_screen.json">后移线圈及原始间隙界</a> · <a href="cam_rearward_loops/refined_pairs.json">同一几何的细分复核</a></p></section><!-- /UPPER_ROUTE_DIAGNOSTIC -->'''
p=OUT/'index.html';page=p.read_text()
page=re.sub(r'<!-- UPPER_ROUTE_DIAGNOSTIC -->.*?<!-- /UPPER_ROUTE_DIAGNOSTIC -->','',page,flags=re.S)
assert '</main>' in page;page=page.replace('</main>',html+'</main>');p.write_text(page)
pub=read(OUT/'publication.json')
files=reports+[p,OUT/'entry_commands.json',OUT/'upper_departure_review/upper_exit_conflicts.png',OUT/'cam_rearward_loops/curves.npz']
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in files})
pub.update(upper_direction_diagnosis='PASS',upper_flare_options='BLOCKED',rearward_pitch_loops='PASS',
    upper_transition_to_rearward_loops='NOT_TESTED',full_harness='BLOCKED',
    upper_publisher_sha256=sha(Path(__file__)),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    upper_publication_command=[sys.executable,str(Path(__file__))])
assert pub['C6_approved'] is False and pub['C6_main_applied'] is False
(OUT/'publication.json').write_text(json.dumps(pub,ensure_ascii=False,indent=2)+'\n')
state=read(OUT/'continuation_status.json')
state['utc']=pub['utc'];state['active_processes']=[]
state['upper_current']={'departure_review':'upper_departure_review/departure_review.json','blocked_initial_pins':[3,4],
    'outward_flare':'BLOCKED by Pitch_Yoke for R17/R30 and R18.5/R20',
    'rearward_loops':'cam_rearward_loops/refined_pairs.json','rearward_loop_status':'PASS',
    'cases':['rear3','rear5','rear7'],'minimum_loop_pair_gap_mm':gap,
    'upper_fan_connections':'NOT_TESTED','main_changed':False}
state['next_work']=['Await C6 opening approval; K1 does not approve C6. Do not apply C6 until the human answers the pending request.',
    'Create upper CAM fan paths from current left_tall_balanced starts to rear3 (or rear5/rear7) pitch loops; current electrical pin mapping is1to9,2to8,3to7,4to10. Preserve same logical connector endpoints. Use refined_pairs.json only for its stated loop/local checks; it does not certify new transitions.',
    'If new upper fan and loop combination passes, join to C6 lower nine only with matching geometry/source hashes and full self/native/pair checks. No cut lengths are released.',
    'Complete other endpoints, anchors, strain relief, FFC/FPC and wired assembly. Received hardware evidence is already archived; do not ask the same source questions again.']
(OUT/'continuation_status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print('UPPER_DIAGNOSTICS_PUBLISHED',gap,flush=True)
