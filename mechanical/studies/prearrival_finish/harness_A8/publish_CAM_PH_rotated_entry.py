"""Publish bounded rigid-connector search evidence without assembly claims."""
from pathlib import Path
import json,hashlib,re
from datetime import datetime,timezone
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;P=A8.parent;ROOT=A8.parents[3]
OUT=P/'bridge_connector_rotation';OUT.mkdir(exist_ok=True)
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records={k:json.loads((BASE/k/'screen.json').read_text()) for k in ['PH_rotated_entry','PH_rotated_entry_fast']}
inputs={}
for k,script in [('PH_rotated_entry','plan_CAM_PH_rotated_entry.py'),('PH_rotated_entry_fast','plan_CAM_PH_rotated_entry_fast.py')]:
    r=records[k];assert r['script_sha256']==sha(A8/script) and r['helper_sha256']==sha(A8/'screen_CAM_bridge_wire_stock.py')
    assert r['status']=='BLOCKED' and r['stop']=='bounded_search_stopped' and r['path_states'] is None
    assert r['source_objects']==209 and r['present_source_objects']==122 and r['fixed_wire_solids']==14 and r['mating_allocations']==29
    assert len(r['rotation_matrices'])==24 and not r['main_applied'] and not r['manufacturing_release']
    for p in [BASE/k/'screen.json',A8/script,A8/'screen_CAM_bridge_wire_stock.py']:inputs[str(p.relative_to(ROOT))]=sha(p)
fast=records['PH_rotated_entry_fast'];assert fast['optimizer_base_sha256']==sha(A8/'plan_CAM_PH_rotated_entry.py')
assert all(not(q['fast_clear'] and not q['exact_clear']) for q in fast['exact_boolean_audits'])
protected=fast['protected_sources'];assert all(sha(ROOT/n)==h for n,h in protected.items())
rel='../harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
md=f'''# 身体端 PH 插头：带转动的独立路径诊断

状态 **BLOCKED：本轮限时搜索未找到完整路径**。这不证明无法装入，也不是实物适配结论。

前一版仅允许固定朝向平移。本轮允许 24 种正交朝向及 90° 转动，保留 122 件本装配阶段的真实源部件、29 个插接空间分配和全部 14 根既有身体导线。
偏航及俯仰总成按明确工序尚未安装。共同 PH 插头使用原有未实测的 9.8 × 4.5 × 6.85 mm 分配及 0.3 mm 余量；没有改小插头、移动电路板或移除障碍。

| 搜索 | 已展开状态 | 尚待搜索状态 | 结果 |
|---|---:|---:|---|
| 原闭合实体布尔检查 | 206 | 663 | 150 秒预算内未找到路径 |
| 凸体与 BVH 辅助检查 | 272 | 801 | 150 秒预算内未找到路径 |

初始轴向退出 8 mm 仍通过。后续阻挡包括 MCU、承重桥、已有插头和相邻身体导线。
辅助检查用 398 次实体布尔抽查核对，没有发现“辅助判空、实体相交”的抽查样本；2 次辅助检查保守拒绝。
这不能将未遍历的搜索空间判为失败，更不能证明所有转动、弯线或装配次序都不可行。

本轮只研究刚性插头空间，**四根相连 CAM 导线的供线、手部操作、真实插头朝向和厂家配合仍未验证**。
当前需要继续完成身体供线和分步装配设计；裁线图仍未放行。主模型未修改。

[布尔搜索记录]({rel}/PH_rotated_entry/screen.json) · [辅助检查记录]({rel}/PH_rotated_entry_fast/screen.json) · [完整线长与分步装配](../harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/split_assembly/index.html) · [总进度](../index.html)
'''
(OUT/'README.md').write_text(md)
table=''.join(f'<tr><td>{label}</td><td>{records[k]["expanded_nodes"]}</td><td>{records[k]["frontier_nodes"]}</td><td>预算内未找到路径</td></tr>' for k,label in [('PH_rotated_entry','闭合实体布尔'),('PH_rotated_entry_fast','凸体 / BVH 辅助')])
body=f'''<p>独立装配研究 · 未应用主模型</p><h1>身体端插头加入转动后，仍需继续找装配路径</h1><p>本轮保留 122 件阶段部件、29 个插接空间分配及 14 根既有身体导线，增加 24 种正交朝向。两次限时搜索都没有找到完整路径，不能据此判定无法安装。</p><table><tr><th>检查方法</th><th>已展开状态</th><th>剩余状态</th><th>结果</th></tr>{table}</table><p>轴向退出 8 mm 通过；后续涉及 MCU、承重桥及相邻导线。四根相连 CAM 线的完整供线与手部操作不在本次刚性插头检查内。</p><p>不改板位，不缩小插头，不放行裁线图。后续仍需完成供线和装配次序。</p><nav><a href="README.md">范围与数值说明</a><a href="{rel}/PH_rotated_entry/screen.json">布尔搜索记录</a><a href="{rel}/PH_rotated_entry_fast/screen.json">辅助检查记录</a><a href="../index.html">总进度</a></nav>'''
style='body{background:#f6f8f7;color:#263f46;font:17px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:960px;margin:auto;padding:40px 20px}h1{font-size:30px}table{width:100%;border-collapse:collapse;margin:30px 0}th,td{padding:12px;text-align:left;border-bottom:1px solid #ccd7d6}a{color:#187970}nav{display:flex;gap:20px;flex-wrap:wrap}'
(OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI 身体端插头路径</title><style>'+style+'</style><main>'+body+'</main></html>')
statuspath=P/'work_status.json';status=json.loads(statuspath.read_text());status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['CAM_body_connector_rotation']=dict(status='BLOCKED',scope='Bounded bare-housing path search, not impossibility proof',review='bridge_connector_rotation/index.html',expanded_nodes=[206,272],main_applied=False)
statuspath.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
idx=P/'index.html';doc=idx.read_text();section='<section id="cam-connector-rotation"><h2>身体端插头转动路径</h2><p><a href="bridge_connector_rotation/index.html">查看本轮范围与结果</a>：保留14根身体导线，增加24种正交朝向。限时搜索暂未找到完整路径；完整供线与装配次序仍需继续完成。</p></section>'
doc=re.sub(r'<section id="cam-connector-rotation">.*?</section>','',doc,flags=re.S);assert '</main>' in doc;idx.write_text(doc.replace('</main>',section+'</main>'))
pub=dict(status='PASS',scope='Publication and source validation, not assembly approval',script_sha256=sha(SCRIPT),source_files=inputs,protected_sources=protected,
 outputs={n:sha(OUT/n) for n in ['README.md','index.html']},search_result='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'publication.json').write_text(json.dumps(pub,ensure_ascii=False,indent=2)+'\n')
print('PH_ROTATION_REVIEW_PUBLISHED')
