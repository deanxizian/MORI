# -*- coding: utf-8 -*-
"""Publish independently checked H01-H04 study, keeping the main CAD intact."""
from pathlib import Path
import json,hashlib,datetime,runpy,re,html,urllib.request
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;PROJECT=HERE.parents[3]
REVIEW=HERE/'assembly_safe_review'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
main=PROJECT/'mechanical/mori_v1_2.blend';main_hash=sha(main)
joint_file=HERE/'imu_axial_complete_joint_diagnostic.json'
joint=read(joint_file);static=read(REVIEW/'fourteen_validation.json');body=read(REVIEW/'fourteen_body_sequence.json')
datum=read(HERE/'imu_axial_curve_datums.json');preview=read(REVIEW/'fourteen_preview_manifest.json')
assert all(r['status']=='PASS' for r in [joint,static,body,datum,preview])
assert all(r['source_blend_sha256']==main_hash for r in [joint,static,body,datum])
assert preview['source_main_sha256']==main_hash and sha(REVIEW/preview['candidate_blend'])==preview['candidate_sha256']
for r in preview['images']:assert sha(REVIEW/r['file'])==r['sha256']
assert joint['source_sha256']==sha(HERE/joint['source_pool_file'])
assert static['sources'][str(joint_file.relative_to(PROJECT))]==sha(joint_file)
for path,digest in static['sources'].items():assert sha(PROJECT/path)==digest,path
assert body['source_wire_check_sha256']==sha(REVIEW/'fourteen_validation.json')
assert sha(HERE/'fourteen_body_sequence.json')=='74ed4fdb5d4db7c97b28c787cea37d1effc9819d42d883f17c5708d365bc7acc'
runpy.run_path(str(HERE/'publish_filter_correction.py'),run_name='__main__')
when=datetime.datetime.now(datetime.timezone.utc).isoformat()
gap=min(r['conservative_inflated_capsule_gap_lower_bound_mm'] for r in static['wire_to_wire'])
rigid_gap=min(q['conservative_capsule_gap_lower_bound_mm'] for r in static['rigid_solids'] for q in r['gap_checks'])
style=re.search(r'<style>(.*?)</style>',(HERE/'index.html').read_text(),re.S).group(1)
rows=''.join(f"<tr><td>{r['id']}</td><td>{'左侧' if r['route_side']=='left' else '右侧'}</td><td>{r['minimum_curvature_radius_mm']:.2f} mm</td><td>{r['geometric_centerline_length_mm']:.1f} mm</td></tr>" for r in sorted(joint['routes'],key=lambda r:r['pin']))
content=f'''
<a href="../index.html">返回走线研究</a><h1>固定线束：八根IMU线与原六根线的联合候选</h1>
<p>保持主模型 M1.47、原针脚对应、所有板卡和打印件。未新增开孔，没有把研究线束写入正式装配或视频。</p>
<p class="notice">H01–H04 共14根固定线通过本页声明的名义几何检查。整机线束仍未完成：其余分支、绑束、应力释放、真实出线、松量与带线插拔还需继续落实。这不是裁线单或生产放行。</p>
<table><tr><th>检查</th><th>结果</th><th>范围</th></tr>
<tr><td>针序、端点、曲线与弯曲半径</td><td>PASS</td><td>2203条筛后曲线复核；选中8条保留原编号与5mm端后直段</td></tr>
<tr><td>14根线实体及静态间隙</td><td>PASS</td><td>14个连续实体，91组线间检查；保守线间下界{gap:.3f}mm、近邻硬件下界{rigid_gap:.3f}mm</td></tr>
<tr><td>头部运动</td><td>PASS</td><td>130个组合姿态，未检出相交</td></tr>
<tr><td>身体与承重桥装配</td><td>PASS</td><td>407个位置及两处横向螺钉/工具路径，未检出相交</td></tr></table>
<p>以上是离散位置和明确公差分配下的检查；不代表连续运动、制造误差、线束柔性或实物装配已经验证。</p>
<img src="fourteen_rear_upper.png" alt="十四根固定线候选，上后视图" style="max-width:100%;height:auto"><img src="fourteen_rear_lower.png" alt="十四根固定线候选，下后视图" style="max-width:100%;height:auto">
<p>橙色为尚未选定的线材及名义插头。外壳、电池等仅在预览中隐藏，实体检查仍包含它们。</p>
<h2>八根IMU线</h2><table><tr><th>线号</th><th>通过方向</th><th>最小名义弯曲半径</th><th>几何中心线长</th></tr>{rows}</table>
<p>几何长度未加入压接、插入、松量或制作余量，不能用于裁线。Alpha6711/6712仍是有厂家数据的未选定候选；实际端子横向出线及5mm直段分配为ASSUMED。</p>
<h2>与前次检查的关系</h2><p>前一组14线通过静态检查，但在身体装配中实际碰到了壳体或后板，失败记录保留。本次组合采用3根IMU线的两端转弯细化候选，并重新选择其余曲线，解决了本组14线在规定装配路径中的相交。此前空腔误判的修正与回归记录也保留，不能把有限候选搜索的失败当作结构无解。</p>
<p><a href="MORI_H01_H04_CANDIDATE_NOT_ADOPTED.blend">独立候选 Blender</a> · <a href="fourteen_validation.json">实体与头部运动</a> · <a href="fourteen_body_sequence.json">身体装配与工具</a> · <a href="../imu_axial_curve_datums.json">针脚及曲线数据复核</a> · <a href="../imu_axial_complete_joint_diagnostic.json">八线联合选择</a> · <a href="../assembly_screen_review.html">此前筛选修正记录</a></p>
<p>PROTOTYPE / UNVALIDATED。主模型与 M1.47-A1 装配视频未改变。</p>'''
page=REVIEW/'index.html';page.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 固定线装配候选</title><style>'+style+'</style><main>'+content+'</main></html>')
for path,href in [(HERE/'index.html','assembly_safe_review/index.html'),(HERE/'assembly_screen_review.html','assembly_safe_review/index.html'),(PARENT/'index.html','harness_A2/assembly_safe_review/index.html')]:
    s=path.read_text();s=re.sub(r'<section id="fixed-wire-assembly-update">.*?</section>','',s,flags=re.S)
    note=f'<section id="fixed-wire-assembly-update"><h2>最新固定线装配候选</h2><p><a href="{href}">H01–H04 共14根线</a>已通过静态、130头部姿态和407身体装配位置检查。其余分支、绑束、真实出线及松量仍未完成；主模型保持。</p></section>'
    s=s.replace('<main>','<main>'+note,1)
    if path==HERE/'index.html':
        s=re.sub(r'<section id="screen-correction-update">.*?</section>','',s,flags=re.S)
        s=re.sub(r'<h1>(.*?)</h1>',r'<h1>历史记录 · \1</h1>',s,count=1,flags=re.S)
    if path.name=='assembly_screen_review.html':
        s=s.replace('<h1>装配走线：筛选修正与未完成项</h1>','<h1>历史记录：走线筛选修正</h1>')
        s=s.replace('八根IMU线的联合方案仍为 BLOCKED。','以下为此前有限候选集的 BLOCKED 记录；当前通过的联合候选见上方链接。')
    path.write_text(s)
