# -*- coding: utf-8 -*-
"""Publish received A3 review and verify this documentation-only addendum."""
from pathlib import Path
import json,hashlib,datetime,html,re,urllib.request
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;PROJECT=HERE.parents[3]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
when=datetime.datetime.now(datetime.timezone.utc).isoformat()
review=read(PARENT/'J10_A3_review/review.json')
base=read(PARENT/'M1_47_delivery.json')
main=PROJECT/'mechanical/mori_v1_2.blend'
assert sha(main)==base['source_blend_sha256']==review['source_blend_sha256']
for path,digest in review['sources'].items():assert sha(PROJECT/path)==digest,path
val=read(HERE/'ecowire_validation.json');joint=read(HERE/'ecowire_joint.json')
assert val['status']==joint['status']=='PASS'
assert val['source_joint_sha256']==sha(HERE/'ecowire_joint.json')
assert val['source_blend_sha256']==sha(main)

# Data-led final A3 review. Keep received earlier C2 report immutable.
back='\n'.join('|%s|%.2f|%.2f|'%(r['reference'],r['supplied_back_depth_mm'],r['extra_downward_clearance_lower_bound_mm']) for r in review['backside'])
wire=[]
for model in ['Alpha5853','Alpha6711_NOT_SELECTED']:
    for z in [1.2,1.8,2.4,3.,3.6]:
        rows=[r for r in review['local_eight_wire_bends'] if r['wire']==model and r['assumed_exit_z_above_pcb_mm']==z]
        angles=[str(r['bend_angle_from_Y_deg']) for r in rows if r['status']=='PASS']
        wire.append((model,z,'、'.join(angles) or '无'))
wire_md='\n'.join('|%s|%.1f|%s|'%(m,z,a) for m,z,a in wire)
md=f'''# J10 A3：独立机械复核

{when}。主模型 M1.47 保持。收到的是独立摆放候选，电气布线未完成、正式板没有替换。

## 已检查

按 A3 最终位置：D30/F70/R50 原 XY 移到背面，JP70 到 (35,44.5)/0°，TP71 到 (23,35)。收到的候选工程及16份正式 PCB 工程文件哈希均核对，不采用早期失败路由中的位置。

三颗背面器件分配包络均无交叠：

|器件|背面深度 mm|额外向下移动余量下界 mm|
|---|---:|---:|
{back}

每0.02mm向下扫描至首次碰撞。这是竖向余量，不是全方向最小间隙。D30/F70含硬件提供的0.15mm装配分配；R50为2×1×1mm假定包络。未扩大整板背面上限。

J10座与插头包络无新增交叠；插头退5.35mm再上提12mm的连续盒体扫掠通过。这是裸插头几何，不是带线拔插完成。

## JP70 和 TP71 的操作阶段

JP70采用原KiCad针座模型刚体旋转/平移，外部零件没有交叠。正式PCB仍保留原孔，因此研究中针脚与旧板实体有约1.31mm³重合，明确列为源差异，未将其当作新板孔位/制造通过。

装好承重桥后，JP70上方直径3/5mm、长度20mm的工具通道被Yaw_Base和Yaw_Bearing挡住；8mm通道还碰J4/J5。TP71上方直径1/2/3mm、长度25mm的探针通道均被Yaw_Base挡住。**这些操作可安排在装桥和Yaw轴承之前**：移除这两件后，上述3/5mm与1/2/3mm分配通道没有其余阻挡。这只核对空通道，跳线帽型号、夹持和电气测量工艺仍未确定；不代表装好头部后可直接维护。

## 八线局部转弯

保留端后5mm直段、0.3mm刚体/线间目标间隙。使用原5853或独立6711候选各自的厂家参数，未缩小原线材要求。所有高度仍未知；下面仅是敏感性试排。

|线材|假定出线高于板面 mm|八线同时通过的局部转弯角度（从机身Y轴起）|
|---|---:|---|
{wire_md}

线间使用点到线段距离并扣除采样间距上界，保留保守下界。此检查尚未并入其余线束、束扎、应力释放和带线取件。不得将2.4/3.0/3.6mm选成已知硬件高度。

## 新的打样前阻断

硬件A3查到正式板18个JST PH接口的0.75mm名义孔小于厂家针对玻纤镀通孔板的成品孔建议。2P为0.80–0.85mm，3–16P为0.85–0.90mm。来源：[JST FAQ](https://www.jst.com/resources/faq/)，已核对硬件保存的官方HTML。机械不改原生板；由硬件联动孔、铜盘、公差、邻线和DRC，之后正式交接。

C2只有J10试改0.90mm孔/1.50mm铜盘。**原生候选DRC仍FAIL：26处未连接、14条警告；制造和采购未放行。**

## 文件与范围

- [逐项机械数据](review.json)
- [A3原始交接](../../../../hardware/v1_2/handoff/mechanical_P5R7_prearrival_A3_J10.json)
- [硬件说明](../../../../hardware/v1_2/prearrival_20261002/j10_refinement_C2/README.md)
- [前一份局部C2记录](../J10_C2_review/REVIEW.md)保留为历史证据。

当前完整线束、实际出线高度、最终板卡、热/电气/实物装配均未完成。所有改动仅在研究数据中，主模型、打印件和装配视频保持。
'''
(PARENT/'J10_A3_review/REVIEW.md').write_text(md)
style=re.search(r'<style>(.*?)</style>',(HERE/'index.html').read_text(),re.S).group(1)
back_html=''.join('<tr><td>%s</td><td>%.2f</td><td>%.2f</td></tr>'%(r['reference'],r['supplied_back_depth_mm'],r['extra_downward_clearance_lower_bound_mm']) for r in review['backside'])
wire_html=''.join('<tr><td>%s</td><td>%.1f</td><td>%s</td></tr>'%(m,z,a) for m,z,a in wire)
(PARENT/'J10_A3_review/index.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · J10 A3机械复核</title><style>{style}</style><main><a href="../index.html">返回到货前工作</a><h1>J10 A3：局部摆放通过，线束和PCB仍未完成</h1><p class="notice">独立候选。主模型 M1.47、正式电源板 P5R6、打印件和视频保持。C2原生DRC仍有26处未连接和14条警告，没有制造放行。</p><h2>背面空间与插头路径</h2><table><tr><th>器件</th><th>背面包络深度 mm</th><th>额外向下余量下界 mm</th></tr>{back_html}</table><p>三处包络没有交叠；余量来自0.02mm步长竖向扫描，不是全方向最小间隙，也没有扩大整板背面上限。R50仍是2×1×1mm假定包络。裸插头退出5.35mm、上提12mm的连续盒体扫掠通过。</p><h2>操作要放在装桥之前</h2><p>JP70新位置针座没有外部碰撞。其上方3/5mm工具通道被承重桥与Yaw轴承挡住；TP71上方1/2/3mm探针通道被承重桥挡住。未装这两件时，上述通道没有其余阻挡。跳线帽本体、实际夹持和带线取件仍需完善，不能认为装好头部后可直接维护。</p><h2>八线局部试排</h2><p>始终保留5mm端后直段、0.3mm目标间隙，并检查八根线之间的空间。出线高度没有已知值；下表是敏感性比较，不能挑能通过的高度作为硬件尺寸。6711只是独立线材候选。</p><table><tr><th>线材</th><th>假定高度 mm</th><th>通过的局部转弯角度</th></tr>{wire_html}</table><p>尚未并入其余线束、绑束、拆装松量和完整H05路线。</p><h2>打样前新增：18个PH接口孔径</h2><p>硬件A3抽取的18个正式PH接口目前名义孔径为0.75mm。<a href="https://www.jst.com/resources/faq/">JST针对玻纤镀通孔板的成品孔建议</a>是2P 0.80–0.85mm、3–16P 0.85–0.90mm。硬件需要一起修正孔、铜盘、公差和邻线并重跑DRC；机械没有改板孔。C2只修了J10候选，其他正式板尚未替换。</p><p><a href="review.json">机械原始数据</a> · <a href="REVIEW.md">完整说明</a> · <a href="../../../../hardware/v1_2/handoff/mechanical_P5R7_prearrival_A3_J10.json">A3交接</a> · <a href="../harness_A2/index.html">H01–H03候选</a></p></main></html>''')

