# -*- coding: utf-8 -*-
"""Publish screening correction and bounded search result; not a CAD release."""
from pathlib import Path
import json,hashlib,datetime,runpy,re,html,urllib.request
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;PROJECT=HERE.parents[3]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
main=PROJECT/'mechanical/mori_v1_2.blend';main_hash=sha(main)
reports={n:read(HERE/n) for n in ['screen_regression.json','terminal_straights_corrected.json',
    'endpoint_plug_body_sequence.json','imu_assembly_pools.json','imu_side_assembly_pools.json',
    'imu_refined_pools.json','imu_refined_assembly_pools.json','imu_refined_assembly_joint.json']}
assert all(r['source_blend_sha256']==main_hash for r in reports.values())
assert all(reports[n]['status']=='PASS' for n in ['screen_regression.json','terminal_straights_corrected.json','endpoint_plug_body_sequence.json'])
for stem in ['imu_assembly','imu_side_assembly','imu_refined_assembly']:
    r=reports[stem+'_pools.json']
    assert r['source_pool_sha256']==sha(HERE/r['source_pool_file'])
    assert 'Nearest-face-normal sign is not used' in r['method']
joint=reports['imu_refined_assembly_joint.json']
assert joint['source_sha256']==sha(HERE/'imu_refined_assembly_pools.json')
# Preserve the old real solid collision record referenced by hardware A5.
assert sha(HERE/'fourteen_body_sequence.json')=='74ed4fdb5d4db7c97b28c787cea37d1effc9819d42d883f17c5708d365bc7acc'
runpy.run_path(str(HERE/'publish_fourteen.py'),run_name='__main__')
when=datetime.datetime.now(datetime.timezone.utc).isoformat()
stats=[]
for filename,label in [('imu_assembly_pools.json','原后缘候选'),('imu_side_assembly_pools.json','原侧缘候选'),('imu_refined_assembly_pools.json','保留结构的局部细化候选')]:
    r=reports[filename]
    stats.append(dict(file=filename,label=label,input=sum(x['input'] for x in r['search']),passed=sum(x['passed'] for x in r['search'])))
style=re.search(r'<style>(.*?)</style>',(HERE/'index.html').read_text(),re.S).group(1)
tr=''.join('<tr><td>'+r['label']+'</td><td>'+str(r['input'])+'</td><td>'+str(r['passed'])+'</td><td><a href="'+r['file']+'">记录</a></td></tr>' for r in stats)
body=f'''
<a href="index.html">返回十四线静态研究</a><h1>装配走线：筛选修正与未完成项</h1>
<p>主模型 M1.47 与 M1.47-A1 视频保持；未采用研究开口，未改针号或硬件。</p>
<p class="notice">八根IMU线的联合方案仍为 {joint['status']}。单根路线能通过，并不能证明八根同时可装；现有候选不能作为完整线束下单或裁线图。</p>
<h2>这次确认的结果</h2><ul>
<li>八个端点插头本体：407个身体装配位置、两处承重桥螺钉和工具路径通过。</li>
<li>H01–H05共44个单线端后5mm直段分配通过；真实端子出线及5mm分配仍属假设。</li>
<li>原十四线候选的静态实体与130头部姿态通过；原407位置身体装配的真实相交FAIL保持。</li>
</ul>
<h2>修正一次误判</h2><p>此前以“最近三角面法向的正负”判断点是否在实体内部。靠近三角面边缘时，这个判断不成立：实际空腔点离支座约14.88mm，却被误拒绝。旧的“整批候选全部被拒绝”结论撤回；原记录放入历史目录，没有当成不存在路线的证明。</p>
<p>现在先保留完整曲线的表面距离下界。若曲线有一点在物体包围盒之外，且整段已证实不穿过表面，就排除整体包含；仅在整段都被包围盒覆盖时，用封闭实体探针确认包含。空腔、实体内部、穿透及近表面四项实际场景检查通过。</p>
<h2>修正后的有限候选搜索</h2><table><tr><th>候选组</th><th>输入曲线</th><th>单线通过</th><th>证据</th></tr>{tr}</table>
<p>各行包含重复或细化关系，不能把数量相加当成不同结构方案。细化候选做了八线兼容组合搜索：{joint['search_nodes']}个搜索节点、{joint['compatibility_pairs']}对兼容计算，结果为{joint['status']}。这是有限候选集的结果，不是所有可能走向都不可行的证明。</p>
<h2>还需要完成</h2><p>八线同时布置、绑束与应力释放、真实出线和松量、带线插拔，以及H05、头部和其他分支。线束制作方式已向用户询问；推荐供应商按图压接，但尚未选定或下单。</p>
<p>独立开孔研究未采用。其早期筛选同样可能受误判影响，不能据此要求用户接受结构改动。</p>
<p><a href="screen_regression.json">四项回归检查</a> · <a href="terminal_straights_corrected.json">44个端后直段</a> · <a href="endpoint_plug_body_sequence.json">插头装配检查</a> · <a href="imu_refined_assembly_joint.json">八线组合搜索</a> · <a href="filter_false_rejection_history/README.md">撤回记录说明</a> · <a href="deck_slot_review/README.md">未采用的开孔研究</a></p>
<p>PROTOTYPE / UNVALIDATED。所有PASS仅覆盖声明的名义检查，制造和完整线束没有放行。</p>'''
page=HERE/'assembly_screen_review.html'
page.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 装配走线筛选复核</title><style>'+style+'</style><main>'+body+'</main></html>')
note='<section id="screen-correction-update"><h2>后续装配检查</h2><p><a href="assembly_screen_review.html">插头与走线筛选复核</a>：插头本体和44个端后直段通过；修正空腔误判后，八线联合排布仍未完成。研究开口未采用，主模型保持。</p></section>'
p=HERE/'index.html';s=p.read_text();s=re.sub(r'<section id="screen-correction-update">.*?</section>','',s,flags=re.S);s=s.replace('<main>','<main>'+note,1);p.write_text(s)
status=read(PARENT/'work_status.json');old=next(r for r in status['remaining'] if r['id']=='harness')['detail']
new='八个端点插头的407位置装配、44个端后直段通过。原十四线静态/头部姿态通过但身体装配FAIL保持。候选筛选的空腔误判已修正；细化1920条曲线中1224条单线通过，八线联合排布仍未完成。线束制作方式待用户选择；选型、绑束、松量及其余分支未完成。'
next(r for r in status['remaining'] if r['id']=='harness')['detail']=new
status['updated_utc']=when
status['prearrival_wire_addendum'].update(screening_containment_fix='PASS',screen_regression='PASS',
    endpoint_plug_body_sequence='PASS',terminal_straights='PASS',terminal_straight_count=44,
    joint_IMU_assembly_layout=joint['status'],candidate_slot_adopted=False,
    latest_screen_review='harness_A2/assembly_screen_review.html',
    harness_build_method='PENDING_USER_CHOICE; supplier-made recommended, no purchase authorized')
