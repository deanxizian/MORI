"""Publish bounded upper-fan evidence; never adopt an unapproved opening."""
from pathlib import Path
import argparse,datetime,hashlib,html,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
parser=argparse.ArgumentParser();parser.add_argument('--family',default='rear7_multistage');args=parser.parse_args()
assert '/' not in args.family and '..' not in args.family
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,r:p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
base=OUT/'cam_rearward_fans'/args.family
fan=read(base/'fan_screen.json');pack_path=base/'local_join/local_join_screen.json';join_path=base/'c6_join/join_review.json'
pack=read(pack_path) if pack_path.exists() else None;join=read(join_path) if join_path.exists() else None
reports=[OUT/'cam_rearward_fans/rear3/local_join/local_join_screen.json',OUT/'cam_rearward_fans/rear3_aligned/local_join/local_join_screen.json',
    OUT/'cam_rearward_fans/rear3_multistage/fan_screen.json',base/'fan_screen.json']+[p for p in [pack_path,join_path] if p.exists()]
neck_reports=[OUT/n/'neck_screen.json' for n in ['neck_outlet_steering','neck_outlet_offset','rear_outlet_neck','rear_direct_neck','rear_late_neck','rear_separated_neck'] if (OUT/n/'neck_screen.json').exists()]
reports+=neck_reports
for p in reports:
    r=read(p)
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
pub=read(OUT/'publication.json');assert not pub['C6_approved'] and not pub['C6_main_applied']
assert sha(ROOT/'mechanical/mori_v1_2.blend')==pub['source_blend_sha256']
joint_ok=bool(pack and pack['status']=='PASS');c6_ok=bool(join and join['status']=='PASS')
counts={r['pin']:len(r['candidates']) for r in fan['rows']}
summary=('CAM四根上部线与后移余量圈已通过共同检查。' if joint_ok else 'CAM上部共同走向仍未通过。')
summary+=('已与C6九线下段衔接并复核，四根CAM参考路线贯通。' if c6_ok else '尚未与C6九线下段完成共同验证。')
summary+='C6仍待确认，主模型未采用；其余上部端点、固定与应力释放、FFC/FPC及带线装配未完成。'
items=''.join(f'<li>CAM {pin}：{n}条通过本轮单线筛查的候选</li>' for pin,n in counts.items())
proof=(f'<p>四根上部连线共同通过130个yaw／pitch组合的780组互检；未选线材和端部估计仍有原记录的限制。</p>' if joint_ok else '<p>单线候选不等于整束通过。当前组合结果仍为BLOCKED，保留所有失败记录。</p>')
if c6_ok:proof+='<p>C6衔接复核逐段匹配共享颈部样本，并新增4680组上段与身体前段互检。复用的下部715组、上部780组证据均已核对来源和几何哈希；该结论只覆盖四根贯通CAM参考线、五根其余下部线及两个局部喇叭线预留。</p>'
links=' · '.join(f'<a href="{p.relative_to(OUT).as_posix()}">{html.escape(label)}</a>' for p,label in [(base/'fan_screen.json','本轮单线筛查')]+([(pack_path,'上部共同检查')] if pack else [])+([(join_path,'C6衔接检查')] if join else []))
neck_summaries=[]
for p in neck_reports:
    r=read(p)
    obstacles=sorted({h['object'] for row in r['results'] for h in row.get('hits',[])})
    neck_summaries.append(dict(family=p.parent.name,status=r['status'],obstacles=obstacles,full_harness=r['full_harness']))
neck_html='<h3>出口方向复核</h3><ul>'+''.join(f'<li><a href="{p.relative_to(OUT).as_posix()}">{html.escape(p.parent.name)}</a>：{read(p)["status"]}，仅为局部路线检查。</li>' for p in neck_reports)+'</ul><p>直接右移会碰偏航舵机，左移会碰俯仰托架。后侧候选还需同时处理颈内限制、线间距离和长度补偿；局部路线通过也不能代替完整端部和带线装配。</p>' if neck_reports else ''
render=base/'c6_join/render_manifest.json';assets=[];pictures=''
diagnostic_path=OUT/'rear_separated_neck/review/review.json';diagnostic=None;diagnostic_html=''
if diagnostic_path.exists():
    diagnostic=read(diagnostic_path)
    for f,h in {**diagnostic['sources'],**diagnostic['inputs']}.items():assert sha(ROOT/f)==h,f
    assets.append(diagnostic_path)
    diagnostic_html='<h3>最新：后侧出口的剩余冲突</h3><p>此候选中，排除一根CAM供电线后，其余10条局部路线的585组线间检查通过。红色是仍需修正的供电线；青色／橙色区分其他规划导线，全部仍为未选定线材的占位路径。原下部入口保持，主模型没有改动。</p><p>这不是整束通过：红线与托架及相邻CAM线的距离仍不足；后侧路线的长度变化、上部余量圈、端部连接及带线装配还要继续完成。</p>'
    for row in diagnostic['images']:
        p=diagnostic_path.parent/row['file'];assert sha(p)==row['sha256'];assets.append(p)
        diagnostic_html+=f'<figure><img src="{p.relative_to(OUT).as_posix()}" alt="后侧出口中红色供电线仍需避让" style="width:100%"></figure>'
    blend=diagnostic_path.parent/'MORI_M1_49_rear_outlet_diagnosis.blend';assert sha(blend)==diagnostic['blend_sha256'];assets.append(blend)
    diagnostic_html+=f'<p><a href="{diagnostic_path.relative_to(OUT).as_posix()}">实际检查与复现</a> · <a href="{blend.relative_to(OUT).as_posix()}">可编辑诊断模型</a></p>'
