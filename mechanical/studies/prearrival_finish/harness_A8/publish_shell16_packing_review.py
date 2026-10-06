"""Publish finite assembly investigations without changing the main model."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,platform

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
STOCK=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
ORDER=STOCK/'install_order';OUT=ORDER/'shell16_packing_diagnosis'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
inputs={}

def receive(p,script):
    d=read(p);assert d['script_sha256']==sha(A8/script),script
    for q in [p,A8/script]:inputs[str(q.relative_to(ROOT))]=sha(q)
    for name,h in d.get('source_files',{}).items():
        assert sha(ROOT/name)==h,name;inputs[name]=h
    for name,h in d.get('protected_sources',{}).items():assert sha(ROOT/name)==h,name
    for name,h in d.get('outputs',{}).items():
        q=p.parent/name;assert sha(q)==h,name;inputs[str(q.relative_to(ROOT))]=h
    if 'curves_sha256' in d:
        q=p.parent/'curves.npz';assert sha(q)==d['curves_sha256'];inputs[str(q.relative_to(ROOT))]=sha(q)
    return d

d=receive(OUT/'diagnosis.json','diagnose_shell16_wire_packing.py')
plot=receive(OUT/'plot.json','plot_shell16_wire_packing.py')
detour=receive(ORDER/'shell16_second_wire_detour/screen.json','search_shell16_second_wire_detour.py')
early=receive(ORDER/'shell16_early_wire_planes/screen.json','search_shell16_early_wire_planes.py')
splay=receive(ORDER/'shell16_temporary_tail_splay/screen.json','screen_shell16_temporary_tail_splay.py')
refined=receive(ORDER/'shell16_refined_tail_splay/screen.json','screen_shell16_refined_tail_splay.py')
small=receive(ORDER/'shell16_small_tail_splay/screen.json','screen_shell16_small_tail_splay.py')
precise=receive(ORDER/'shell16_splay_clearance/diagnosis.json','diagnose_shell16_splay_clearance.py')
closed=receive(STOCK/'PH_rotated_entry_extended/screen.json','extend_CAM_PH_rotated_entry.py')
opened=receive(STOCK/'PH_shell16_entry/screen.json','plan_CAM_PH_shell16_entry.py')
deferred=receive(STOCK/'PH_shell16_deferred_entry/screen.json','plan_CAM_PH_shell16_deferred_entry.py')
waypoints=receive(STOCK/'PH_shell16_waypoints/screen.json','screen_CAM_PH_shell16_waypoints.py')
deferred_waypoints=receive(STOCK/'PH_shell16_deferred_waypoints/screen.json','screen_CAM_PH_shell16_deferred_waypoints.py')
stepped=receive(STOCK/'PH_shell16_stepped_entry/screen.json','screen_CAM_PH_shell16_stepped_entry.py')
stepcheck=receive(STOCK/'PH_shell16_stepped_entry/verification.json','verify_CAM_PH_shell16_stepped_entry.py')
stepplot=receive(STOCK/'PH_shell16_stepped_entry/plot.json','plot_CAM_PH_shell16_stepped_entry.py')
assert stepped['status']==stepcheck['status']==stepplot['status']=='PASS'
assert stepcheck['source_screen_sha256']==sha(STOCK/'PH_shell16_stepped_entry/screen.json')
exit_leads=receive(STOCK/'PH_shell16_stepped_entry/exit_leads.json','check_CAM_PH_stepped_exit_leads.py')
assert exit_leads['status']=='PASS' and len(exit_leads['rows'])==4
assert all(len(r['segments'])==6 and r['status']=='PASS' for r in exit_leads['rows'])
assert stepcheck['continuous_translation_segments']==7
assert d['status']==plot['status']==precise['status']=='PASS'
assert detour['status']==early['status']==splay['status']==refined['status']==small['status']=='BLOCKED'
assert all(not x['main_applied'] and not x['manufacturing_release'] for x in [d,detour,early,splay,refined,small,precise,closed,opened])
assert detour['configurations']==171 and len(early['packing'])==36
assert sum(r['status']=='PASS' for r in early['packing'])==6
p4=next(r for r in precise['rows'] if r['tail_yaw_deg']==4.)
assert p4['status']=='FAIL' and p4['result']['surface_gap_upper_bound_mm']<.3
link=lambda p:os.path.relpath(p,OUT)
open_result=('找到裸插头的有限路径，仍需复核所选路径、连接的四根线、工具和后续收线。'
             if opened['status']=='PASS' else
             f"搜索展开{opened['expanded_nodes']}个状态后仍未找到完整路径；保留{opened['frontier_nodes']}个待搜索状态，不代表不存在路径。")
rows=[
 ('分两次升高，经上方开口接入PH','裸胶壳7段平移的封闭实体扫掠复核通过；保留0.3mm预留，初始8mm插合段有已记录的原生配合例外。四根线前5mm直段另有24段扫掠通过；余下柔性导线尚未验证。',link(STOCK/'PH_shell16_stepped_entry/verification.json')),
 ('CAM2局部绕开CAM1',f"检查171种配置、展开18个可达状态，所选控制范围内未连到目标。",'../shell16_second_wire_detour/screen.json'),
 ('提前调整导线高度',f"12个单线候选的抬升通过；36种四线组合中6种通过抬升，但继续后移都未通过。",'../shell16_early_wire_planes/screen.json'),
 ('临时扭开自由线尾',f"3°、3.5°局部对桥间隙通过，但四线合并仍未通过；4°时对桥的表面间隙上界约{p4['result']['surface_gap_upper_bound_mm']:.3f}mm，已低于0.3mm目标。",'../shell16_splay_clearance/diagnosis.json'),
 ('关闭上壳时插PH',f"同一插头和障碍物下，延长至600秒，展开{closed['expanded_nodes']}状态，仍未找到完整路径。",link(STOCK/'PH_rotated_entry_extended/screen.json')),
 ('保持上壳打开后插PH',open_result,link(STOCK/'PH_shell16_entry/screen.json')),
 ('H01/H04延后，再插PH',('裸胶壳路径找到；H01/H04的10根线和4个插头明确延后，其后带线装入仍未完成。' if deferred['status']=='PASS' else f"展开{deferred['expanded_nodes']}状态后未找到完整路径；H01/H04明确延后，不能据此省略后装验证。"),link(STOCK/'PH_shell16_deferred_entry/screen.json')),
]
commands=[]
for script,log in [
 ('diagnose_shell16_wire_packing.py','shell16_packing_diagnosis.log'),
 ('search_shell16_second_wire_detour.py','shell16_second_wire_detour.log'),
 ('search_shell16_early_wire_planes.py','shell16_early_wire_planes.log'),
 ('screen_shell16_temporary_tail_splay.py','shell16_temporary_tail_splay.log'),
 ('screen_shell16_refined_tail_splay.py','shell16_refined_tail_splay.log'),
 ('diagnose_shell16_splay_clearance.py','shell16_splay_clearance.log'),
 ('screen_shell16_small_tail_splay.py','shell16_small_tail_splay.log'),
 ('extend_CAM_PH_rotated_entry.py','CAM_PH_rotated_entry_extended.log'),
 ('plan_CAM_PH_shell16_entry.py','PH_shell16_entry.log'),
 ('plan_CAM_PH_shell16_deferred_entry.py','PH_shell16_deferred_entry.log'),
 ('screen_CAM_PH_shell16_waypoints.py','PH_shell16_waypoints.log'),
 ('screen_CAM_PH_shell16_deferred_waypoints.py','PH_shell16_deferred_waypoints.log'),
 ('screen_CAM_PH_shell16_stepped_entry.py','PH_shell16_stepped_entry.log'),
 ('verify_CAM_PH_shell16_stepped_entry.py','PH_shell16_stepped_verification.log'),
 ('check_CAM_PH_stepped_exit_leads.py','PH_shell16_exit_leads.log'),
]:
    lp=A8.parent/'verification_logs'/log
    assert lp.is_file();inputs[str(lp.relative_to(ROOT))]=sha(lp)
    commands.append(dict(command='/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 2 --python mechanical/studies/prearrival_finish/harness_A8/'+script,
                         log=str(lp.relative_to(ROOT)),exit_code=0))
md=f'''# 新增上方PH插接路径，完整带线装配仍未完成

新增一条裸PH胶壳从上方开口接入的明确路径，7段平移用封闭实体的连续扫掠复核通过。
![上方接入路径]({link(STOCK/'PH_shell16_stepped_entry/path.png')})

这条路径采用H02/H03先装、H01/H04延后的顺序，桥已经就位，上壳保持16°/+14mm。四根导线最前5mm直段另有24段扫掠通过（不含最终8mm插合段），余下柔性导线与完整工序仍未通过。

主模型M1.47没有修改。本页记录装配候选的诊断与比较；不是制造放行。

![导线局部间隙](local_pairs.png)

## 两处卡点

- 颈部：CAM2中段下移时靠近CAM1的上升段，原有限采样的保守表面间隙约0.030mm。
- 身体插头旁：CAM3的转弯靠近CAM4，原保守间隙约0.173mm。

研究采用0.6604mm导线外径、0.3mm预留。图线是中心线；这两个下界不是实际最小间隙，也不能一概当作实体相交。

## 已比较的方向

'''
for title,detail,url in rows:md+=f'- **{title}**：{detail} [原始结果]({url})\n'
md+='''
临时扭线的数值检查保留原圆弧误差，对边缘结果细分原弦线，并对桥表面的距离另做下界/上界检查。
没有通过缩小导线、插头、降低0.3mm预留或删去障碍物来消除问题。
3.5°只是本次测试的一个局部可行角度，不是全局最大角度，也不是完整动作通过。

## 打开上壳后插接的范围

上壳组保持16°、上抬14mm，固定承重桥位于装好位置；29个其他插接空间及14根固定身体线继续参与，H02使用已经记录的新走向。
这次目标改为机身右侧外部空间，PH胶壳不必穿颈孔。上壳、后板插头作为一个整体变换。
另作一个顺序候选：H02/H03先装、H01/H04延后；暂不装入的10根导线和4个插头逐项列在报告中，之后仍必须检查其装入过程。
此检查只有裸PH胶壳的既有保守包络，四根CAM导线尚未随胶壳检查；真实插合、手部空间和连接后收线仍待完成。

## 接下来仍可在到货前做的事

继续选择可执行的装配顺序，并把身体端插接、完整导线和头部装入一起衔接；随后处理H01/H04、其余跨关节线与FFC、扎带和工具。
当前失败仅限所列参数族、网格和搜索时长，不能据此宣布所有方式都不可行。
供应商按图制作已确定；公开原厂资料继续作为来源。具体配套端子/线尾/舵盘未公开的尺寸仍要厂家回复，最终裁线图尚未放行。

[此前四段刚体和前两段含线检查](../shell16_joint_feed/index.html) · [本次来源与命令](publication.json)
'''
(OUT/'README.md').write_text(md)
body=''.join(f'<tr><td>{title}</td><td>{detail}</td><td><a href="{url}">记录</a></td></tr>' for title,detail,url in rows)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MORI · CAM线装配卡点</title><style>body{{font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif;max-width:1140px;margin:auto;padding:24px;color:#24404a;background:#f2f6f6}}section{{background:white;padding:24px;margin:18px 0;border-radius:12px}}a{{color:#076b80}}img{{width:100%;height:auto}}.note{{background:#fff0d8}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #d6e2e6}}td:first-child{{min-width:150px}}</style>
<p><a href="{link(A8/'supplier_source_update/index.html')}">← 资料与设计进度</a></p><h1>上方插头路径已找到，继续补齐带线装配</h1>
<section class="note"><p>找到裸PH插头从上方开口接入的7段路径，封闭实体扫掠复核通过；两处原线间问题也已定位。四根导线随插头移动仍待检查，主模型M1.47未改，裁线图未放行。</p></section>
<section><h2>新找到：上方开口的7段平移路径</h2><p>裸PH胶壳的封闭实体扫掠复核通过，外形未缩小，仍加0.3mm预留。采用H02/H03先装、H01/H04延后的顺序；四根线最前5mm直段有24段扫掠通过，余下柔性导线随胶壳移动尚未检查。</p><a href="{link(STOCK/'PH_shell16_stepped_entry/path.png')}"><img src="{link(STOCK/'PH_shell16_stepped_entry/path.png')}" alt="PH胶壳从上方开口进入，经两段高度调整后插入板端的三维源模型投影"></a></section>
<section><h2>原先带线后移的两个局部问题</h2><a href="local_pairs.png"><img src="local_pairs.png" alt="CAM1与CAM2在颈部靠近；CAM3与CAM4在身体插头旁靠近；三向中心线投影"></a><p>两处原采样的保守表面间隙分别约0.030和0.173mm，未达到本研究0.3mm预留。下界不等于实际最小间隙，未达到目标也不一概等于实体相交。</p></section>
<section><h2>已经比较的方向</h2><table><thead><tr><th>方案</th><th>本次结果及边界</th><th>证据</th></tr></thead><tbody>{body}</tbody></table><p>导线外径0.6604mm、目标预留0.3mm保持。局部扭开3.5°并不代表整段动作或四根线一起通过；4°的间隙不足另外用距离上界确认。</p></section>
<section><h2>新顺序：承重桥就位后，保持上壳打开再插身体端</h2><p>上壳保持16°、抬高14mm，桥在安装位置，目标是机身右侧外部空间。固定身体线、后板插头和上壳实体保留；这次没有要求PH胶壳穿颈孔。</p><p>{open_result} 这里只检查裸胶壳的既有包络，四根CAM线随插头的移动、真实插合、手部和工具仍未验证。</p></section>
<section class="note"><h2>还不能归为“只等实物”</h2><p>完整带线装配顺序、H01/H04、其他跨关节线和FFC、扎带与工具仍是待完成的设计。受限搜索失败不能证明所有方式都不可行。</p><p>供应商按图制作已确定；最终线长和制作图需要装配路线收敛后再确定。</p><p><a href="README.md">详细说明</a> · <a href="publication.json">来源、命令和工具版本</a> · <a href="../shell16_joint_feed/index.html">此前已经通过的局部检查</a></p></section></html>'''
(OUT/'index.html').write_text(html)
report=dict(status='PASS',scope='Verified publication of diagnostic outcomes; assembly not complete',
    generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),source_files=inputs,
    protected_sources=d['protected_sources'],outputs={n:sha(OUT/n) for n in ['README.md','index.html','local_pairs.png']},
    commands=commands,versions=dict(blender='5.2.2 LTS d13f752e3b9c',publisher_python=platform.python_version()),
    stepped_PH_rigid='PASS',stepped_PH_segments=7,stepped_PH_first5mm_leads='PASS',stepped_PH_lead_segments=24,stepped_PH_wires='NOT_TESTED',
    wire_pair_diagnosis='PASS',local_detour=detour['status'],early_four_wire_path=early['status'],
    splay_four_wire_path=small['status'],closed_PH_rigid=closed['status'],open_PH_rigid=opened['status'],
    open_PH_expanded_nodes=opened['expanded_nodes'],deferred_PH_rigid=deferred['status'],complete_attached_assembly='BLOCKED',
    main_applied=False,manufacturing_release=False,physical_validation='NOT_TESTED')
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
state_path=A8.parent/'work_status.json';state=read(state_path)
state['CAM_shell16_packing_diagnosis']=dict(publication=str((OUT/'publication.json').relative_to(A8.parent)),
    publication_sha256=sha(OUT/'publication.json'),stepped_PH_rigid='PASS',stepped_PH_segments=7,stepped_PH_first5mm_leads='PASS',local_diagnosis='PASS',four_wire_rear_motion='BLOCKED',
    open_shell_late_PH_rigid=opened['status'],deferred_PH_rigid=deferred['status'],complete_attached_assembly='BLOCKED',main_applied=False)
for item in state['remaining']:
    if item['id']=='harness':
        item['latest_packing_evidence']=str((OUT/'index.html').relative_to(A8.parent))
        item['latest_packing_detail']='新增上方开口PH裸胶壳7段平移路径，封闭实体扫掠复核通过，前5mm出线直段24段扫掠通过；四根CAM余下柔性导线随动仍待检查。已定位颈部CAM1/2及身体端CAM3/4的局部间隙问题；提前降线和临时扭线未使四线后移通过。打开上壳后后接PH的裸胶壳结果：'+opened['status']+'；H01/H04延后方案：'+deferred['status']+'。完整带线顺序和制造图仍未完成。'
state['updated_utc']=report['generated_utc'];state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print('PACKING_REVIEW_PUBLISHED stepped PH PASS; earlier side search',report['open_PH_rigid'],'complete assembly BLOCKED')