write(PARENT/'work_status.json',status)
p=PARENT/'index.html';s=p.read_text().replace(html.escape(old),html.escape(new)).replace(old,new);p.write_text(s)
p=HERE/'REVIEW.md';s=p.read_text();s+='\n## 最新筛选复核\n\n见[assembly_screen_review.html](assembly_screen_review.html)。旧空腔误拒绝已修正；44个端后直段和八插头407位置通过。1920条细化曲线中1224条单线通过，八线组合仍BLOCKED。没有采用开口或修改主模型。\n';p.write_text(s)
core=read(PARENT/'M1_47_delivery.json')
for path,digest in core['files'].items():
    if path.endswith('/work_status.json'):core['files'][path]=sha(PROJECT/path)
    else:assert sha(PROJECT/path)==digest,path
write(PARENT/'M1_47_delivery.json',core)
delivery=read(HERE/'delivery.json')
pages=[page,HERE/'index.html',PARENT/'index.html'];checks=[]
for p in pages:
    missing=[]
    for ref in re.findall(r'(?:href|src)=["\']([^"\']+)',p.read_text()):
        if ref.startswith(('http:','https:','#','data:','mailto:')):continue
        if not (p.parent/ref.split('#')[0].split('?')[0]).resolve().exists():missing.append(ref)
    assert not missing,(str(p),missing)
    checks.append(dict(page=str(p.relative_to(PROJECT)),missing=missing))
http=[]
for p in pages:
    url='http://127.0.0.1:58201/'+str(p.relative_to(PROJECT))
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as resp:http.append(dict(url=url,status=resp.status))
assert all(r['status']==200 for r in http)
for p in HERE.rglob('*'):
    if p.is_file() and p!=HERE/'delivery.json' and p.suffix in ['.json','.py','.log','.md','.html','.png','.blend','.svg']:
        delivery['files'][str(p.relative_to(PROJECT))]=sha(p)
for p in [PARENT/'index.html',PARENT/'work_status.json']:
    delivery['files'][str(p.relative_to(PROJECT))]=sha(p)
commands=[
 'inspect_deck_slots.py -- --ecowire','imu_slot_routes.py -- --ecowire',
 'filter_imu_body_paths.py -- --late-rear','check_fourteen_body_sequence.py -- --endpoint-plugs',
 'imu_individual_routes.py -- --ecowire --side-path','filter_imu_body_paths.py -- --side-path',
 'imu_individual_routes.py -- --ecowire --notch-path','validate_slot_access.py -- --ecowire',
 'imu_inner_slot_routes.py -- --ecowire','filter_imu_body_paths.py -- --deck-slot',
 'audit_filter_rejections.py -- --ecowire','filter_imu_body_paths.py',
 'refine_imu_assembly_routes.py -- --ecowire','filter_imu_body_paths.py -- --refined',
 'validate_screen_regression.py -- --ecowire','recheck_terminal_straights.py -- --ecowire']
delivery['commands'] += ['/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/'+s for s in commands]
delivery['commands'] += ['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_imu_joint.py --assembly',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_imu_joint.py --assembly --refined',
 'python3 mechanical/studies/prearrival_finish/harness_A2/publish_filter_correction.py']
delivery.update(verified_utc=when,screening_correction='PASS',IMU_joint_assembly_layout=joint['status'],
    endpoint_plug_body_sequence='PASS',nominal_terminal_straights='PASS',candidate_slot_adopted=False,
    screening_statistics=stats,latest_local_link_checks=checks,latest_HTTP_checks=http)
write(HERE/'delivery.json',delivery)
assert sha(main)==main_hash
print('SCREEN_CORRECTION_DELIVERY_VERIFIED',len(delivery['files']),'files',len(checks),'pages','IMU_joint',joint['status'],'main',main_hash)
