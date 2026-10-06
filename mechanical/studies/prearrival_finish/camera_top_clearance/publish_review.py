"""Publish an independently verified candidate; do not adopt it into main."""
from pathlib import Path
import json,hashlib,html,re,sys
from datetime import datetime,timezone
SCRIPT=Path(__file__).resolve();OUT=SCRIPT.parent;PARENT=OUT.parent;PROJECT=OUT.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
c=read(OUT/'construction.json');v=read(OUT/'verification.json');r=read(OUT/'render.json');p=read(OUT/'plots.json')
assert '--visual-reviewed' in sys.argv,'Inspect comparison.png and sections.png before publishing.'
assert v['status']==r['status']==p['status']=='PASS'
assert v['script_sha256']==sha(OUT/'verify_candidate.py')
assert c['script_sha256']==sha(OUT/'build_candidate.py')
assert v['construction_sha256']==sha(OUT/'construction.json')
assert r['verification_sha256']==sha(OUT/'verification.json')
assert p['render_sha256']==sha(OUT/'render.json')
assert r['script_sha256']==sha(OUT/'render_and_extract.py') and p['script_sha256']==sha(OUT/'plot_review.py')
assert all(sha(OUT/n)==h for q in [r,p] for n,h in q['outputs'].items())
assert all(sha(PROJECT/n)==h for n,h in c['protected_sources'].items())
md=f'''# 相机支架上沿：连续平直的局部间隙候选

状态：**独立候选，尚未采用**。当前主模型仍为 M1.47，配置、合同和其他 208 件源对象保持。

主模型 Display_Frame 相机口的两个上角与 Head_Front 有约 0.00765 mm³ 名义相交。
候选把相机口上方外边整条降低 **0.6 mm**，不增加局部缺口、台阶、孔或零件。
相机、原内侧定位面、前壳夹持唇、镜头和所有安装轴保持；前壳没有削薄。
代价是这一段上壁名义厚度由 **1.8 mm 变为 1.2 mm**。

![前后对比](comparison.png)
![实际网格剖面](sections.png)

## 已完成的名义几何检查

- 保存后的网格闭合、单个连通实体；其他 208 件源对象的网格和世界变换不变。
- 保存模型的支架/前壳相交为 0 mm³，最近间隙 {v['saved_shell_gap_mm']:.6f} mm。
- 上壁 20 个截面样本 {v['sampled_upper_wall']['min_mm']:.6f}–{v['sampled_upper_wall']['max_mm']:.6f} mm。只代表该上壁，不能当作整件最小壁厚或强度认证。
- 相机沿局部三轴正负各移动 0.5 mm，仍被原支架或前壳阻挡；这是名义限位检查，不是夹持力试验。
- 光学框架、相机、前壳分别 141 / 49 / 137 个具名装配位置通过。按工序未安装的部件逐项列在报告中，没有把全装状态与分步装配混淆。
- 前壳相对这次修改的支架沿 +Y 0–68 mm 平移，以距离变化界覆盖完整连续路径，共 8 个区间通过。其他部件对仍为有限位置检查。
- 理想布尔候选严格包含于原支架内部；全部安装变换保持，所以材料减少不会新增刚体运动干涉。原有其他接口不因此获得放行。

相机细部仍为官方尺寸加照片估算，实物配合与 PA12 上壁强度未验证。
完整线束、身体段供线和舵盘接口仍未完成。本页不代表可发厂生产或整机装配已通过。

[独立 Blender 候选](candidate.blend) · [保存模型与路径检查](verification.json) · [构造记录](construction.json) · [供应商资料](../harness_A8/supplier_source_update/index.html) · [返回总进度](../index.html)
'''
(OUT/'README.md').write_text(md)
body='''<p class="eyebrow">MORI M1.47 · 独立候选 · 未应用主模型</p>
<h1>相机支架上沿，保持平直并留出间隙</h1>
<p class="lead">上沿整条降低 <b>0.6 mm</b>，相机位置和内侧定位面保持。上壁名义厚度从 <b>1.8 → 1.2 mm</b>；没有新增局部台阶、孔或零件。</p>
<figure><img src="comparison.png" alt="相机支架上沿前后对比"><figcaption>橙色表示拟去除的上沿。相机与外壳保持原位。</figcaption></figure>
<figure><img src="sections.png" alt="相机支架实际网格剖面"><figcaption>模型间隙约 0.357 mm；外壳未削薄。</figcaption></figure>
<h2>检查结果</h2><ul><li>闭合单实体；其他 208 件的网格和位置保持。</li><li>上壁 20 个样本约 1.2 mm；相机六个方向仍受原结构限位。</li><li>光学框架、相机和前壳：141 / 49 / 137 个装入位置通过。</li><li>前壳与这处支架的 68 mm 合拢路径，8 个连续区间通过。</li></ul>
<p>这是名义几何结果。相机照片估算细部、PA12 壁强度和实际配合仍需到货验证；其他线束与传动问题仍保留。</p>
<h2>待确认</h2><p>是否接受将这条上沿降低 0.6 mm、保留 1.2 mm 名义上壁？按此前结构变化先确认的要求，本候选尚未写入主模型。</p>
<nav><a href="candidate.blend">Blender 候选</a><a href="verification.json">检查记录</a><a href="construction.json">构造记录</a><a href="README.md">完整说明</a><a href="../harness_A8/supplier_source_update/index.html">供应商资料</a><a href="../index.html">总进度</a></nav>'''
style='body{margin:0;background:#f5f7f6;color:#253e46;font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1100px;margin:auto;padding:46px 24px}h1{font-size:32px;line-height:1.4}h2{margin-top:32px}.eyebrow{color:#22766e}.lead{font-size:20px}figure{margin:28px 0}img{display:block;width:100%;border-radius:10px}figcaption{color:#66767c;font-size:14px}nav{display:flex;gap:20px;flex-wrap:wrap;margin-top:28px}a{color:#167970}li{margin:8px 0}'
(OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI 相机支架上沿候选</title><style>'+style+'</style><main>'+body+'</main></html>')
status=read(PARENT/'work_status.json');status['updated_utc']=datetime.now(timezone.utc).isoformat()
row=next(q for q in status['remaining'] if q['id']=='head_front_contact')
row.update(status='BLOCKED',owner='机械；局部候选待用户确认',
 detail='已完成独立平直上沿候选：整条降低0.6mm，上壁名义1.8→1.2mm；保存模型相交0，最近间隙0.357mm。六向限位、具名装入路径及前壳/支架连续68mm路径通过。其他208件保持。候选未应用，主模型原0.00765mm³相交仍存在；强度及实际相机配合待验证。',
 evidence='camera_top_clearance/index.html')
status['camera_top_clearance_candidate']=dict(status='PASS',scope='Independent nominal geometric review only',pending_user_adoption=True,
 candidate_sha256=sha(OUT/'candidate.blend'),verification_sha256=sha(OUT/'verification.json'),main_applied=False,manufacturing_release=False)
(PARENT/'work_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
idx=PARENT/'index.html';doc=idx.read_text();section='<section id="camera-top-clearance"><h2>相机支架上沿间隙候选</h2><p><a href="camera_top_clearance/index.html">查看前后对比与剖面</a>：上沿整条降低0.6mm，模型间隙约0.357mm，保留1.2mm名义上壁。限位、装入和前壳/支架连续合拢路径通过，其他208件保持。待确认后应用，主模型尚未修改。</p></section>'
doc=re.sub(r'<section id="camera-top-clearance">.*?</section>','',doc,flags=re.S)
assert '</main>' in doc;doc=doc.replace('</main>',section+'</main>');idx.write_text(doc)
publication=dict(status='PASS',script_sha256=sha(SCRIPT),protected_sources=c['protected_sources'],main_applied=False,
 candidate_pending_user_adoption=True,manufacturing_release=False,visual_reviewed=True,
 source_files={n:sha(OUT/n) for n in ['build_candidate.py','verify_candidate.py','render_and_extract.py','plot_review.py','construction.json','verification.json','render.json','plots.json','candidate.blend']},
 outputs={n:sha(OUT/n) for n in ['README.md','index.html','comparison.png','sections.png']})
(OUT/'publication.json').write_text(json.dumps(publication,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/n)==h for n,h in c['protected_sources'].items())
print('CAMERA_TOP_PUBLISHED PASS')
