"""Publish connected nominal UART paths without releasing a physical harness."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

SCRIPT=Path(__file__).resolve(); HERE=SCRIPT.parent; OUT=HERE/'cam_fan_in'
PARENT=HERE.parent; ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
loop=read(OUT/'short_tail_v2/screen.json'); lpack=read(OUT/'short_tail_v2/packing.json')
lmath=read(OUT/'short_tail_v2/math_bounds.json'); pool=read(OUT/'four_bend_transition/pool.json')
pack=read(OUT/'four_bend_transition/packing.json'); math=read(OUT/'four_bend_transition/math_bounds.json')
joins=read(OUT/'joins.json'); render=read(OUT/'render_manifest.json')
assert all(r['status']=='PASS' for r in [loop,lpack,lmath,pool,pack,math,joins,render])
assert sha(ROOT/'mechanical/mori_v1_2.blend')==pack['source_main_sha256']
assert len(pack['assignments'])==81 and len(pack['individual_replay'])==12
gap=lpack['rows'][0]['minimum_mutual_gap_bound_mm']
fan_gap=min(r['gap_bound_mm'] for r in pack['pairs'])
upper_r=lmath['rows'][0]['upper_radius']['lower_mm']
detail=('身体到CAM的四条名义导线路径已连通：新增颈部到俯仰线环的过渡，四线同时存在的间隙检查通过；'
        '各过渡均重放源实体、线环和身体线段检查，覆盖130个组合姿态，1560处接点一致。'
        '名义线间隙下界约0.306mm，线环整段长度/半径已有解析界；碰撞仍是姿态采样。'
        '真实固定、完整装入、其余七根头部导线和相机FPC仍未完成，实际CAM插合件未定。'
        '此为未采用的独立候选；主模型未改，不能下发加工线长。')

md=f'''# 身体到 CAM：四条名义导线路径接通

**本轮完成过渡连接和四线共同排布。完整线束仍为 BLOCKED，主模型保持 M1.47。**

身体侧原路线在颈部 Z193 mm 接出，经各自的过渡进入 Z230 mm 的俯仰线环。相机端原有直段仅缩短2.5mm，之前的曲线和插头出线直段保留。四条路线现在首尾相接，无新增打印件；实际夹持座尚未设计。

![完整名义路径，部分零件隐藏](overview.png)

| 检查 | 当前证据 |
|---|---|
| 新过渡的源实体、既有插头及静态线 | 12条候选逐一重放通过；相对姿态覆盖13个yaw × 10个pitch，即130组合 |
| 新过渡与活动线环、身体线段 | PASS；各候选检查自身接续、其他三根及相对运动 |
| 四条过渡同时存在 | 54个候选配对检查均通过，81种组合可用；展示组合为0/0/0/0 |
| 过渡之间表面间隙 | 下界不小于{fan_gap:.6f}mm；名义要求0.3mm |
| CAM端四条线环间隙 | 下界{gap:.6f}mm；与身体线段共存检查通过 |
| 路线接续 | 130姿态共1560处接点；最大坐标差{joins['maximum_endpoint_error_mm']:.9f}mm，属于保存变换的数值误差 |
| 线环全俯仰范围 | −20°至+25°长度恒定，活动段72.610689mm；上部弧半径下界{upper_r:.6f}mm，下部7.5mm |
| 过渡整段曲率 | 全部12候选半径下界≥7.0mm；当前筛查值6.9342mm，不是动态寿命规格 |
| 未改段的证据继承 | 相机端仅删除直段尾部；保留段逐点一致，曲率下界7.2009mm继承原检查 |

## 三个头部姿态

![零位](zero.png)
![低头20度](down20.png)
![抬头25度](up25.png)

图中隐藏部分壳体/器件，实体检查仍包含209个物理源件、29个插头分配和14条静态线。使用的是独立J3M打印件候选，不能把结果直接算作现有主模型通过。四色仅表示几何槽位，不定义供应商线色或针腔视图。

## 还没有完成的部分

1. 实际固定点和应力释放：路线中的固定坐标目前只是设计基准，不能保证自由导线会自然呈现图中形状。
2. 完整装入及拆修：此前局部松端子穿入检查，不等于本轮完整四线可实际装入。还需要连同固定结构检查装配顺序、手和工具空间。
3. 其余七根头部活动导线、相机FPC，以及照片位置误差与制造公差。
4. CAM实际互配料号、针腔视图、具体线材/端子/工具组合和供应商工艺参数。之后才能完成整根加工长度与公差。

0.306mm是名义模型的间隙下界，距0.3mm筛查线很近；没有包含实物误差。弧段解析界不证明连续姿态碰撞、弯折寿命或整机可靠性。所有模型仍为 PROTOTYPE / UNVALIDATED。

## 资料与复查

供应商按图制作已经确定；不再等待制作方式选择。[2026-10-04公开资料补查](../../supplier_made_harness/recheck_20261004/README.md)列明了已取得的JST官方数据，以及舵盘、WeAct、CAM插合/FPC等具体缺项。未取得的字段仍需进一步资料或实物确认，不是把全部检索工作转给供应商。

- [独立 Blender 检查副本](comparison.blend)、[图像来源](render_manifest.json)、[复现命令](commands.json)。
- [过渡候选](four_bend_transition/pool.json)、[独立重放和整束检查](four_bend_transition/packing.json)、[过渡整段数学界](four_bend_transition/math_bounds.json)。
- [CAM线环实体检查](short_tail_v2/screen.json)、[线环整束检查](short_tail_v2/packing.json)、[全角度线长/半径界](short_tail_v2/math_bounds.json)、[接点与直段裁短证明](joins.json)。
- [本次来源清单](review_manifest.json)、[之前尚未连接的阶段](../cam_parallel_pitch/index.html)。

早期尝试和失败日志原样保留。早期Bezier搜索记录中的connection_checks被覆盖为空值，不能作为通过证据；本轮packing.json中的individual_replay重新执行了全部12个候选的自交、相邻路线和源实体检查，并明确记录PASS。未完成的广泛搜索未用于本轮结论。
'''
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 身体至CAM四线路径</title>
<style>body{{font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f3f6f5;color:#283e43;max-width:1120px;margin:28px auto;padding:0 24px 60px}}a{{color:#086f78}}.note{{background:#fff0d9;padding:18px 22px;border-radius:8px}}.ok{{background:#e4f2eb;padding:18px 22px;border-radius:8px}}.images{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}figure{{margin:0}}img{{width:100%;border-radius:8px}}.overview{{max-width:640px;display:block;margin:auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:11px;border-bottom:1px solid #cdd9d7;text-align:left}}@media(max-width:760px){{.images{{grid-template-columns:1fr}}}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">全部剩余项目</a></p>
<h1>身体至CAM：四线路径已接通</h1>
<p class="ok">新增颈部到俯仰线环的过渡。四条名义路径共同通过本轮几何检查，解决了上次两段未连接的问题。</p>
<p class="note">独立候选，主模型未改。实际固定、完整装配、其余头部线路和实物接口仍未完成；不能按本页长度加工。</p>
<a href="overview.png"><img class="overview" src="overview.png" alt="完整四线名义路线，选择性隐藏遮挡零件"></a>
<p>从身体板端经过颈部和两轴活动区，接到条件性CAM插合分配。下方显示同一组路线在零位、低头和抬头时的形状；四色仅表示槽位。</p>
<div class="images">'''+''.join(f'<figure><a href="{file}.png"><img src="{file}.png" alt="{label}的CAM四线路径"></a><figcaption>{label} · 点击原图</figcaption></figure>' for file,label in [('zero','零位'),('down20','低头20°'),('up25','抬头25°')])+f'''</div>
<table><tr><th>已完成</th><th>结果</th></tr><tr><td>130组合姿态下的源实体及路线检查</td><td>PASS，采用独立J3M打印件候选</td></tr><tr><td>四线共同排布</td><td>PASS，54个过渡配对检查，81种可用组合</td></tr><tr><td>1560处路线接点</td><td>PASS，最大数值误差小于0.000008mm</td></tr><tr><td>名义线间隙</td><td>CAM段下界{gap:.3f}mm，过渡之间≥{fan_gap:.3f}mm；未计实物公差</td></tr><tr><td>整段半径/长度</td><td>解析界PASS；不代表连续碰撞或线材寿命通过</td></tr></table>
<h2>仍需完成</h2><p>实际固定和应力释放、完整装入与拆修、其余七根头部导线与相机FPC、真实插合件和加工公差。位置固定仅是当前路径约束，自由导线未必按图弯曲。</p>
<p>供应商按图制作已确定。<a href="../../supplier_made_harness/recheck_20261004/README.md">最新公开资料补查</a>列出了具体已知和未知尺寸；目前不会把模型中心线直接作为下料长度。</p>
<p><a href="README.md">完整说明</a> · <a href="comparison.blend">Blender副本</a> · <a href="four_bend_transition/packing.json">四线独立重放</a> · <a href="four_bend_transition/math_bounds.json">过渡数学界</a> · <a href="short_tail_v2/math_bounds.json">线环数学界</a> · <a href="joins.json">接点复核</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">来源清单</a></p></html>'''
(OUT/'index.html').write_text(html)

status_path=PARENT/'work_status.json'; status=read(status_path)
row=next(r for r in status['remaining'] if r['id']=='harness'); old_detail=row['detail']
row.update(detail=detail,evidence='harness_A8/cam_fan_in/index.html')
status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_fan_in/index.html',
    CAM_parallel_fan_in='PASS',CAM_parallel_anchors='NOT_TESTED',CAM_yaw_pitch_service_loop='PASS',
    CAM_whole_four_wire_packing='PASS',CAM_connected_route_scope='Nominal prescribed four-wire geometry with J3M study solids; no real anchors or complete installation',
    CAM_connected_route='PASS',CAM_connected_route_seams='PASS',CAM_connected_route_head_poses=130,
    CAM_connected_route_review='harness_A8/cam_fan_in/index.html',CAM_connected_route_gap_lower_mm=gap,
    CAM_connected_route_applied=False,CAM_route_applied=False,
    public_source_recheck='supplier_made_harness/recheck_20261004/README.md')
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html'; text=p.read_text(); assert old_detail in text
p.write_text(text.replace(old_detail,detail).replace('<a href="harness_A8/cam_parallel_pitch/index.html">','<a href="harness_A8/cam_fan_in/index.html">'))
for p,link in [(HERE/'index.html','cam_fan_in/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_fan_in/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_fan_in/index.html')]:
    text=p.read_text()
    if p==HERE/'index.html':
        pattern=r'<section id="threading-update">.*?</section>'
        block=f'<section id="threading-update"><h2>最新：身体至CAM四线路径接通</h2><p>{detail}</p><p><a href="{link}">查看当前路线与三姿态图</a>；下方保留历史阶段。</p></section>'
    else:
        start='<!-- A8_PITCH_FLEX_UPDATE -->'; end='<!-- /A8_PITCH_FLEX_UPDATE -->'
        pattern=re.escape(start)+'.*?'+re.escape(end)
        block=f'{start}<section><h2>身体至CAM四线路径更新</h2><p>{detail}</p><p><a href="{link}">当前结果及剩余项目</a></p></section>{end}'
    text,n=re.subn(pattern,block,text,flags=re.S); assert n==1; p.write_text(text)
p=HERE/'README.md'; text=p.read_text()
text,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->',
    '<!-- A8_PITCH_FLEX_LATEST -->\n最新见[身体至CAM四线路径](cam_fan_in/index.html)：名义连接和四线共同排布检查通过；真实固定、完整装入和其他头部线路尚未完成，主模型未替换。下方保留历史阶段。\n<!-- /A8_PITCH_FLEX_LATEST -->',text,flags=re.S)
assert n==1; p.write_text(text)

base='mechanical/studies/prearrival_finish/harness_A8/'
bpy_cmd='/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python '+base
py_cmd='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base
commands={'cwd':str(ROOT),'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':'3.12.14'},
    'commands':[bpy_cmd+'plan_cam_short_tail_v2.py',bpy_cmd+'check_cam_short_tail_bundle.py',py_cmd+'audit_cam_short_tail_arc.py',
                py_cmd+'prepare_fan_curvature_v4.py',bpy_cmd+'plan_cam_yaw_fan_v4.py',bpy_cmd+'plan_cam_yaw_fan_four_bends.py',
                py_cmd+'audit_cam_fan_math.py four_bend_transition',bpy_cmd+'pack_cam_fan_transitions.py',py_cmd+'verify_cam_fan_joins.py',
                '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/studies/prearrival_finish/harness_A8/assembly_feed_v3/open_mouth/cleaned/candidate.blend -t 4 --python-exit-code 1 --python '+base+'render_cam_fan_review.py',
                py_cmd+'publish_cam_fan_review.py',py_cmd+'verify_delivery.py'],
    'execution_notes':['Existing original tail, body-prefix and J3M source studies are dependencies; their hashes are retained.',
        'Broad cubic search was explicitly terminated without a completed pool; it contributes no passing evidence.',
        'The initial pack assertion failed on overwritten search metadata. The final pack script independently replayed all12 candidates; fan_pack_replay.log records the completed check.',
        'Fixed-anchor, high-anchor and sidepass failures remain in their separate study directories.',
        'The review render was rerun to add the full-route overview; geometry and selected route were unchanged.']}
(OUT/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
files=[OUT/n for n in ['README.md','index.html','commands.json','short_tail_v2/screen.json','short_tail_v2/curves.npz',
    'short_tail_v2/tails.npz','short_tail_v2/packing.json','short_tail_v2/math_bounds.json','four_bend_transition/pool.json',
    'four_bend_transition/curves.npz','four_bend_transition/packing.json','four_bend_transition/math_bounds.json',
    'joins.json','render_manifest.json','overview.png','zero.png','down20.png','up25.png','comparison.blend']]
manifest={'status':'PASS','scope':'Independent nominal UART continuity, finite-pose packing and reviewed publication',
    'script_sha256':sha(SCRIPT),'source_main_sha256':pack['source_main_sha256'],'main_applied':False,
    'images_visually_reviewed':True,'whole_harness':'BLOCKED','manufacturing_release':False,
    'files':{str(p.relative_to(ROOT)):sha(p) for p in files}}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('CAM_FAN_REVIEW_PUBLISHED')
