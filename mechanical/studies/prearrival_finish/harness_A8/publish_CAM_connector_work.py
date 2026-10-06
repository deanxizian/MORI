"""Publish bounded work-access evidence and model-only routed-length datums."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,platform,re,shutil

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3];OUT=A8/'cam_connector_install'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
work=read(OUT/'work_access.json');lengths=read(OUT/'route_datums.json');render=read(OUT/'render_manifest.json')
assert work['status']==lengths['status']==render['status']=='PASS'
assert work['source_main_sha256']==lengths['source_main_sha256']==render['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
assert render['source_work_report_sha256']==sha(OUT/'work_access.json')
assert render['review_sha256']==sha(OUT/'review.blend')
for r in render['images']:assert r['sha256']==sha(OUT/r['file'])
preferred=next(r for r in work['rows'] if r['angle_about_tail_axis_deg']==180.)
assert preferred['bench']['status']=='PASS' and preferred['final_prescribed_loops']['status']=='BLOCKED'
assert work['service_fixture_levels']['open_head_on_robot']['status']=='BLOCKED'
assert work['service_fixture_levels']['detached_pitch_module_no_shells']['status']=='PASS'
assert lengths['pose_wire_instances']==520 and all(r['cut_length_mm'] is None for r in lengths['rows'])
length_table='\n'.join(f"| {r['geometry_slot']} | {r['body_pin_reference']} | {r['total_routed_model_mm']:.1f} | {r['datums'][2]['distance_from_body_exit_model_mm']:.1f} | {r['between_candidate_clamp_centres_model_mm']:.2f} | 未定 |" for r in lengths['rows'])
detail='CAM插头侧已补齐离机剪尾工具空间和四线模型长度基准。须先剪尾再整理线环；同一工具在装回机器人后被下方结构挡住。完整线束暂存、连接后的头部装拆、身体侧固定和其余7根头部导线/FPC仍未完成，裁线长度未放行；主模型保持M1.47。'
md=f'''# CAM线束：操作空间与长度基准

**本轮完成两项数字工作：离机操作空间、四根路线的模型长度基准。完整线束仍为 BLOCKED，主模型仍为 M1.47。**

## 固定之后怎样剪尾

沿用已检查的[短固定座候选](../cam_pitch_anchor/index.html)，本轮没有新增或修改打印结构。CAM板先插线再装到离机头托；扎带剪尾工具朝下摆放，从下方接近，最后才整理俯仰线环。

![离机剪尾位置](work_detail.png)

青色为候选固定座，黄色是插头/扎带的目录尺寸空间分配，绿色线框是参与碰撞计算的实体工具包络边缘。图中四色只用于区分几何路线，不代表电气针序；导线仍只显示Z200–214.6mm的临时局部直段。

| 检查 | 数字结果 | 范围 |
|---|---|---|
| 剪尾工具朝下、直线接近60mm | PASS | 扩大的钳头/手柄实体盒连续扫掠；与离机板卡/头托最小名义间距{preferred['fixture_only']['minimum_gap_below_5mm']['gap_mm']:.2f}mm，与局部直线导线{preferred['temporary_wires_only']['minimum_gap_below_5mm']['gap_mm']:.2f}mm |
| 扎带自由尾端工作区 | PASS | 所设6×110×2.7mm工作区，最近名义间距{work['tail_work_volume']['minimum_gap_below_5mm']['gap_mm']:.2f}mm；不代表手指空间或真实拉紧行程 |
| 工具朝上/横向 | BLOCKED | 与头托相交；仅排除本次工具分配和方向 |
| 斜向135° | 未采用 | 虽未相交，但对CAM板仅约0.09mm间距，继续采用向下方案 |
| 先形成最终线环再剪尾 | BLOCKED | 工具与既定线路的间隙检查失败，要求先剪尾、再理线 |
| 完整离机俯仰组件、拆下两片头壳 | 工具空间PASS | 包括光学支架及其硬件；不包括连接线束后的组件取出过程 |
| 留在机器人上、只拆头壳 | BLOCKED | 工具被偏航座、承重桥等下方结构挡住；不能声称可原位剪尾 |

![整把工具与自由尾端工作区](work_overview.png)

工具参考[已归档的KNIPEX79 22 125目录尺寸](../cam_tie_install/sources/dimensions.json)，采用扩大盒体，未选购工具，也不是厂家完整CAD。工具与扣头/带身的0.25mm名义切面偏置是设计工作位置，不是工具精度或允许残尾公差。实际钳口、手部、拉紧力、抓持和绝缘压伤仍未验证。

![原位操作失败](installed_tool_conflict.png)

## 四根模型路线的长度

测量基准是身体端Motion J5的**分配出线面**，沿当前规定曲线，到CAM目录/照片分配插头的**出线面**。表内含当前服务环，没有将端子内部长度、剥线长度或制造公差编成已知数值。

| 几何线号 | 身体端来源 | 全路线模型长度mm | 身体出线面至yaw夹持中心mm | 两夹持中心间模型长度mm | 实际裁线长度 |
|---|---|---:|---:|---:|---|
{length_table}

CAM夹持中心到其分配出线面均约2.60mm。两夹持中心之间约107.75mm，包含活动线环及相邻未被刚性导轨约束的曲段。

这次对13个yaw×10个pitch×4根线共520组保存曲线重新求长并检查接点，与来源模型长度差均小于0.003mm。该数值仅说明数字曲线一致；不是制造精度、实物线长公差或动态变形证明。

CAM侧实际针腔视图尚未确认，所以G1–G4只表示几何槽位，不是CAM pin1–4；不得据此接线。CSV文件有明确REFERENCE_ONLY标记，裁线列留空。

## 制作图与装配仍需要闭合的部分

目前J3穿装证据覆盖的是**先让未入胶壳的SH端子逐根穿过颈部**。它不支持把两端已装胶壳的整束直接穿过；也不能把相反方向的PH端子当作已验证。

已知顺序约束如下，并不是整束安装已经通过：

1. 逐根SH端子穿过颈部后，才完成头侧插壳；实际针腔视图及供货组装状态仍待定。
2. CAM插头先插板，再把板装到头托。
3. 离机操作、先剪扎带尾端，再整理最终线环。
4. 必须继续核对两个离机子组件之间的整段导线暂存、连接后的头部装入/取出，以及身体侧固定。

**不能把这些局部顺序直接串成一条已验证的整机装配流程。** 当前完整线束暂存和柔性穿紧仍为NOT_TESTED，CAM真实互配及端子端部修正量仍为BLOCKED。

裁线尺寸应由路线长度、两端带符号的端部基准修正及约定加工公差组成，不能直接把上表四个数字发给供应商裁线。供应商按图制作的路线已经确定，无需重复确认；目前没有联系供应商或发布加工订单。

## 文件

- [独立Blender](review.blend)、[工具及维修检查](work_access.json)。
- [长度和夹持基准报告](route_datums.json)、[长度表：仅模型参考](length_datums_REFERENCE_ONLY.csv)、[零位路线坐标：仅参考](route_reference_only.csv)。
- [原夹持座候选](../cam_pitch_anchor/index.html)、[原颈部端子穿装](../assembly_feed_v3/open_mouth/index.html)。
- [复现命令](commands.json)、[图像来源](render_manifest.json)、[交付记录](review_manifest.json)。

正式主模型、STL、装配动画和硬件文件均未修改。仍属PROTOTYPE / UNVALIDATED；所有PASS均限本页所述数字检查。
'''
(OUT/'README.md').write_text(md)
rows=''.join(f"<tr><td>{r['geometry_slot']}</td><td>{r['body_pin_reference']}</td><td>{r['total_routed_model_mm']:.1f}</td><td>{r['datums'][2]['distance_from_body_exit_model_mm']:.1f}</td><td>{r['between_candidate_clamp_centres_model_mm']:.2f}</td><td>未定</td></tr>" for r in lengths['rows'])
fig=lambda f,t:f'<figure><a href="{f}.png"><img src="{f}.png" alt="{t}"></a><figcaption>{t}</figcaption></figure>'
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM线束操作与长度基准</title>
<style>body{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f3f6f5;color:#243b3c;max-width:1080px;margin:32px auto;padding:0 24px 60px}h1{font-size:30px}a{color:#08727b}.note{padding:18px;background:#fff0d9;border-radius:8px}.done{padding:18px;background:#dfede6;border-radius:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{width:100%;border-radius:8px}figcaption{font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #ccd8d4}table{width:100%;border-collapse:collapse}.tablewrap{overflow:auto}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">当前未完成项</a> · <a href="../cam_pitch_anchor/index.html">固定座候选</a></p>
<h1>CAM线束：操作空间与长度基准</h1><p class="done">本轮补齐离机剪尾工具空间，并整理四根线的模型路线与夹持基准。没有新增打印结构。</p>
<p class="note">完整线束仍为BLOCKED。主模型M1.47未采用候选；表内路线长度不是裁线长度，整束暂存、装拆及其余头部线路仍需完成。</p>
<h2>先剪尾，再整理线环</h2><p>CAM先插线再上头托。钳子朝下摆放，在离机组件上从下方接近；随后整理俯仰线环。工具连续扫掠与板卡/头托名义间距2.14mm，与局部直线导线1.56mm。</p>
<div class="grid">'''+fig('work_detail','黄色：插头和扎带的目录空间分配；绿色：工具实体包络边缘；四色不是针序')+fig('work_overview','完整工具向下伸出；橙色长框为自由尾端工作区。未包含手部和整束松线')+'''</div>
<h2>维修限制也已经记入</h2><p>同一工具在机器人上操作会被偏航座等下方结构挡住。离机俯仰组件拆掉头壳后工具有空间，但连接整束线之后如何取下组件，尚未验证。先形成最终线环也会挡住当前工具，因此必须先剪尾。</p>'''+fig('installed_tool_conflict','失败示例：只拆头壳并不能给向下的工具腾出空间')+'''
<h2>模型长度表</h2><p>从Motion J5分配出线面沿既定路线量到CAM分配出线面。G1–G4为几何槽位；CAM实际针腔视图未定，不得按G编号接线。</p>
<div class="tablewrap"><table><tr><th>几何线号</th><th>身体端来源</th><th>模型全长mm</th><th>至yaw夹持中心mm</th><th>两夹持中心间mm</th><th>裁线长度</th></tr>'''+rows+'''</table></div>
<p>CAM夹持中心至出线面约2.60mm。13×10姿态、四根线共520组保存曲线与模型长度差小于0.003mm，只验证数字一致性；不是制造公差或动态弯折资格。</p>
<h2>相邻工序仍需衔接</h2><ol><li>现有颈部路线要求SH端子尚未入胶壳，逐根穿线后再装头侧插壳；两端已装胶壳整束穿装未验证。</li><li>先插CAM，再将板装到头托；再完成离机绑扎和剪尾。</li><li>整段导线暂存、连接后的头部装入/取出、身体侧固定及其他七根头部线和FPC仍未完成。</li></ol>
<p>供应商按图制作已经确定。终端基准修正和制造公差尚缺，CSV裁线列留空，不发加工订单。</p>
<p><a href="README.md">完整说明与检查边界</a> · <a href="review.blend">独立Blender</a> · <a href="work_access.json">操作检查</a> · <a href="route_datums.json">长度基准</a> · <a href="length_datums_REFERENCE_ONLY.csv">参考长度表</a> · <a href="route_reference_only.csv">参考路线坐标</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">交付记录</a></p></html>'''
(OUT/'index.html').write_text(html)
for origin,target in [('/tmp/mori_cam_connector_work_access.log','work_access.log'),('/tmp/mori_cam_route_datums.log','route_datums.log'),('/tmp/mori_cam_connector_work_render.log','render.log')]:
    shutil.copyfile(origin,OUT/target)
base='mechanical/studies/prearrival_finish/harness_A8/'
commands=['/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python '+base+'check_CAM_connector_work_access.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'prepare_CAM_route_datums.py',
 '/Applications/Blender.app/Contents/MacOS/Blender -b '+base+'cam_pitch_anchor/connector_anchor/review.blend -t 4 --python-exit-code 1 --python '+base+'render_CAM_connector_work.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'publish_CAM_connector_work.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'verify_delivery.py']
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':commands,'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':platform.python_version()},'main_applied':False},indent=2)+'\n')
status_path=PARENT/'work_status.json';status=read(status_path)
row=next(r for r in status['remaining'] if r['id']=='harness');old_detail=row['detail'];row.update(detail=detail,evidence='harness_A8/cam_connector_install/index.html')
status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_connector_install/index.html',CAM_connector_bench_tool='PASS',
 CAM_connector_tool_on_robot='BLOCKED',CAM_connector_route_length_datums='PASS',CAM_connector_work_review='harness_A8/cam_connector_install/index.html',
 CAM_supplier_cut_lengths='BLOCKED',CAM_whole_connected_installation='NOT_TESTED')
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';s=p.read_text();assert old_detail in s;s=s.replace(old_detail,detail).replace('harness_A8/cam_pitch_anchor/index.html','harness_A8/cam_connector_install/index.html').replace('最新：CAM插头固定座候选','最新：CAM操作空间与长度基准');p.write_text(s)
for p,link in [(A8/'index.html','cam_connector_install/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_connector_install/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_connector_install/index.html')]:
    s=p.read_text()
    if p==A8/'index.html':pat=r'<section id="threading-update">.*?</section>';block=f'<section id="threading-update"><h2>最新：CAM操作空间与长度基准</h2><p>{detail}</p><p><a href="{link}">操作图与长度基准</a>；下方保留历史阶段。</p></section>'
    else:
        a='<!-- A8_PITCH_FLEX_UPDATE -->';b='<!-- /A8_PITCH_FLEX_UPDATE -->';pat=re.escape(a)+'.*?'+re.escape(b);block=f'{a}<section><h2>CAM操作空间与长度基准</h2><p>{detail}</p><p><a href="{link}">操作图与长度基准</a></p></section>{b}'
    s,n=re.subn(pat,block,s,flags=re.S);assert n==1;p.write_text(s)
p=A8/'README.md';s=p.read_text();s,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->','<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM操作空间与长度基准](cam_connector_install/index.html)：离机剪尾工具和四线模型长度已补齐；完整线束与裁线仍未完成，主模型未采用。\n<!-- /A8_PITCH_FLEX_LATEST -->',s,flags=re.S);assert n==1;p.write_text(s)
files=[p for p in OUT.iterdir() if p.is_file() and p.name!='review_manifest.json' and not p.name.endswith('.blend1')]
manifest={'status':'PASS','scope':'Bounded work-access evidence and model-only length datums; not whole installation or manufacture',
 'script_sha256':sha(SCRIPT),'source_main_sha256':work['source_main_sha256'],'files':{str(p.relative_to(ROOT)):sha(p) for p in files},
 'images_visually_reviewed':True,'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('CAM_WORK_PUBLISHED',len(files),'files',flush=True)
