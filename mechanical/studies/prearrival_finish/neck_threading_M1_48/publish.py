"""Publish a corrective addendum, keeping historical numerical data intact."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,re

HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3];FINISH=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
audit=json.loads((HERE/'source_audit.json').read_text())
screen=json.loads((HERE/'native_threading_screen.json').read_text())
outer=json.loads((HERE/'outer_corridor_screen.json').read_text())
motion=json.loads((HERE/'outer_corridor_motion_lowest.json').read_text())
original_motion=json.loads((HERE/'outer_corridor_motion.json').read_text())
lower_motion=json.loads((HERE/'outer_corridor_motion_lower.json').read_text())
ntrials=len(outer['trials']);npass=len(outer['passing'])
assert all(x['source_main_sha256']==audit['source_main_sha256'] for x in [screen,outer,motion])
assert sha(PROJECT/'mechanical/mori_v1_2.blend')==audit['source_main_sha256']
now=datetime.now(timezone.utc).isoformat()
old=FINISH/('harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/'
            'body_supply/complete_head/bridge_wire_stock/bridge_tail_order_review')
changed_pages={p:sha(p) for p in [old/'index.html',old/'README.md',FINISH/'index.html',FINISH/'work_status.json',PROJECT/'mechanical/index.html']}
new_link=os.path.relpath(HERE/'index.html',old)
note='更正：旧研究初始化时加载了尚未采用的 Yaw_Base / Pitch_Yoke 切槽候选，原文“全部使用原桥座”的表述不成立。当前 M1.48 主模型未改；重新核对后，下套端子的局部碰撞仍成立，原 R8 下弯线中心也穿入主模型材料。下方保留历史文本及数值，不能据此认定现有主模型线路已通过。'
for path in [old/'index.html',old/'README.md']:
    text=path.read_text()
    if path.suffix=='.html':
        block=f'<aside id="native-source-correction" style="padding:20px;background:#fff0d3;border:2px solid #b97919;margin:18px 0"><b>M1.48 来源更正</b><p>{note}</p><a href="{new_link}">查看主模型复查与新的外侧局部通路</a></aside>'
        if 'id="native-source-correction"' not in text:
            # This historical page has an implicit HTML body and no <main>.
            assert '</style>' in text;text=text.replace('</style>','</style>'+block,1)
    else:
        block=f'> **M1.48 来源更正**：{note}\n> [查看当前复查]({new_link})\n\n'
        if not text.startswith('> **M1.48 来源更正**'):text=block+text
    path.write_text(text)

motion_summary=(f'选定的4段固定局部路径，在{motion["poses"]}个头部姿态下未检出间隙失败；'
                if motion['status']=='PASS' else
                f'选定局部路径在{motion["poses"]}个头部姿态中仍有{len(motion["failures"])}个失败姿态；')
details=f'''# M1.48：颈部研究来源更正与当前实体复核

更新时间：{now}。当前模型哈希：`{audit['source_main_sha256']}`。

旧“原桥座”研究用了未采用的切槽候选。与主模型相比，候选 Yaw_Base 移除约92.641mm³，Pitch_Yoke 移除约332.838mm³。旧保存剖面与候选相符，与主模型不符；初始化替换链和实体差分已记录。历史数值文件保留，原来源声明撤回。

![当前主模型与历史候选剖面](bridge_comparison.png)

直接加载当前主模型后得到两条有效的失败证据：

- 桥座下套224mm位置，第四根临时直立线尾的端子请求空间仍与底面相交2.718mm³；它是具体路线失败，不是所有装法都不可能。
- 原R8下弯路线在四个方位均穿进主模型。首个检出的中心入实体点在Z141.493mm附近，不能把旧候选的静态排布通过沿用给原件。

另外测试的四条“裸端子沿该R8弯逐渐转直”的路径，连未加余量的1×1.8×4.1mm名义端子也会碰到桥座；这些端子尺寸仍是ASSUMED空间，绝非厂家真实端子CAD。中央Ø3.6mm孔的结构用途是舵盘锁紧工具通道，没有改作永久走线通道。

## 不改打印件的替代方向

![外侧局部路径，两端均未连接](outer_corridor.png)

围绕原轴承外侧测试{ntrials}条R8弯曲局部线段，{npass}条在机械零位通过连续线段间隙检查。原上端Z172mm在91个头部姿态中有间隙失败，Z170mm版本仍在89个姿态中失败。最新候选把外侧半径调到37.6mm，下端保持Z137mm，上弯起点Z160mm、上端Z168mm；四个方位使用同一截面参数，{motion_summary}这仅覆盖身体固定的颈部局部段。

线径0.6604mm、项目表面间隙0.3mm保持。检查用采样间距的一半及解析圆弧弦误差覆盖连续线段，并单独检查点是否在实体内；头部姿态仍是有限采样。四段相隔90°/180°，互相中心线距离下界{motion['continuous_interwire_distance_lower_bound_mm']:.3f}mm。

以下工作仍未完成：下端接到PCB的实际路径、上方偏航/俯仰服务环、完整四线长度和固定、真实端子/胶壳穿入、其余身体线/跨关节线与FFC、手和工具操作。外侧路径尚未应用，不能据此放行线束制作。主模型、参数、合同、STL和装配视频均保持M1.48本轮已交付状态，没有增加孔、切槽或零件。

## 原始记录

- [几何来源差分与加载链](source_audit.json)
- [主模型下弯与端子碰撞](native_threading_screen.json)
- [{ntrials}条外侧局部路径](outer_corridor_screen.json)
- [最新候选130个头部姿态检查](outer_corridor_motion_lowest.json)
- [Z172mm版本失败记录](outer_corridor_motion.json) / [Z170mm版本失败记录](outer_corridor_motion_lower.json)
- [当前整体剖面](native_neck_context.png)
- [实际执行命令与来源](publication.json)
'''
(HERE/'README.md').write_text(details)
body=f'''<nav><a href="../index.html">到货前复核</a> · <a href="../../../index.html?revision=V1.2-M1.48#camera-cam">当前主模型</a></nav>
<h1>颈部走线：来源更正与当前实体复查</h1>
<p class="note"><b>完整线束仍为 BLOCKED。</b> 主模型没有采用任何通道候选。本页没有改模型或更新装配动作。</p>
<h2>旧研究中“原桥座”的来源标签有误</h2><p>初始化脚本加载了未采用的两处切槽候选。保存剖面与候选完全对应，与主模型不同。历史数值保留，来源声明已在原页面显著更正。</p>
<figure><img src="bridge_comparison.png" alt="左侧主模型，下弯路线穿入材料；右侧是未采用的切槽候选"><figcaption>左：当前主模型。右：旧研究实际使用的独立候选。红线仅示意原来R8下弯中心线。</figcaption></figure>
<p>重新检查主模型，原下弯中心线确实穿入桥座。桥座直接下套时的端子碰撞也仍存在：局部相交约2.718mm³。中央小孔用于舵盘锁紧工具，未改成走线孔。这些结果只排除具体路径，不证明所有装法均不可行。</p>
<h2>现有零件仍有外侧局部通路</h2><p>{ntrials}条局部候选中，{npass}条在零位满足所设线径与间隙。把固定段上端从Z172mm收低至Z168mm并调整外侧半径后，{motion_summary}<b>两端尚未接到PCB和头部服务环，不能当成整条线束通过。</b></p>
<figure><img src="outer_corridor.png" alt="绕轴承外侧的局部通路，上下两端都未连接"><figcaption>蓝线绕过原轴承外侧。圆圈表示尚未连接的两端；打印件保持原样。</figcaption></figure>
<table><thead><tr><th>检查</th><th>结论与边界</th></tr></thead><tbody>
<tr><td>主模型来源</td><td>PASS：直接读取M1.48保存实体，无研究候选替换。</td></tr>
<tr><td>原R8内侧下弯</td><td>FAIL：四个方位的线中心均进入桥座材料。</td></tr>
<tr><td>外侧局部段</td><td>零位连续线段间隙PASS；选定四段头部{motion['poses']}姿态检查{motion['status']}。不是完整线束。</td></tr>
<tr><td>采购与制造</td><td>BLOCKED：真实压接端子、服务环、固定和完整装配顺序未完成。无采购或制作放行。</td></tr>
</tbody></table>
<p class="links"><a href="README.md">完整说明</a><a href="source_audit.json">来源差分</a><a href="native_threading_screen.json">主模型碰撞</a><a href="outer_corridor_screen.json">外侧候选</a><a href="outer_corridor_motion_lowest.json">姿态检查</a><a href="publication.json">命令与哈希</a><a href="native_neck_context.png">整体剖面</a></p>'''
css='body{background:#f0f4f2;color:#263a33;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;margin:0}main{max-width:1140px;margin:auto;padding:30px 22px 70px}a{color:#126954}h1{font-size:32px}h2{margin-top:32px}.note{background:#fff1d2;border:1px solid #d0b582;padding:17px}figure{margin:24px 0;background:white;border:1px solid #c3d2cb}img{width:100%;display:block}figcaption{padding:12px}table{border-collapse:collapse;width:100%}td,th{padding:13px;border-bottom:1px solid #c3d2cb;text-align:left;vertical-align:top}.links{display:flex;flex-wrap:wrap;gap:16px}@media(max-width:700px){h1{font-size:25px}main{padding:20px 13px}}'
(HERE/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.48 · 颈部走线复查</title><style>'+css+'</style><main>'+body+'</main></html>')

path=FINISH/'work_status.json';w=json.loads(path.read_text())
w['updated_utc']=now
w['native_bridge_tail_order'].update(historical_original_solids_claim='FAIL',
    historical_substituted_prints=['Yaw_Base','Pitch_Yoke'],
    correction='neck_threading_M1_48/index.html',main_model_unchanged=True)
w['native_neck_current_review']=dict(status='PASS',scope='Source audit and bounded local corridor only',
    whole_harness='BLOCKED',source_blend_sha256=audit['source_main_sha256'],
    evidence='neck_threading_M1_48/index.html',historical_source_claim='FAIL',
    local_outer_paths_passed=npass,selected_outer_path_head_pose_status=motion['status'],
    main_applied=False)
r=next(x for x in w['remaining'] if x['id']=='harness')
r['latest_native_bridge_order_evidence']='neck_threading_M1_48/index.html'
r['latest_native_bridge_order_detail']=f'旧“原桥座”初始化误用了未采用的J2切槽候选，来源声明已撤回。当前M1.48重跑确认下套端子约2.718mm³碰撞仍成立，原R8下弯线中心也穿入桥座。{ntrials}条外侧局部通道中{npass}条零位通过；'+motion_summary+'尚未连接两端PCB/服务环，完整线束和装配仍BLOCKED。'
r['native_geometry_source_correction']='neck_threading_M1_48/source_audit.json'
path.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n')

for path,href in [(FINISH/'index.html','neck_threading_M1_48/index.html'),
                  (PROJECT/'mechanical/index.html','studies/prearrival_finish/neck_threading_M1_48/index.html')]:
    text=path.read_text()
    block=f'<aside id="M1-48-neck-audit" class="notice"><b>颈部走线来源复核已更新。</b> 旧“原桥座”研究误载了通道候选，已更正；当前主模型下弯路线仍有实体冲突。另找到不改打印件的外侧局部通道，尚未接成完整线束。<a href="{href}">查看剖面、范围与剩余工作</a>。</aside>'
    if 'id="M1-48-neck-audit"' not in text:
        assert '<main>' in text;text=text.replace('<main>','<main>'+block,1)
    if path==FINISH/'index.html':
        text=text.replace('<title>MORI M1.47 · 已确认的两处修正</title>','<title>MORI M1.48 · 到货前复核</title>')
        text=text.replace('CAM内六角螺钉待确认；裁线图未放行。','CAM内六角螺钉已于M1.48采用；裁线图未放行。')
    path.write_text(text)

commands=[]
for script,log in [('audit_sources.py','audit_sources.log'),('screen_native_threading.py','native_threading_screen.log'),
                   ('section_inputs.py','section_inputs.log'),('screen_outer_corridor.py','outer_corridor_screen.log'),
                   ('check_outer_corridor_motion.py','outer_corridor_motion.log')]:
    contents=(HERE/log).read_text();assert 'Blender quit' in contents and 'Traceback' not in contents
    commands.append(dict(command='/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python '+str((HERE/script).relative_to(PROJECT)),
                         cwd=str(PROJECT),exit_code=0,log=log,log_sha256=sha(HERE/log)))
commands.append(dict(command='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+str((HERE/'plot_sections.py').relative_to(PROJECT)),cwd=str(PROJECT),exit_code=0))
for option,log in [('--lower-upper-bend','outer_corridor_motion_lower.log'),('--lowest-upper-bend','outer_corridor_motion_lowest.log')]:
    contents=(HERE/log).read_text();assert 'Blender quit' in contents and 'Traceback' not in contents
    commands.append(dict(command='/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python '+str((HERE/'check_outer_corridor_motion.py').relative_to(PROJECT))+' -- '+option,
                         cwd=str(PROJECT),exit_code=0,log=log,log_sha256=sha(HERE/log)))
publication=dict(status='PASS',scope='Corrected source labels, independent native checks, and local corridor research',utc=now,
    source_main_sha256=audit['source_main_sha256'],tools={'Blender':'5.2.2 LTS d13f752e3b9c','plot_python':'/Users/dean/.cache/codex-runtimes/mori-cad/bin/python'},
    commands=commands,changed_presentation_files={str(p.relative_to(PROJECT)):{'before':h,'after':sha(p)} for p,h in changed_pages.items()},
    files={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name not in ['publication.json','delivery.json']},
    historical_numeric_records_unchanged=True,whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    publication_repair=dict(initial_exit_code=1,reason='Historical HTML has no main element; no source model was changed.',
                            resolution='Insert corrective banner after the existing style element.'))
(HERE/'publication.json').write_text(json.dumps(publication,ensure_ascii=False,indent=2)+'\n')
print('NATIVE_NECK_REVIEW_PUBLISHED',motion['status'],flush=True)
