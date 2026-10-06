"""Publish the unadopted J3M mouth cleanup and its scoped saved-solid checks."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, re

HERE = Path(__file__).resolve().parent
OUT = HERE / 'assembly_feed_v3/open_mouth'
PARENT = HERE.parent
ROOT = HERE.parents[3]
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
names = ['candidate_screen', 'cleaned/storage', 'reloaded_verification',
         'relaxation_screen', 'journal_sections', 'mouth_cleanup_audit',
         'continuous_slack', 'render_manifest']
data = {n: read(OUT / (n + '.json')) for n in names}
assert all(d['status'] == 'PASS' for d in data.values())
check = data['reloaded_verification']
audit = data['mouth_cleanup_audit']
continuous = data['continuous_slack']
assert sha(ROOT / 'mechanical/mori_v1_2.blend') == check['source_blend_sha256']
assert check['source_candidate_sha256'] == sha(OUT / 'cleaned/candidate.blend')
assert audit['after_isolated_section_count'] == 0 and not continuous['unresolved_intervals']
detail = ('J3M独立候选已把四处穿线出口薄边整理为连续开口；保存实体的穿装、130个头部姿态、'
          '局部相邻剖面和规定角向理线过程的连续间隙检查通过。轴颈壁厚样本不变。'
          '候选尚未应用主模型；完整固定、松散尾线操作、俯仰段/CAM、其余7根活动线和FPC仍未完成。')
md = f'''# J3M：穿线出口整理

**独立候选，未应用主模型；完整线束仍为 BLOCKED，不能据此下料或打印放行。**

{detail}

## 改了哪里

在J3两件打印候选的基础上，只进一步移除Pitch_Yoke四个出口上方的薄边，形成连续开口。
准确布尔构建共移除{data['candidate_screen']['upper_mouth']['removed_volume_mm3']:.3f} mm³，不增加材料、台阶、零件或紧固件。
开口限定在局部R12.5–19、切向±1.2、Z183.5–191.01 mm区域，功能轴线和轴颈不移动。
其余207个原有实体与主模型一致。这里的“四处开口”属于未应用的线束候选；正式M1.47没有这些通道。

![J3清理前，实际保存网格](mouth_before.png)
![J3M清理后，相同相机和比例](mouth_after.png)

## 已完成的数字检查

| 检查 | 结果 | 范围 |
|---|---|---|
| 保存重载拓扑 | PASS | 两件候选均为单个连通闭合网格，无零面积三角面 |
| 出口薄边清理 | PASS | 每版100个相邻剖面，局部孤立截面片92→0；检查保存后的实际网格 |
| 原通道保持 | PASS | Z183.5以下材料差异仅数值量级；轴颈最小径向壁厚样本仍{audit['journal_minimum_sample_unchanged_mm']:.3f} mm |
| 端子连尾线穿入 | PASS | 4个入口；名义端子/软线间隙下界{check['nominal_contact_gap_bound_mm']:.3f}/{check['nominal_tail_gap_bound_mm']:.3f} mm |
| 已装线形与头部姿态 | PASS | 130组合姿态、520线/姿态；209源实体、29对插分配、14根静态线 |
| 规定角向理线过程 | PASS | 64个自适应参数区间，包含区间内运动与曲线离散误差；弯曲半径下界{continuous['central_bend_radius_lower_bound_mm']:.3f} mm |

角向理线是明确规定的运动学曲线，不是软线受力/弹性模拟。径向与高度调整沿用J3已检查的连续扫掠；88个有限阶段复核也保留。
内部补入的5.10 mm只是局部理线长度变化，**不是最终下料长度或完整装配松量**。
保留[J3逐根装入顺序数据](../local_wire_order.json)：导线路径与顺序不变，本次仅移除打印材料。

仍未证明全件最小壁厚、PA12强度、手部操作、摩擦、实际压接形状或动态弯折寿命。CAM插座位置/配套仍含照片估计，不能将目录候选当作实物确认。

## 原厂资料与待完成项

[JST SH原厂目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)和[JST PH原厂目录](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)已提供端子、线径与工具资料；[逐料号工艺查询](../../TOOLING_DETAILS.md)保留来源和版本限制。
后续需完成俯仰段与CAM、固定点、全部分支及加工长度。实际匹配和工艺仍需供应商按具体线材/端子确认，不要求用户代替检索公开资料。

- [独立可编辑Blender](cleaned/candidate.blend)
- [保存实体复核](reloaded_verification.json) · [薄边与相邻剖面](mouth_cleanup_audit.json)
- [连续理线检查](continuous_slack.json) · [轴颈截面](journal_sections.json)
- [图像来源](render_manifest.json) · [复现命令](commands.json) · [发布清单](review_manifest.json)
- [J3历史检查](../index.html) · [完整项目状态](../../../index.html)

主模型SHA256：`{check['source_blend_sha256']}`。本次未修改硬件文件、STL或装配视频。
'''
(OUT / 'README.md').write_text(md)
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · J3M穿线出口整理</title><style>body{{font:16px/1.85 system-ui,sans-serif;color:#283e43;background:#f2f5f5;max-width:1140px;margin:30px auto;padding:0 24px 50px}}a{{color:#07717b}}h1{{font-size:29px}}.note{{background:#fff0d7;padding:16px 20px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}figure{{margin:0}}img{{width:100%;border-radius:8px}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #ccd7d8}}@media(max-width:700px){{.pair{{grid-template-columns:1fr}}}}</style>
<p><a href="../../index.html">← A8线束研究</a> · <a href="../../../index.html">完整项目状态</a></p>
<h1>穿线出口的薄边，整理成连续开口</h1><p class="note">独立候选 J3M，未应用主模型。完整线束仍为 BLOCKED，尚未形成加工放行图。</p>
<p>{detail}</p><div class="pair"><figure><img src="mouth_before.png" alt="J3实际保存网格，出口顶部有薄边"><figcaption>J3：清理前</figcaption></figure><figure><img src="mouth_after.png" alt="J3M实际保存网格，出口连续敞开"><figcaption>J3M：清理后；相同视角和比例</figcaption></figure></div>
<h2>范围与结果</h2><p>四处上缘总计移除33.876 mm³；没有新增台阶、零件、紧固件。保持轴线、轴颈及其余207个实体。</p>
<table><tr><th>数字检查</th><th>结果</th><th>范围</th></tr><tr><td>保存网格与局部剖面</td><td>PASS</td><td>两个连通闭合实体；100个相邻剖面中薄边截面片92→0</td></tr><tr><td>端子带线穿入、头部姿态</td><td>PASS</td><td>4个入口；130个组合姿态；名义端子/线间隙下界0.306/0.302 mm</td></tr><tr><td>规定的连续角向理线</td><td>PASS</td><td>64个参数区间；弯曲半径下界7.955 mm</td></tr><tr><td>全件壁厚、承载与实物线束</td><td>NOT_TESTED</td><td>截面与运动学计算不代表强度、手部操作或弯折寿命</td></tr></table>
<p>局部理线需补入5.10 mm线长。这不是整束下料长度。俯仰段/CAM、固定点、其他活动线及完整FPC仍需完成。</p>
<p>原厂公开资料：<a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">JST SH</a> · <a href="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf">JST PH</a> · <a href="../../TOOLING_DETAILS.md">工艺查询与版本限制</a></p>
<p><a href="cleaned/candidate.blend">打开独立Blender候选</a> · <a href="README.md">完整说明</a> · <a href="reloaded_verification.json">保存实体复核</a> · <a href="mouth_cleanup_audit.json">薄边审查</a> · <a href="continuous_slack.json">连续理线</a> · <a href="journal_sections.json">轴颈截面</a> · <a href="render_manifest.json">图像来源</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">发布清单</a> · <a href="../index.html">J3历史研究</a></p></html>'''
(OUT / 'index.html').write_text(page)
base = '"/Applications/Blender.app/Contents/MacOS/Blender"'
rootcmd = 'mechanical/studies/prearrival_finish/harness_A8/'
scripts = ['build_open_feed_mouth', 'clean_open_feed_mouth', 'verify_open_feed_mouth',
           'check_open_feed_relaxation', 'inspect_open_feed_sections',
           'audit_open_feed_mouth', 'check_continuous_feed_slack', 'render_open_feed_mouth']
commands = []
for s in scripts:
    blend = rootcmd+'assembly_feed_v3/open_mouth/candidate.blend' if s == 'clean_open_feed_mouth' else (
        rootcmd+'assembly_feed_v3/open_mouth/cleaned/candidate.blend' if s == 'render_open_feed_mouth' else 'mechanical/mori_v1_2.blend')
    commands.append(base+' -b '+blend+' -t 4 --python-exit-code 1 --python '+rootcmd+s+'.py')
commands += ['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+rootcmd+s+'.py' for s in ['publish_open_feed_mouth','verify_delivery']]
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'reproduction_commands_in_separate_processes':commands,
    'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':'3.12.14'},
    'scope':'Reproduction commands; raw command history remains in conversation and saved logs',
    'main_applied':False},ensure_ascii=False,indent=2)+'\n')
sp = PARENT/'work_status.json'; state = read(sp)
old = next(r['detail'] for r in state['remaining'] if r['id']=='harness')
for row in state['remaining']:
    if row['id']=='harness': row.update(detail=detail,evidence='harness_A8/assembly_feed_v3/open_mouth/index.html')
state['A8_harness_research'].update(latest_review='harness_A8/assembly_feed_v3/open_mouth/index.html',
    J3M_upper_mouth_cleanup='PASS',J3M_saved_geometry_replay='PASS',J3M_continuous_angular_relaxation='PASS',
    J3M_applied=False,J3M_full_print_wall_and_strength='NOT_TESTED')
state['updated_utc']=datetime.now(timezone.utc).isoformat()
sp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
for path,href in [(HERE/'index.html','assembly_feed_v3/open_mouth/index.html'),(PARENT/'index.html','harness_A8/assembly_feed_v3/open_mouth/index.html')]:
    text=path.read_text();block=f'<section id="threading-update"><h2>最新：穿线出口薄边已在独立候选中整理</h2><p>{detail}</p><p><a href="{href}">查看J3M前后图与检查结果</a>。下方为历史阶段。</p></section>'
    assert '<section id="threading-update">' in text
    text=re.sub(r'<section id="threading-update">.*?</section>',block,text,flags=re.S).replace(old,detail)
    path.write_text(text)
path=HERE/'README.md';text=path.read_text()
note='<!-- coupled-feed-latest:start -->\n**最新进展：**'+detail+'\n\n[J3M出口清理与连续理线](assembly_feed_v3/open_mouth/index.html)。下方保留历史研究。\n<!-- coupled-feed-latest:end -->'
assert '<!-- coupled-feed-latest:start -->' in text
path.write_text(re.sub(r'<!-- coupled-feed-latest:start -->.*?<!-- coupled-feed-latest:end -->',note,text,flags=re.S))
manifest={'status':'PASS','scope':'Scoped J3M review publication, not full harness or manufacturing release',
    'updated_utc':datetime.now(timezone.utc).isoformat(),'source_blend_sha256':check['source_blend_sha256'],
    'source_candidate_sha256':sha(OUT/'cleaned/candidate.blend'),'source_script_sha256':sha(Path(__file__)),
    'checks':{n+'.json':sha(OUT/(n+'.json')) for n in names},
    'images':data['render_manifest']['images'],'main_model_applied':False,
    'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('J3M_REVIEW_PUBLISHED_MAIN_UNCHANGED')