# Keep the unplaced nominal mass separate from the saved CAD mass/COM.
a2p=PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A2.json';a2=read(a2p)
engp=PARENT/'engineering_current.json';eng=read(engp)
extra=sum(x['mass_nominal_g'] for x in a2['brake_resistors'])
mass=dict(revision='V1.2-M1.47',status='BLOCKED',scope='Unplaced candidate nominal-mass addendum only',
    source_blend_sha256=sha(main),base_report_sha256=sha(engp),hardware_A2_sha256=sha(a2p),
    saved_model_estimate_g=eng['totals']['whole']['mass_g'],unplaced_resistor_candidates=a2['brake_resistors'],
    unplaced_resistors_nominal_total_g=extra,partial_candidate_sum_g=eng['totals']['whole']['mass_g']+extra,
    physical_measured=False,COM_recomputed=False,main_model_changed=False,
    limitations=['Two resistor candidates have documented nominal mass but no approved mounting location.',
        'The sum is neither complete robot mass nor a proven minimum/upper bound.',
        'Retain original mass/material uncertainties and missing harness, fuse/holder and thermal mounts; no automatic dynamics/torque release.'])
(PARENT/'engineering_A2_mass_addendum.json').write_text(json.dumps(mass,ensure_ascii=False,indent=2)+'\n')

status=read(PARENT/'work_status.json');old={r['id']:r.copy() for r in status['remaining']}
for row in status['remaining']:
    if row['id']=='hardware_selection':
        row['detail']='现成软轮胎未定型。收到独立A3/C2：D30/F70/R50局部背面空间和裸插头退出通过，JP70/TP71操作需在装桥前；真实出线与带线取件未定。候选有26处未连接、14条DRC警告，正式板与机械模型未替换。'
        row['evidence']='J10_A3_review/index.html'
    if row['id']=='supplier_interfaces':
        row['detail']='SCS0009舵盘/短轴锁紧、S288输出自攻螺钉、WeAct E成品孔/针与插接长度仍缺资料；新增JST PHR8插合后真实出线高度。硬件A3查到18个正式PH接口孔径需在打样前修正并重跑DRC，不能只留到实物验证。'
    if row['id']=='load_budget':
        row['detail']='M1.47名义质量估算1.324kg仍超过1.0–1.2kg工程目标。A2两颗未布置制动电阻另计标称3.8g，候选部分合计1.327kg；未选模块、完整线束和热隔离固定仍缺，未修改主模型COM或宣称动力学通过。'
