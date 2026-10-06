"""Publish current local progress and the still-open upper connection."""
from pathlib import Path
import datetime,hashlib,html,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
pub=read(OUT/'publication.json');assert not pub['C6_approved'] and not pub['C6_main_applied']
assert sha(ROOT/'mechanical/mori_v1_2.blend')==pub['source_blend_sha256']
relative=['rear_power_delayed/neck_screen.json','rear_power_separation/neck_screen.json','rear_power_bump/neck_screen.json',
          'rear_power_bump/review/review.json','cam_compensated_loops/loop_screen.json','cam_compensated_loops/refined_pairs.json',
          'cam_rear_return/loop_screen.json','cam_side_return/tail_screen.json']
reports=[OUT/p for p in relative if (OUT/p).exists()]
for p in reports:
    r=read(p)
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
local=read(OUT/'rear_power_bump/neck_screen.json');review=read(OUT/'rear_power_bump/review/review.json')
assert local['status']==review['status']=='PASS'
refined=read(OUT/'cam_compensated_loops/refined_pairs.json');loops=read(OUT/'cam_compensated_loops/loop_screen.json')
case=next(r for r in local['results'] if r['status']=='PASS')
assets=[];pictures=''
for row in review['images']:
    p=OUT/'rear_power_bump/review'/row['file'];assert sha(p)==row['sha256'];assets.append(p)
    pictures+=f'<figure><img src="{p.relative_to(OUT).as_posix()}" style="width:100%" alt="当前十一线颈部候选，绿色为调整后的CAM供电线"><figcaption>绿色仅标识本次调整的供电路径；所有曲线仍是独立规划候选。</figcaption></figure>'
blend=OUT/'rear_power_bump/review/MORI_M1_49_rear_neck_local.blend';assert sha(blend)==review['blend_sha256'];assets.append(blend)
obstacles=[]
for p in reports:
    if p.parent.name not in ['cam_rear_return','cam_side_return']:continue
    rr=read(p);names=sorted({h['object'] for c in rr['results'] for h in c.get('hits',[])})
    obstacles.append(dict(study=p.parent.name,status=rr['status'],obstacles=names))