status=read(PARENT/'work_status.json');row=next(r for r in status['remaining'] if r['id']=='harness');old=row['detail']
row['detail']='H01–H04 共14根固定线的新联合候选：14实体、91组线间检查、130头部姿态、407身体装配位置及桥螺钉/工具路径通过。未新增打印孔或改针脚。供应商按图制作已确认；其余分支、实际线材、真实出线、绑束、应力释放、松量和带线插拔仍未完成；主模型未采纳研究线束。'
row['status']='BLOCKED';status['updated_utc']=when
status['prearrival_wire_addendum'].update(joint_IMU_assembly_layout='PASS',fourteen_static_assembly_candidate='PASS',
    fourteen_candidate_body_sequence='PASS',fourteen_head_poses=130,fourteen_body_positions=407,
    candidate_slot_adopted=False,complete_harness='BLOCKED',main_harness_adopted=False,
    latest_assembly_review='harness_A2/assembly_safe_review/index.html')
write(PARENT/'work_status.json',status)
p=PARENT/'index.html';s=p.read_text().replace(html.escape(old),html.escape(row['detail'])).replace(old,row['detail']);p.write_text(s)
p=HERE/'REVIEW.md';s=p.read_text();s=re.sub(r'\n## 最新固定线装配候选\n[\s\S]*','',s)
s+='\n## 最新固定线装配候选\n\n见[assembly_safe_review/index.html](assembly_safe_review/index.html)：新14线候选的实体、91线对、130头部姿态及407身体装配位置通过，主模型未改。保留原14线身体装配FAIL记录；整机其余线束、选型、绑束和松量仍未完成。\n';p.write_text(s)
core=read(PARENT/'M1_47_delivery.json')
for path,digest in core['files'].items():
    if path.endswith('/work_status.json'):core['files'][path]=sha(PROJECT/path)
    else:assert sha(PROJECT/path)==digest,path