status['updated_utc']=when
status['prearrival_wire_addendum']['J10_A3_review']='J10_A3_review/index.html'
status['prearrival_wire_addendum']['PH_formal_interfaces_requiring_correction']=18
status['prearrival_wire_addendum']['A3_candidate_applied']=False
(PARENT/'work_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
top=(PARENT/'index.html').read_text()
for row in status['remaining']:
    prev=old[row['id']]
    top=top.replace(html.escape(prev['detail']),html.escape(row['detail'])).replace(prev['detail'],row['detail'])
top=top.replace('<a href="J10_C2_review/index.html">J10 C2局部复核</a>已反馈硬件；带线拔插仍未完成。','<a href="J10_A3_review/index.html">J10 A3最新复核</a>已反馈硬件；带线拔插、候选布线及18个PH接口孔径修正仍未完成。')
(PARENT/'index.html').write_text(top)
# M1.47 model/artifact hashes remain untouched; only the live checklist changed.
for path,digest in base['files'].items():
    actual=sha(PROJECT/path)
    if path.endswith('/work_status.json'):base['files'][path]=actual
    else:assert actual==digest,'Unexpected main delivery drift: '+path
base['documentation_addendum']='harness_A2/delivery.json'
(PARENT/'M1_47_delivery.json').write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n')

# Check all generated HTML references, including cross-links to received files.
pages=[HERE/'index.html',PARENT/'index.html',PARENT/'J10_C2_review/index.html',PARENT/'J10_A3_review/index.html']
links=[]
for page in pages:
    missing=[];checked=[]
    for ref in re.findall(r'(?:href|src)=["\']([^"\']+)',page.read_text()):
        if ref.startswith(('http:','https:','#','data:','mailto:')):continue
        path=(page.parent/ref.split('#')[0].split('?')[0]).resolve()
        checked.append(str(path.relative_to(PROJECT)))
        if not path.exists():missing.append(ref)
    links.append(dict(page=str(page.relative_to(PROJECT)),checked=checked,missing=missing))
assert not any(x['missing'] for x in links),links
http=[]
for path in [HERE/'index.html',HERE/'bridge_visible.png',HERE/'bridge_hidden.png',PARENT/'J10_A3_review/index.html']:
    url='http://127.0.0.1:58201/'+str(path.relative_to(PROJECT))
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as resp:
        http.append(dict(url=url,status=resp.status,content_type=resp.headers.get('Content-Type')))
assert all(x['status']==200 for x in http)

artifacts=list(HERE.glob('*.json'))+list(HERE.glob('*.py'))+list(HERE.glob('*.log'))+list(HERE.glob('*.png'))
artifacts += [HERE/'index.html',HERE/'REVIEW.md',HERE/'MORI_H01_H03_CANDIDATE_NOT_ADOPTED.blend']
artifacts += list((PARENT/'J10_A3_review').glob('*'))+[PARENT/'review_J10_A3.py',PARENT/'J10_A3_review.log',PARENT/'index.html',PARENT/'work_status.json',PARENT/'engineering_A2_mass_addendum.json']
files={str(p.relative_to(PROJECT)):sha(p) for p in artifacts if p.is_file() and p.name!='delivery.json'}
commands=[
    '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/check_static.py',
    '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/check_static.py -- --ecowire',
    '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_joint.py',
    '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/validate_candidate.py',
    '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/imu_candidates.py -- --ecowire',
    '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/render_candidate.py',
    '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/review_J10_C2.py',
    '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/review_J10_A3.py',
    'python3 mechanical/studies/prearrival_finish/harness_A2/publish.py',
    'python3 mechanical/studies/prearrival_finish/harness_A2/finalize_delivery.py']
delivery=dict(verified_utc=when,status='PASS',scope='Research artifact/source/link consistency only, not complete harness or manufacturing release',
    main_source_sha256=sha(main),main_geometry_changed=False,animation_changed=False,STL_changed=False,
    H01_H03_geometry='PASS',IMU_full_route='BLOCKED',J10_A3_complete_harness='BLOCKED',formal_board_PH_hole_correction='BLOCKED',
    adopted=False,files=files,received_A3_sources=review['sources'],local_link_checks=links,HTTP_checks=http,
    commands=commands,versions={'Blender':'5.2.2 LTS d13f752e3b9c','system_Python':'3.9.6','cad_Python':'3.12.14'},
    manufacturing_release=False)
(HERE/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n')
print('ADDENDUM_VERIFIED',len(files),'files',len(links),'pages',len(http),'HTTP objects',sha(main))
