"""Deliver checked CAM side-route progress with the remaining join explicit."""
from pathlib import Path
import datetime,hashlib,html,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
reports=[OUT/p for p in ['cam_oblique_return/tail_screen.json','neck_side_tail_join/join_screen.json','neck_side_tail_gentle/join_screen.json',
                         'cam_side_service/loop_screen.json','cam_side_following/loop_screen.json','side_cam_review/review.json']]
for p in reports:
    r=read(p)
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
join=read(reports[2]);service=read(reports[4]);review=read(reports[5]);assert join['status']==review['status']=='PASS'
case=next(r for r in join['results'] if r['status']=='PASS');has_service=service['status']=='PASS';assert review['includes_service_loops']==has_service
pub=read(OUT/'publication.json');assert sha(ROOT/'mechanical/mori_v1_2.blend')==pub['source_blend_sha256'] and not pub['C6_main_applied'] and not pub['C6_approved']
service_text=('侧向余量圈与引线也已通过本轮联合筛查，下一步补齐颈部出口至余量圈的四段固定连接。' if has_service else '侧向余量圈仍未通过，保留失败记录；已通过的侧向引线和颈部路线不等于完整连接。')
assets=[];pictures=''
for row in review['images']:
    p=OUT/'side_cam_review'/row['file'];assert sha(p)==row['sha256'];assets.append(p)
    pictures+=f'<figure><img src="{p.relative_to(OUT).as_posix()}" alt="独立CAM侧向路线候选，俯仰{row["pitch_deg"]}度" style="width:100%"><figcaption>俯仰{row["pitch_deg"]}°；外壳隐藏以检查内部。图中保留未完成连接的断口，曲线均为规划候选。</figcaption></figure>'
blend=OUT/'side_cam_review/MORI_M1_49_side_CAM_candidate.blend';assert sha(blend)==review['blend_sha256'];assets.append(blend)
links=''.join(f'<li><a href="{p.relative_to(OUT).as_posix()}">{html.escape(p.parent.name)}：{read(p)["status"]}</a></li>' for p in reports)
section=f'''<!-- SIDE_CAM_PROGRESS --><section id="side-cam"><h2>最新：CAM侧向引线与颈部联合通过</h2>
<p>四根CAM引线保留原连接器位置和5mm直线出线段，改为从侧边绕回。仅将三根颈部导线的上端向前缓移1.4mm，其余八条路径不动。新增468组结构检查、351组颈部线间检查和1560组引线／颈部线间检查通过；其余未变化的证据按原曲线复用。改变的颈部曲线最小采样弯曲半径为{case['minimum_sampled_bend_mm']:.3f}mm，没有放宽7mm规划限制或0.3mm净距。</p>
<p>{service_text}整条线束仍为BLOCKED，未放行供应商线长图纸、采购或制造。C6开口仍待确认，主模型、STL和装配视频仍保留已采用的C5＋K1版本。</p>
{pictures}<p><a href="{blend.relative_to(OUT).as_posix()}">可编辑独立候选</a> · <a href="SIDE_CAM_PROGRESS.md">当前接续点</a> · <a href="upper_connection_commands.json">实际执行记录</a></p>
<p>接下来：固定连接段与总长度补偿、身体前段共同检查、固定与应力释放、其他上端点、FFC/FPC、完整带线装配。端头和线材的实物资料限制继续保留。</p><ul>{links}</ul></section><!-- /SIDE_CAM_PROGRESS -->'''
page=OUT/'index.html';s=page.read_text();s=re.sub(r'<!-- SIDE_CAM_PROGRESS -->.*?<!-- /SIDE_CAM_PROGRESS -->','',s,flags=re.S)
s=s.replace('<h2>最新：颈部11线局部通过，上方接续仍在处理</h2>','<h2>此前：颈部11线局部通过</h2>')
s=s.replace('</main>',section+'</main>');page.write_text(s)
note=OUT/'SIDE_CAM_PROGRESS.md'
note.write_text('# CAM侧向引线接续\n\n'+service_text+'\n\n当前通过的颈部曲线：neck_side_tail_gentle/neck_curves.npz。四根引线：neck_side_tail_gentle/tails.npz。孔位、打印件、连接器和其他硬件姿态均未修改。\n\n三处上端由Z178至208平缓移向+Y1.4mm；原低端保持，其他八条数组相同。此改动仍是独立线束规划，主模型没有采用C6或任何候选线束。\n\n完整供应商长度、端头、扎固和应力释放、其他上端点、FFC/FPC、身体共同装配与实物疲劳仍未完成。\n')
readme=OUT/'README.md';readme.write_text('# M1.49 线束候选\n\n主模型已采用C5＋K1。C6待确认。\n\n最新：CAM侧向引线与颈部联合通过。'+service_text+'\n\n完整线束仍BLOCKED；候选没有加入主模型、STL或装配视频。见 index.html#side-cam。\n')
state=read(OUT/'continuation_status.json');now=datetime.datetime.now(datetime.timezone.utc).isoformat();state['utc']=now;state['active_processes']=[]
state['upper_current'].update(latest_rear_diagnostic='side_cam_review/review.json',side_tails_plus_neck='PASS',
    side_tails_neck_report='neck_side_tail_gentle/join_screen.json',new_candidate_curves='neck_side_tail_gentle/neck_curves.npz',new_tail_curves='neck_side_tail_gentle/tails.npz',
    side_service_report='cam_side_following/loop_screen.json',side_service_status=service['status'],CAM_tail_neck_conflict_cases=0,
    fixed_fans='NOT_TESTED',full_harness='BLOCKED',main_changed=False)
state['next_work']=['C6 opening is still awaiting a human answer; K1 approval does not approve C6.',
    'Use neck_side_tail_gentle PASS: slots4/8/9 move +Y1.4 gradually over Z178..208; other eight paths are unchanged. Four concentric side-return CAM tails coexist; native ports and first5mm leads retained.',
    ('Connect the four fixed-yaw fans from the accepted neck endpoints to the accepted side-service-loop anchors. Preserve motion groups; then check complete mutual/self distances and full combined yaw/pitch samples, actual joined lengths and C6 body-prefix coexistence.' if has_service else 'Complete the side service loop after reading cam_side_following actual native/line conflicts; do not mark the separate passing neck/tails as a complete wire.'),
    'Complete anchoring/strain relief, other upper endpoints, FFC/FPC and wired assembly. Supplier pin/terminal and physical wire limitations remain; hardware-owned sources stay read-only.']
write(OUT/'continuation_status.json',state)
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in reports+assets+[page,note,readme,OUT/'upper_connection_commands.json',OUT/'execution_failures.json']})
pub.update(utc=now,CAM_side_tail_neck='PASS',CAM_tail_neck_join='PASS',CAM_side_service_loops=service['status'],CAM_fixed_fans='NOT_TESTED',full_harness='BLOCKED',
           side_progress_publisher_sha256=sha(Path(__file__)),side_progress_publish_command=[sys.executable,*sys.argv])
write(OUT/'publication.json',pub);print('SIDE_CAM_PROGRESS_PUBLISHED',service['status'],flush=True)