write(PARENT/'M1_47_delivery.json',core)
delivery=read(HERE/'delivery.json');pages=[page,HERE/'index.html',HERE/'assembly_screen_review.html',PARENT/'index.html'];checks=[]
for p in pages:
    missing=[]
    for ref in re.findall(r'(?:href|src)=["\']([^"\']+)',p.read_text()):
        if ref.startswith(('http:','https:','#','data:','mailto:')):continue
        if not (p.parent/ref.split('#')[0].split('?')[0]).resolve().exists():missing.append(ref)
    assert not missing,(p,missing)
    url='http://127.0.0.1:58201/'+str(p.relative_to(PROJECT))
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as resp:code=resp.status
    assert code==200;checks.append(dict(page=str(p.relative_to(PROJECT)),missing=missing,http_status=code))
for p in HERE.rglob('*'):
    if p.is_file() and p!=HERE/'delivery.json' and p.suffix in ['.json','.py','.log','.md','.html','.png','.blend','.svg']:
        delivery['files'][str(p.relative_to(PROJECT))]=sha(p)
for p in [PARENT/'index.html',PARENT/'work_status.json']:delivery['files'][str(p.relative_to(PROJECT))]=sha(p)
commands=[
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_imu_joint.py --assembly --refined --diagnose',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/refine_imu_terminal_turns.py -- --ecowire',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/filter_imu_body_paths.py -- --pool imu_terminal_turn_pools.json --output-prefix imu_terminal_assembly',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/merge_imu_terminal_pools.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_imu_joint.py --assembly --pool imu_targeted_assembly_pools.json --output-prefix imu_targeted_assembly_joint --diagnose',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/refine_imu_terminal_turns.py -- --ecowire --upper',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/filter_imu_body_paths.py -- --pool imu_upper_turn_pools.json --output-prefix imu_upper_assembly',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/merge_imu_terminal_pools.py --upper',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_imu_joint.py --assembly --pool imu_dual_terminal_assembly_pools.json --output-prefix imu_dual_terminal_assembly_joint --diagnose',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_imu_joint.py --assembly --pool imu_dual_terminal_assembly_pools.json --output-prefix imu_dual_arc_assembly_joint --arc-prune --max-seconds 600 --diagnose',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/refine_imu_axial_pairs.py -- --ecowire',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/filter_imu_body_paths.py -- --pool imu_axial_pair_pools.json --output-prefix imu_axial_pair_assembly',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/merge_imu_terminal_pools.py --axial-pairs',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_imu_joint.py --assembly --pool imu_axial_complete_assembly_pools.json --output-prefix imu_axial_complete_joint --arc-prune --max-seconds 600 --diagnose',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/audit_axial_curve_datums.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/validate_fourteen.py -- --assembly-reviewed --joint imu_axial_complete_joint_diagnostic.json',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/check_fourteen_body_sequence.py -- --assembly-reviewed',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/render_fourteen.py -- --assembly-reviewed',
 'python3 mechanical/studies/prearrival_finish/harness_A2/publish_assembly_safe.py']
delivery['commands']+=commands
delivery.update(verified_utc=when,IMU_joint_assembly_layout='PASS',fourteen_assembly_candidate='PASS',
    latest_assembly_review=str(page.relative_to(PROJECT)),latest_assembly_static_gap_lower_mm=gap,
    complete_harness='BLOCKED',main_harness_adopted=False,latest_local_link_checks=checks)
write(HERE/'delivery.json',delivery)
assert sha(main)==main_hash
print('ASSEMBLY_SAFE_DELIVERY_VERIFIED',len(delivery['files']),'files',len(checks),'pages','main',main_hash)