upper='补偿上段长度后的回环没有碰到结构件，线圈之间的细化检查也通过；但与颈部导线仍有交叉。'
assert not loops['hits'] and all(p['status']=='PASS' for p in refined['pairs'])
detail=''.join(f'<li><a href="{p.relative_to(OUT).as_posix()}">{html.escape(p.parent.name)}：{read(p)["status"]}</a></li>' for p in reports)
section=f'''<!-- REAR_NECK_PROGRESS --><section id="rear-local"><h2>最新：颈部11线局部通过，上方接续仍在处理</h2>
<p>保留其他10条路径，仅调整CAM供电线离开颈部的弯曲位置。新增156组结构间隙检查、130组线间检查通过；其余585组线间证据按相同曲线复用。供电线与其他线的最小保守净距为{review['pair_gap_lower_bound_mm']:.3f}mm，所需预留为0.3mm。它在零位与托架的最小采样净距约{review['zero_pose_power_yoke_minimum_sampled_gap_mm']:.3f}mm。</p>
<p>这只通过了颈部局部路径。9根下部工作导线加2根扬声器路径预留，不等于11根完整端到端线束；线材、端头、固定与应力释放、整束运动及带线装配尚未闭环。C6入口开口仍待确认，主模型、STL和动画未加入这些候选。</p>
{pictures}<p><a href="{blend.relative_to(OUT).as_posix()}">可编辑局部候选</a> · <a href="rear_power_bump/review/review.json">本次局部交付记录</a></p>
<h3>上段还剩什么</h3><p>{upper}当前有限姿态记录有{len(refined['lower_conflicts'])}组未满足净距的线对检查，集中在CAM插头引线弯出段与新的颈部路线接续处。这个数量是姿态检查条目数，不是独立缺陷数。</p>
<p>已比较向后与向侧面绕回的候选。其状态保留在下列记录中；失败路线没有用于主模型，也没有通过削薄支架或放宽净距来放行。</p><ul>{detail}</ul><p><a href="upper_connection_commands.json">实际执行命令与结果</a> · <a href="REAR_NECK_PROGRESS.md">接续说明</a></p></section><!-- /REAR_NECK_PROGRESS -->'''
page=OUT/'index.html';s=page.read_text();s=re.sub(r'<!-- REAR_NECK_PROGRESS -->.*?<!-- /REAR_NECK_PROGRESS -->','',s,flags=re.S)
s=s.replace('<h3>最新：后侧出口的剩余冲突</h3>','<h3>历史：后侧出口的剩余冲突（见下方最新修正）</h3>')
s=s.replace('</main>',section+'</main>');page.write_text(s)
note=OUT/'REAR_NECK_PROGRESS.md'
note.write_text('''# M1.49 颈部与CAM上段接续\n\n已采用的K1和主模型保持不动。C6仍待用户确认。\n\n- rear_power_bump/neck_screen.json：局部11线PASS。供电线5的下段至Z177不变，其他10条路径数组完全相同。\n- CAM回环的长度补偿算法已建立；结构间隙和线圈互检通过，但与当前颈部路线仍有交叉，完整线束BLOCKED。\n- 新的后向／侧向返回路径只存为独立候选；看各自报告的实际状态。\n- 接下来处理CAM端部接续，再联合身体前段、其他上端点、固定与应力释放、FFC/FPC以及带线装配。\n\n半径和长度均为名义几何规划，不能代替动态弯曲寿命或实物线材、压接和端头验证。没有供应商联系、采购或制造放行。\n''')
readme=OUT/'README.md';readme.write_text('# M1.49 线束候选\n\nC5、K1已采用。C6入口待确认。\n\n最新进展：颈部11线局部检查通过；CAM上部回环仍与颈部路径交叉，完整线束BLOCKED。见 index.html#rear-local 和 REAR_NECK_PROGRESS.md。\n\n候选曲线没有加入主模型、STL或装配动画。\n')
state=read(OUT/'continuation_status.json');now=datetime.datetime.now(datetime.timezone.utc).isoformat();state['utc']=now;state['active_processes']=[]
state['upper_current'].update(all_eleven_local_paths='PASS',remaining_conflict_slot=None,remaining_conflict_function=None,
    latest_rear_diagnostic='rear_power_bump/review/review.json',rear_local_curves='rear_power_bump/curves.npz',rear_constant_length='BLOCKED',
    compensated_CAM_loops='cam_compensated_loops/refined_pairs.json',compensated_CAM_loop_status=refined['status'],CAM_tail_neck_conflict_cases=len(refined['lower_conflicts']),tail_alternatives=obstacles,
    main_changed=False)
state['next_work']=['C6 approval remains pending; do not apply the opening to main from the separate K1 approval.',
    'Use rear_power_bump/curves.npz as the current local eleven-path candidate. Other ten paths are byte-identical; slot5 lower samples through Z177 are unchanged. Preserve all sources and printed hardware.',
    'Resolve actual CAM tail versus neck crossings recorded by cam_compensated_loops/refined_pairs.json. Current loops are clear of native solids, but the full assembly is BLOCKED. Rear/side return attempts are separate recorded candidates.',
    'Then connect the fixed-yaw fans, compensate full joined lengths, recheck C6 body-prefix coexistence, complete the other upper endpoints and anchoring/strain relief, FFC/FPC and wired assembly.']
write(OUT/'continuation_status.json',state)
files=reports+assets+[page,note,readme,OUT/'upper_connection_commands.json',OUT/'execution_failures.json']
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in files})
pub.update(utc=now,rear_local_eleven='PASS',CAM_tail_neck_join=refined['status'],full_harness='BLOCKED',
           rear_progress_publisher_sha256=sha(Path(__file__)),rear_progress_publish_command=[sys.executable,*sys.argv])
write(OUT/'publication.json',pub);print('REAR_PROGRESS_PUBLISHED',review['pair_gap_lower_bound_mm'],len(refined['lower_conflicts']),obstacles,flush=True)
