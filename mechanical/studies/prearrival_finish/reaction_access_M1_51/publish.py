"""Publish verified M1.52 artifacts; keep previous study evidence historical."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];M=ROOT/'mechanical';BASE=OUT.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cfg=read(ROOT/'config/geometry.json');rev=cfg['revision'];assert rev=='V1.2-M1.52'
source=sha(M/'mori_v1_2.blend');scope=read(M/'reports/reaction_nut_alignment_validation.json')
access=read(OUT/'access.json');body=read(OUT/'body_split_check.json');val=read(M/'reports/validation.json')
exports=read(M/'reports/export_manifest.json');consistency=read(M/'reports/delivery_consistency.json')
animation=read(M/'animation/manifest.json');av=read(M/'animation/validation.json');engineering=read(BASE/'engineering_current.json')
assert all(r['status']=='PASS' for r in [scope,access,body,consistency,av,engineering])
assert all(r['source_blend_sha256']==source for r in [scope,access,body,animation,engineering])
assert val['counts']['FAIL']==0 and len(scope['scope']['changed_ids'])==2 and scope['scope']['unchanged_native_parts']==199
assert animation['rendered_video'] and animation['animation_revision']==rev+'-A1'
prep=read(OUT/'preparation.json');snapshot=ROOT/prep['snapshot_root']
old=read(snapshot/'mechanical/reports/export_manifest.json')
assert {r['id']:r['sha256'] for r in exports['parts']}=={r['id']:r['sha256'] for r in old['parts']}
assert len(exports['parts'])==21 and all(r['status']=='PASS' for r in exports['parts'])
assert all(sha(ROOT/n)==h for n,h in prep['protected_hardware'].items())
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()

summary='两枚现有试配六角螺母绕各自原螺钉轴转正30°，与原六角槽对齐。孔位、螺钉轴、尺寸和全部打印件保持；没有扩大孔槽或改变采购选型。'
limits='下部反力连接的螺母、螺钉与名义工具进入路径通过。上部舵盘夹口仍不能按所测直线路径在头架装好后塞入螺母；完整初装、真实舵盘与五金配合仍未完成。'
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.52 · 螺母槽对齐</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#edf1f0;color:#243a33;font:16px/1.8 system-ui,sans-serif}}main{{max-width:1080px;margin:auto;padding:28px 22px 64px}}nav{{display:flex;gap:20px;flex-wrap:wrap}}a{{color:#146c53}}img{{width:100%;display:block;border-radius:10px;border:1px solid #c9d6d0}}.done,.note{{padding:18px;border-radius:10px;background:#dcece3}}.note{{background:#fff0d5}}td,th{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #cad6d0}}table{{width:100%;border-collapse:collapse}}code{{word-break:break-all}}</style>
<main><nav><a href="../../../index.html?revision={rev}#nut-alignment">当前总装</a><a href="../../../animation/index.html?revision={rev}-A1">装配视频</a><a href="../body_split_adoption/index.html">前后分壳记录</a></nav>
<h1>两枚螺母与六角槽已对齐</h1><p>{rev} · {stamp}</p><p class="done">{summary} Blender、STL、预览与新版视频已同步；21件STL逐文件保持，仍是16件本体打印件。</p>
<a href="nut_alignment.png"><img src="nut_alignment.png" alt="两处真实剖面对比：原螺母错开30度，修正后与原槽边平行，打印件未改"></a>
<p>原先每处约0.00847mm³的角部相交已消除。图中橙色是试配螺母包络，实际螺母规格、螺纹和啮合尚未定型。</p>
<h2>检查结果与装配顺序</h2><table><tr><th>项目</th><th>本次证据</th></tr>
<tr><td>改动范围</td><td>仅两枚螺母做刚体转动；另199件机器人实体的坐标和三角网格保持。全部21件STL与M1.51字节一致。</td></tr>
<tr><td>下部横向锁紧</td><td>身体前后壳及线束暂不安装。先从后侧装螺母，再从前侧装横向螺钉；名义螺钉、螺母和刀杆/手柄的150mm连续轴向进入包络未检出碰撞。真实批头啮合、操作空间和扭矩需验证。</td></tr>
<tr><td>上部舵盘夹口</td><td>仍BLOCKED：头架装好后的直线装螺母路径与Pitch_Yoke相交；最终舵盘、短轴和夹紧方式仍待厂家资料。本次没有将已预装的动画当作初装验证。</td></tr>
<tr><td>头部与外壳</td><td>整机刚体、组合头部姿态、车轮与拓扑检查已重跑；前后壳含附件各275个位置、底部螺钉和工具路径复核通过。</td></tr>
<tr><td>完整线束</td><td>C6穿线口与导线约束候选未应用。端部、完整恒定长度线束、应力释放和带线合壳仍未完成。</td></tr></table>
<p class="note">{limits} 几何检查不能代替PA12强度、实物插合或完整线束验证；本轮无制造放行。</p>
<p><a href="access.json">下部进入与上部受阻记录</a> · <a href="../../../reports/reaction_nut_alignment_validation.json">两件刚体变换与座孔检查</a> · <a href="../../../reports/validation.json">当前检查及历史证据边界</a> · <a href="body_split_check.json">当前外壳与底部工具复核</a> · <a href="commands.json">执行记录</a></p>
<p>来源主模型SHA256：<code>{source}</code></p></main></html>'''
(OUT/'index.html').write_text(page)

p=M/'index.html';s=p.read_text()
s=s.replace('<title>MORI V1.2-M1.51</title>','<title>MORI V1.2-M1.52</title>').replace('<b>MORI V1.2-M1.51</b>','<b>MORI V1.2-M1.52</b>')
s=s.replace('<a href="#body-split">本轮前后分壳</a>','<a href="#nut-alignment">本轮螺母对齐</a><a href="#body-split">前后分壳</a>')
s=s.replace('<h1>身体前后分壳已应用。</h1>','<h1>反力连接螺母已与原槽对齐。</h1>')
s=s.replace('<h2>本轮：前后分壳</h2>','<h2>已采用：前后分壳</h2>')
section=f'<section id="nut-alignment"><h2>本轮：纠正两枚螺母的摆放角度</h2><p>{summary}</p><p>{limits}</p><p><a href="studies/prearrival_finish/reaction_access_M1_51/index.html?revision={rev}">查看真实剖面对比与当前检查</a>。主模型另199件实体保持，21件STL字节不变。</p></section>'
if 'id="nut-alignment"' in s:s=re.sub(r'<section id="nut-alignment">.*?</section>',lambda _:section,s,flags=re.S)
else:s=s.replace('<section id="body-split">',section+'<section id="body-split">')
s=re.sub(r'(src="renders/[^"]*\?revision=)V1\.2-M1\.51',r'\g<1>V1.2-M1.52',s)
s=s.replace('V1.2-M1.51当前已建模名义质量','V1.2-M1.52当前已建模名义质量')
s=s.replace('前后分壳已用于当前主模型，内部结构可在身体外壳未装时固定。反力夹本身的初次装配、最终舵盘接口以及与完整线束共存的工序仍需完成；本轮没有改变反力夹。',limits)
s=s.replace('四组上下壳孔、螺钉和嵌件配对移至X±22/Y±71；孔口作局部导入，螺钉承压台保持。上壳携附件倾斜取出路径已检查。','M1.43时的上下壳方案已由M1.51前后分壳取代：保留四枚框架螺钉，底部插舌定位；前后壳带附件平移装入及底部工具路径已重新检查。')
checks_section=f'<section id="checks"><h2>检查与文件</h2><p>本轮重跑{len(val["current_rerun_ids"])}项主模型检查，无几何FAIL；另完成当前外壳装入和下部横向锁紧工具检查。不受影响的历史证据保留原版本。21件STL全部导出通过，并与M1.51逐文件一致。</p><p>主模型、当前预览、电子细模与新版装配动画同步。完整线束、上部反力夹初装和供应商资料仍有未完成项。</p></section>'
s=re.sub(r'<section id="checks">.*?</section>',lambda _:checks_section,s,flags=re.S)
p.write_text(s)

work=read(BASE/'work_status.json');work.update(revision=rev,source_blend_sha256=source,updated_utc=stamp)
for r in work['completed']:
 if r['id']=='geometry_delivery':r.update(detail='M1.52只纠正两枚试配螺母的30°方向；另199件实体保持，21件STL与M1.51逐文件一致；全部当前预览与电子细模同步。',evidence='reaction_access_M1_51/index.html')
 if r['id']=='animation':r['detail']='V1.2-M1.52-A1：85.75秒、22步骤，同步两枚螺母方向。前后分壳工序保持；上部反力夹初装与完整线束仍未完成。'
 if r['id']=='engineering':r['detail']='V1.2-M1.52名义质量和390姿态计算同步；不是实物称重或载荷验证。'
work['completed']=[r for r in work['completed'] if r['id']!='reaction_nut_alignment']+[dict(id='reaction_nut_alignment',status='PASS',detail=summary,evidence='reaction_access_M1_51/index.html')]
for r in work['remaining']:
 if r['id']=='reaction_assembly':r.update(detail=limits,evidence='reaction_access_M1_51/index.html')
 if r['id']=='load_budget':r['detail']=r['detail'].replace('M1.51','M1.52')
work['reaction_nut_alignment']=dict(status='PASS',revision=rev,source_blend_sha256=source,evidence='reaction_access_M1_51/index.html',full_reaction_preassembly='BLOCKED',physical_fit='NOT_TESTED')
(BASE/'work_status.json').write_text(json.dumps(work,ensure_ascii=False,indent=2)+'\n')
p=BASE/'index.html';s=p.read_text();s=re.sub(r'<title>.*?</title>','<title>MORI · 到货前复核</title>',s,count=1)
banner=f'<div class="notice done" id="M1-52-adopted"><b>当前{rev}：两枚反力连接试配螺母方向已修正。</b> <a href="reaction_access_M1_51/index.html">剖面对比、下部进入检查与仍未完成的上部初装</a>。下方保留各版本历史记录；完整线束未完成。</div>'
if 'id="M1-52-adopted"' not in s:s=s.replace('<main>','<main>'+banner,1)
p.write_text(s)
(M/'README.md').write_text(f'# MORI {rev}\n\n{summary}\n\n主模型、电子细模、当前预览和{rev}-A1装配视频同步。另199件机器人实体保持，全部21件STL与M1.51字节一致；16件本体打印件。\n\n两处名义座孔相交消失。下部横向螺母、螺钉与工具的150mm连续进入包络通过；当前头部运动、外壳装入、底部工具和拓扑复核通过。旧检查保留其原版本与适用范围。\n\n{limits} 完整线束、供应商接口、质量预算和PA12实物验证仍未关闭。PROTOTYPE / UNVALIDATED；无制造放行。\n\n[本轮详情](studies/prearrival_finish/reaction_access_M1_51/index.html) · [装配动画](animation/index.html) · [工作状态](studies/prearrival_finish/work_status.json)\n')
for rel in ['parts.html','manufacturing.html']:
 p=M/rel;p.write_text(p.read_text().replace('V1.2-M1.51','V1.2-M1.52'))
p=M/'reports/组装与打印.md';s=p.read_text();s=s.replace('V1.2-M1.51','V1.2-M1.52')
s=re.sub(r'(当前主模型 SHA256：`)[0-9a-f]{64}(`)',lambda m:m[1]+source+m[2],s)
s=s.replace('其中两片身体壳更新，另外19件文件不变。','全部21件文件与M1.51一致。')
heading='## M1.52 反力连接螺母方向修正'
if heading in s:s=s.split(heading)[0].rstrip()
s+='\n\n'+heading+'\n\n'+summary+'\n\n'+limits+' 先不装前后壳和线束，从后侧装下部螺母，从前侧穿入横向螺钉；工具从前方进入。该工序只证明当前试配实体和名义工具的几何通路。\n'
p.write_text(s)
p=BASE/'ENGINEERING.md';s=p.read_text().replace('V1.2-M1.51','V1.2-M1.52')
s=re.sub(r'(当前模型SHA256 `)[0-9a-f]{64}(`)',lambda m:m[1]+source+m[2],s)
values={'整机已建模质量':f'{engineering["totals"]["whole"]["mass_g"]/1000:.3f} kg',
        '本体打印件':f'{engineering["totals"]["prints"]["mass_g"]:.1f} g',
        '俯仰总成':f'{engineering["totals"]["pitch"]["mass_g"]:.1f} g',
        'Yaw总成（含俯仰）':f'{engineering["totals"]["yaw"]["mass_g"]:.1f} g',
        '零位重心高度':f'{engineering["totals"]["whole"]["COM_mm"][2]:.2f} mm',
        '最大采样俯仰重力矩':f'{max(abs(r["pitch_gravity_Nm"]) for r in engineering["head_poses"]):.5f} N·m'}
for name,value in values.items():s=re.sub(r'\| '+re.escape(name)+r' \| [^|]+ \|','| '+name+' | '+value+' |',s)
p.write_text(s)
(M/'animation/CHANGELOG_M1.52_A1.md').write_text('# M1.52-A1\n\n两枚反力连接试配螺母与六角槽对齐；仅绕原轴旋转30°。当前模型及全视频同步，前后分壳的22步骤和85.75秒时长保持。上部夹口仍按预装总成演示，初装和实际舵盘/五金接口未完成。\n')
subprocess.run([sys.executable,str(M/'scripts/publish_animation_update.py')],check=True,cwd=ROOT)
(OUT/'publication.json').write_text(json.dumps(dict(status='PASS',revision=rev,source_blend_sha256=source,published_utc=stamp,
  scope='Two existing trial nut orientations only; no manufacturing release',unchanged_exports=21,unchanged_native_parts=199,
  protected_hardware_files=len(prep['protected_hardware']),command=[sys.executable,str(Path(__file__))],
  python=sys.version,script_sha256=sha(Path(__file__))),ensure_ascii=False,indent=2)+'\n')
print('M1_52_PUBLISHED',flush=True)
