"""Publish source evidence and clearly separate individual routes from packing."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
SCRIPT=Path(__file__).resolve();HERE=SCRIPT.parent;OUT=HERE/'cam_pitch_flex';PARENT=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pool=read(OUT/'side/flex_pool.json');packing=read(OUT/'side/packing.json');math=read(OUT/'side/math_bounds.json')
diag=read(OUT/'side/full_pair_diagnostic.json');early=read(OUT/'early_turn/screen.json');render=read(OUT/'render_manifest.json')
photo_path=ROOT/'hardware/v1_2/cam_uart_photo_review_20261003/evidence.json';photo=read(photo_path)
assert pool['status']==math['status']==early['status']=='PASS'
assert packing['status']==diag['status']=='BLOCKED' and not packing['simultaneous_assignments']
assert len(packing['rows'])==19 and all(r['status']=='PASS' for r in packing['rows'])
assert photo['official_photo_position_status']==photo['electrical_map_correspondence']=='PASS'
assert photo['actual_header_mpn'] is None and photo['manufacturing_status']=='BLOCKED'
assert sha(ROOT/'mechanical/mori_v1_2.blend')==pool['source_main_sha256']
maximum_length_error=max(p['maximum_constant_length_error_bound_mm'] for r in math['rows'] for p in r['poses'])
source_receipt={'received_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS',
    'source':str(photo_path.relative_to(ROOT)),'source_sha256':sha(photo_path),
    'photo_sha256':photo['photo_sha256'],'photo_board_face_position':'PASS','logical_pin_correspondence':'PASS',
    'recorded_zero_pose_slot_to_logic':[1,2,3,4],'slot_evidence':'ASSUMED_MODEL_INFERENCE',
    'actual_header_mpn':'BLOCKED','actual_mating_cavity_views':'BLOCKED','physical_continuity':'NOT_TESTED',
    'formal_pinmap_or_hardware_changed':False}
(OUT/'photo_receipt.json').write_text(json.dumps(source_receipt,ensure_ascii=False,indent=2)+'\n')
detail=('已补齐官方照片中的CAM板端UART位置，硬件复核与现有逻辑针序一致；实际插座料号及线端针腔视图仍未确认。'
    '四根UART各自已有连接两端的恒长候选，19条单线的实体、全线自交和既有前缀检查通过；整束组合仍未达到0.3mm间隔要求。'
    '已定位抬头25°时首根线上行段靠近CAM末根出线，提前R7侧弯的局部候选通过，尚未接回整束。固定点、整束装入和最终下料长度仍需设计；主模型未改。')
md=f'''# 公开资料与头部活动线：已取得什么、设计还差什么

**完整线束 BLOCKED，主模型与装配视频没有替换。本页是设计研究，不是可交厂加工的图纸。**

## 公开资料已由项目查证

| 内容 | 来源与结果 | 仍不能据此确认 |
|---|---|---|
| SH、PH连接器外形与适用线径 | [JST SH](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)、[JST PH](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf) | CAM实际采用的完整原厂料号 |
| 完整端子料号的压接参考 | [逐料号查询与新旧差异](../TOOLING_DETAILS.md) | 实际线材、工具、版本组合的工艺资格；查询来自test-jst公开主机 |
| CAM板端UART位置 | [硬件照片复核](../../../../../hardware/v1_2/cam_uart_photo_review_20261003/README.md) | 正对插合面的实际针腔图及线端镜像视图 |

官方照片芯片面正视、Type-C朝下时，UART上方左→右为 **GND、3V3、TXD、RXD**，对应现有逻辑4、3、2、1。
该照片在当前零姿态模型中的位置映射给出slot0..3→逻辑1..4，证据等级仍是**ASSUMED推断**，没有改正式针序。[只读接收记录](photo_receipt.json)。

“供应商按图制作”已经确认。公开器件资料由项目查找；路线、固定位置、分支与长度基准也必须由项目设计，不能以此交回用户或归为等待实物。

## 本次活动线路检查

从Z193临时偏航分段点连接到CAM端，建立保持长度的两段Bezier活动曲线。先保留向前出线的失败记录，再检查向左出线。
四根线合计19条单线候选，在130个组合姿态下通过源实体检查；拼接原身体前缀与CAM端后，自身和其他原前缀检查通过。
用De Casteljau细分及凸包界检查各Bezier段的全参数弯曲与长度；十个俯仰角度下，最大长度偏差上界为{maximum_length_error:.7f} mm。
这覆盖的是曲线参数，不是角度采样之间的连续运动，也不是实物导线会自然保持这些形状的证明。6.9342 mm是本轮筛选半径，不是线材动态寿命承诺。

**整束检查没有通过。**对现有候选池的所有组合，尚未找到四根线同时满足0.3 mm表面间隔的路线。最优组合的最小间隙下界约{diag['best_combination_for_review']['minimum_surface_gap_bound_mm']:.4f} mm；未降低间隔要求，也没有把单线通过当作整束通过。

![零位，显示未通过的整束候选](zero.png)
![抬头25度，显示同一未通过的整束候选](tightest.png)

图中只显示CAM、两只舵机与俯仰U托，其余实体为看清线路暂时隐藏；实体检查包含它们。四色为几何路径。此图不是固定点设计，导线当前没有按该姿态的真实保持件。[独立Blender检查副本](comparison.blend)。

## 已定位一个原因并验证局部调整

最紧的一对出现在抬头25°：首根线上行段靠近CAM末根固定出线。其位置在颈部暂存点以上几毫米，并不是上方大线环末端的随机交叉。
在原起点保留+Z切向，增加两个R7圆弧提前向+X侧弯，终点仍为+Z切向。局部候选与源实体、四个原身体前缀及四条CAM固定出线的名义检查通过；CAM端最小间隙下界{early['minimum_head_tail_gap_bound_mm']:.3f} mm。
该局部调整**尚未接回完整活动线**，也未解决其他线对间隔或固定问题。[局部结果](early_turn/screen.json)。

下一步应先重新衔接这个起点并检查四根线共同的活动区域，避免继续只优化互不相关的单线大环。之后完成固定点、装入顺序、照片误差包络、其余七根头部活动导线及FPC，才有条件给完整长度。

## 复现与边界

- [单线池](side/flex_pool.json)、[拼接与整束检查](side/packing.json)、[完整曲线数学界](side/math_bounds.json)、[每个线对的所有姿态](side/full_pair_diagnostic.json)。
- [首轮向前出线失败](flex_pool.json)、[小幅调整仍失败的记录](bundle/flex_pool.json)均保留；有限曲线族失败不表示所有路线无解。
- [图像来源](render_manifest.json)、[命令](commands.json)、[本页来源](review_manifest.json)。
- 配套舵盘、实际端子/线材/插合、PA12配合、固定强度、弯折寿命及整机性能的原限制保持。
'''
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 资料查证与活动线束</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f3f6f5;color:#2b4246;max-width:1120px;margin:32px auto;padding:0 24px 60px}}a{{color:#086f78}}.note{{background:#fff0d9;padding:18px 22px}}.images{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}figure{{margin:0}}img{{width:100%;border-radius:8px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:12px;border-bottom:1px solid #cdd9d7;text-align:left}}@media(max-width:720px){{.images{{grid-template-columns:1fr}}}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">完整项目状态</a></p><h1>公开资料已补查，活动线束继续设计</h1>
<p class="note">完整线束仍为BLOCKED。主模型、STL和装配视频未改；本页不能作为下料或加工图。</p>
<h2>哪些已经查到</h2><table><tr><th>资料</th><th>证据</th></tr><tr><td>SH、PH尺寸与适用线径</td><td><a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">JST SH</a> · <a href="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf">JST PH</a></td></tr><tr><td>完整端子料号压接参考</td><td><a href="../TOOLING_DETAILS.md">逐料号结果和版本限制</a></td></tr><tr><td>CAM板端UART位置</td><td>官方照片左→右GND、3V3、TXD、RXD，与逻辑4、3、2、1一致；<a href="../../../../../hardware/v1_2/cam_uart_photo_review_20261003/README.md">硬件已复核</a></td></tr></table>
<p>实际插座完整料号、正对插合面的针腔图及线端镜像视图仍未确认。当前零位模型的slot0..3→逻辑1..4只是照片配准推断，不改正式针序。</p>
<p>供应商按图制作已经确定。公开资料由项目查找；路线、固定点、分支与长度也由项目完成。</p>
<h2>路线进展与实际卡点</h2><p>{detail}</p>
<div class="images"><figure><img src="zero.png" alt="零位的未通过整束候选，四条路径跨过两只舵机"><figcaption>零位，候选未采用</figcaption></figure><figure><img src="tightest.png" alt="抬头25度的未通过整束候选"><figcaption>抬头25°，四根线仍需共同调整</figcaption></figure></div>
<p>为了查看线路，图中隐藏了部分支架与外壳；检查包含源实体。图中的大线环没有真实保持件，不能把规定的曲线当成自然运动形状。</p>
<table><tr><th>检查</th><th>当前结果</th></tr><tr><td>19条单线：有限姿态实体、全线自交、原前缀间隔</td><td>PASS，尚非整束</td></tr><tr><td>曲线全参数长度与弯曲界</td><td>PASS；十个俯仰角，非连续角度运动或寿命验证</td></tr><tr><td>四根线同时满足0.3mm间隔</td><td>BLOCKED；保留失败结果</td></tr><tr><td>首根线提前R7侧弯</td><td>局部PASS；与CAM端最小间隙下界{early['minimum_head_tail_gap_bound_mm']:.3f}mm，尚未接回整束</td></tr><tr><td>固定点、整束装入、最终长度</td><td>仍需设计</td></tr></table>
<p><a href="README.md">完整说明</a> · <a href="photo_receipt.json">照片证据接收</a> · <a href="side/packing.json">整束检查</a> · <a href="side/math_bounds.json">长度与弯曲界</a> · <a href="side/full_pair_diagnostic.json">具体间距位置</a> · <a href="early_turn/screen.json">提前侧弯</a> · <a href="comparison.blend">检查副本</a> · <a href="commands.json">命令</a> · <a href="review_manifest.json">来源</a></p></html>'''
(OUT/'index.html').write_text(html)
status_path=PARENT/'work_status.json';status=read(status_path)
old_detail=next(x['detail'] for x in status['remaining'] if x['id']=='harness') if 'remaining' in status else None
# Find the actual top-level list without assuming unrelated status key names.
old_detail=None
for value in status.values():
    if isinstance(value,list):
        for row in value:
            if isinstance(row,dict) and row.get('id')=='harness':
                old_detail=row['detail'];row['detail']=detail;row['evidence']='harness_A8/cam_pitch_flex/index.html'
assert old_detail is not None
latest=status['A8_harness_research'];latest.update({
    'latest_review':'harness_A8/cam_pitch_flex/index.html','CAM_yaw_pitch_service_loop':'BLOCKED',
    'CAM_individual_constant_length_routes':'PASS','CAM_full_bezier_bounds_at_finite_poses':'PASS',
    'CAM_whole_four_wire_packing':'BLOCKED','CAM_early_local_S_turn':'PASS','CAM_early_turn_full_rejoin':'NOT_TESTED',
    'CAM_board_face_photo_position':'PASS','CAM_actual_mating_cavity_view':'BLOCKED',
    'CAM_photo_evidence_receipt':'harness_A8/cam_pitch_flex/photo_receipt.json','CAM_route_applied':False})
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';text=p.read_text();assert old_detail in text;text=text.replace(old_detail,detail)
text=text.replace('<a href="harness_A8/cam_pitch_port/index.html">','<a href="harness_A8/cam_pitch_flex/index.html">')
p.write_text(text)
for p,link in [(HERE/'index.html','cam_pitch_flex/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_pitch_flex/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_pitch_flex/index.html')]:
    text=p.read_text()
    if p==HERE/'index.html':
        block=f'<section id="threading-update"><h2>最新：板端照片已复核，活动线束在整束检查中</h2><p>{detail}</p><p><a href="{link}">资料、实际卡点和候选图</a>。下方保留历史阶段。</p></section>'
        text,n=re.subn(r'<section id="threading-update">.*?</section>',block,text,flags=re.S);assert n==1
    else:
        marker='<!-- A8_PITCH_FLEX_UPDATE -->';end='<!-- /A8_PITCH_FLEX_UPDATE -->'
        block=f'{marker}<section><h2>CAM资料与活动线束更新</h2><p>{detail}</p><p><a href="{link}">查看结果与仍需设计的部分</a></p></section>{end}'
        if marker in text:text=re.sub(re.escape(marker)+'.*?'+re.escape(end),block,text,flags=re.S)
        else:text=text.replace('</html>',block+'</html>')
    p.write_text(text)
commands={'cwd':str(ROOT),'separate_Blender_processes_required':True,
    'commands':[f'"/Applications/Blender.app/Contents/MacOS/Blender" -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/{s}' for s in [
        'inspect_pitch_routing_space.py','plan_cam_pitch_flex.py','plan_cam_pitch_flex_side.py','check_cam_pitch_flex_packing.py','refine_cam_pitch_flex_bundle.py','diagnose_pitch_flex_pairs.py','check_pitch_early_turn.py']]+[
        '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/audit_cam_pitch_flex_math.py',
        '"/Applications/Blender.app/Contents/MacOS/Blender" -b mechanical/studies/prearrival_finish/harness_A8/assembly_feed_v3/open_mouth/cleaned/candidate.blend -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/render_pitch_flex_review.py'],
    'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','CAD_Python':'3.12.14'},
    'execution_notes':['Initial diagnostic output used a helper-overwritten directory; correct source/result regenerated, initial copy retained.',
        'First packing execution was stopped to remove repeated remote/self queries; same conservative criteria retained.',
        'First completed packing run failed JSON serialization of NumPy sample indices; typed indices fixed and full run repeated successfully.',
        'check_cam_pitch_bundle.py was prepared but not run: its required refined-pool PASS is not met.']}
(OUT/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
files=[OUT/n for n in ['index.html','README.md','photo_receipt.json','commands.json','side/flex_pool.json','side/packing.json','side/math_bounds.json','side/full_pair_diagnostic.json','bundle/flex_pool.json','early_turn/screen.json','render_manifest.json','zero.png','tightest.png','comparison.blend']]
manifest={'status':'PASS','scope':'Source-backed independent review publication, not harness qualification',
    'source_script_sha256':sha(SCRIPT),'source_main_sha256':pool['source_main_sha256'],
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
    'images_visually_reviewed':True,'files':{str(p.relative_to(ROOT)):sha(p) for p in files}}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('PITCH_FLEX_REVIEW_PUBLISHED',flush=True)