if render.exists():
    rr=read(render)
    for f,h in {**rr.get('sources',{}),**rr.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
    for row in rr['images']:
        p=render.parent/row['file'];assert sha(p)==row['sha256'];assets.append(p)
        pictures+=f'<figure><img src="{p.relative_to(OUT).as_posix()}" alt="CAM走向独立候选" style="width:100%"><figcaption>独立路线候选；外壳隐藏便于检查，主模型未采用。</figcaption></figure>'
    blend=render.parent/'MORI_M1_49_C6_CAM_candidate.blend';assert sha(blend)==rr['blend_sha256'];assets+=[render,blend]
    links+=f' · <a href="{blend.relative_to(OUT).as_posix()}">可编辑Blender候选</a>'
section=f'''<!-- UPPER_CONNECTION_REVIEW --><section id="upper-connections"><h2>CAM上部汇合复核</h2>{diagnostic_html}<p>{summary}</p><ul>{items}</ul>{proof}{pictures}
<p>诊断修正：旧程序给线对排序时没有同步交换方向标签，导致部分“哪根线碰哪根圈”的字段反向。旧PASS／BLOCKED结论同时检查两个方向，未受影响。本轮按导线针号与障碍线圈针号直接记录；旧报告保留。</p>
<p>后移3mm的尝试只解决前两根的局部问题；后两根仍有交叉或自身接近。随后检查更靠后的已有线圈候选。没有改变原连接器逻辑针序、硬件姿态、打印件或间隙要求。</p>{neck_html}<p>{links} · <a href="upper_connection_commands.json">实际执行命令</a></p></section><!-- /UPPER_CONNECTION_REVIEW -->'''
page_path=OUT/'index.html';page=page_path.read_text()
page=re.sub(r'<!-- UPPER_CONNECTION_REVIEW -->.*?<!-- /UPPER_CONNECTION_REVIEW -->','',page,flags=re.S)
page=page.replace('</main>',section+'</main>')
if joint_ok:
    page=page.replace('头部上段仍有冲突，完整线束仍未完成，主模型没有采用C6。','新的CAM上段候选已通过共同检查，见下方最新记录；完整线束仍未完成，主模型没有采用C6。')
page_path.write_text(page)
note=OUT/'UPPER_CONNECTION_REVIEW.md'
note.write_text('# CAM上部汇合复核\n\n'+summary+'\n\n'+'\n'.join(f'- CAM {pin}: {n}条单线候选。' for pin,n in counts.items())+'\n\n旧对称缓存的方向标签修正见本轮原始筛查报告；工程通过结论未被放宽。所有检查为有限名义几何检查，线材采购、压接、疲劳、端部实配和完整带线装配未获准。\n')
readme=OUT/'README.md';readme.write_text('# M1.49 线束入口组合复核\n\n已采用C5与K1。C6下部九线候选已通过；C6开口仍待用户确认。\n\n'+summary+'\n\n具体结果见index.html#upper-connections。主模型与装配视频未加入候选导线。\n')
state=read(OUT/'continuation_status.json');now=datetime.datetime.now(datetime.timezone.utc).isoformat()
state['utc']=now;state['active_processes']=[]
state['upper_current'].update(fan_family=args.family,individual_counts=counts,upper_fan_connections=pack['status'] if pack else 'NOT_TESTED',
    C6_join=join['status'] if join else 'NOT_TESTED',joint_report=str(pack_path.relative_to(OUT)) if pack else None,neck_experiments=neck_summaries,main_changed=False)
if diagnostic:
    state['upper_current'].update(latest_rear_diagnostic=str(diagnostic_path.relative_to(OUT)),ten_local_paths=diagnostic['ten_local_paths'],
        remaining_conflict_slot=5,remaining_conflict_function=diagnostic['excluded_function'],all_eleven_local_paths='BLOCKED',rear_constant_length='BLOCKED')
state['next_work']=['C6 opening approval remains pending. K1 does not approve C6; do not alter the main model before a human answer.',
    ('Complete other upper endpoints, anchors, strain relief, FFC/FPC and wired assembly on the candidate; final connector inputs remain outstanding.' if c6_ok else 'Continue CAM transition routing and joint checks from the latest explicit fan/loop diagnosis; keep old failed reports intact.'),
    'Preserve SCS0009 and all hardware-owned sources. Received supplier/electrical evidence is archived; do not repeat completed source requests.']
if diagnostic:
    state['next_work'][1]='Work from rear_separated_neck/review/curves.npz and its exact pure replay helper. In the selected 171/1.1 case only slot5 (P_J18_1) has native support and CAM1 proximity failures. Preserve the other ten local paths. Review the actual support crossing before another route change; do not treat a conservative threshold witness as a global minimum. Then add upper-loop length compensation and connect the CAM endpoints, all still independent of main.'
write(OUT/'continuation_status.json',state)
files=reports+[page_path,note,readme,OUT/'upper_connection_commands.json',OUT/'execution_failures.json']+assets
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in files})
pub.update(utc=now,upper_transition_to_rearward_loops=pack['status'] if pack else 'BLOCKED',C6_four_CAM_join=join['status'] if join else 'NOT_TESTED',
    full_harness='BLOCKED',upper_connection_publisher_sha256=sha(Path(__file__)),upper_connection_publish_command=[sys.executable,*sys.argv])
write(OUT/'publication.json',pub)
print('UPPER_CONNECTIONS_PUBLISHED',counts,joint_ok,c6_ok,flush=True)
