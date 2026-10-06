"""Publish M1.50, retaining prior structural approvals and unresolved work."""
from pathlib import Path
import datetime,hashlib,html,json,re,subprocess,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];M=ROOT/'mechanical';S=OUT.parent
sys.path.insert(0,str(M/'scripts'))
from parts_classification import generate as parts_view
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
p=read(ROOT/'config/geometry.json');rev=p['revision'];assert rev=='V1.2-M1.50'
source=sha(M/'mori_v1_2.blend');stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
check=read(OUT/'check.json');v=read(M/'reports/validation.json');ex=read(M/'reports/export_manifest.json')
render=read(OUT/'render_manifest.json');am=read(M/'animation/manifest.json');av=read(M/'animation/validation.json')
eng=read(S/'engineering_current.json');electronic=read(M/'reports/electronics_detail_manifest.json')
assert v['counts']['FAIL']==0 and ex['exported_count']==21 and all(x['status']=='PASS' for x in ex['parts'])
assert all(x['status']=='PASS' for x in [check,render,av,eng,read(M/'reports/delivery_consistency.json')])
assert check['sources']['mechanical/mori_v1_2.blend']==source
assert all(x['source_blend_sha256']==source for x in [render,am,eng])
assert electronic['source_main_sha256']==source
assert am['animation_revision']==rev+'-A1' and am['rendered_video']
assert check['changed_native_parts']==['CAM_Mainboard'] and check['unchanged_native_parts']==208
prep=read(OUT/'preparation.json');prior_ex=read(ROOT/prep['snapshot_root']/'mechanical/reports/export_manifest.json')
prior_stls={r['id']:r['sha256'] for r in prior_ex['parts']}
assert {r['id']:r['sha256'] for r in ex['parts']}==prior_stls
assert all(sha(ROOT/n)==h for n,h in prep['protected_hardware'].items())

work=read(S/'work_status.json')
work.update(revision=rev,source_blend_sha256=source,updated_utc=stamp,status='BLOCKED',manufacturing_release=False)
done={r['id']:r for r in work['completed']}
done['cam_entry_M1_50']=dict(id='cam_entry_M1_50',status='PASS',
    detail='CAM相机入口朝上、屏幕入口朝板外，按官方已插线照片修正。仅两个重建插座变化，另208件和130组CAM元件保持；132组均保留证据等级。真实配合仍BLOCKED。',
    evidence='cam_entry_adoption/index.html')
done['geometry_delivery']=dict(id='geometry_delivery',status='PASS',
    detail=f'{rev}主模型、当前渲染与电子细模同步；21件STL与M1.49逐文件相同。主检查{v["counts"]["PASS"]} PASS / 0 FAIL；未完成接口状态保留。',evidence='cam_entry_adoption/index.html')
done['animation']=dict(id='animation',status='PASS',detail=f'{am["animation_revision"]}，{am["duration_seconds"]}秒、{am["frame_range"][1]}帧，来源实体及视频回读通过；完整线束与反力夹最终工序未完成。')
done['engineering']=dict(id='engineering',status='PASS',detail=f'{rev}名义质量与390个姿态计算同步；不是称重、承载或平衡验证。')
work['completed']=list(done.values())
work['cam_entry_adoption']=dict(status='PASS',revision=rev,source_blend_sha256=source,
    scope='Only two CAM reconstructed entries; no printed/board/hole changes',evidence='cam_entry_adoption/index.html',exact_mating='BLOCKED')
mass=eng['totals']['whole']['mass_g']
for row in work['remaining']:
    if row['id']=='harness':
        row['detail']='C5＋K1已采用；C6、滑动导线约束与前后分壳仍是未采用候选。M1.49研究完成了部分端部、固定和拆装检查，但完整恒定材料长度的线束、其余端部、应力释放及带线合壳未完成。M1.50只修正CAM两处排线入口，不代表整套线路已通过。'
        row['latest_entry_correction_evidence']='cam_entry_adoption/index.html'
        row['latest_body_split_candidate']='head_harness_M1_49/remaining_routes/cam_restraints/body_front_rear_split/index.html'
        row['candidate_requires_user_approval']=True
    elif row['id']=='reaction_assembly':
        row['detail']='前后分壳候选已有刚体和工具可达性检查，尚待用户确认，不能用于当前上下分壳的完成声明。反力夹局部修正、与线束共存的完整初装和最终舵盘接口仍未关闭。'
    elif row['id']=='supplier_interfaces':
        row['detail']='CAM相机/屏幕排线出口方向已有官方照片依据并已修正模型。连接器接触面、插深、补强片、实际版本及完整相机FPC仍缺；SCS0009舵盘/短轴锁紧、S288输出螺钉、WeAct E孔针和真实线尾仍未定。'
    elif row['id']=='load_budget':
        row['detail']=f'{rev}已建模名义质量{mass/1000:.3f}kg，超过1.0–1.2kg目标。另两颗制动电阻标称共3.8g，未选模块、完整线束及热隔离固定仍缺；不是实物称重。'
write(S/'work_status.json',work)
status=read(M/'reports/interface_completion_status.json')
status.update(revision=rev,source_blend_sha256=source,project_digital_release='BLOCKED',
    current_work_status='studies/prearrival_finish/work_status.json')
status['pending']=[dict(item='7',status='BLOCKED',detail='P5R7已应用；WeAct E针孔与真实啮合资料仍待确认。')]+work['remaining']
write(M/'reports/interface_completion_status.json',status)

engineering=(S/'ENGINEERING.md').read_text()
engineering=re.sub(r'^# .*? 当前质量与载荷计算',f'# {rev} 当前质量与载荷计算',engineering,count=1)
engineering=re.sub(r'来自当前模型SHA256 `[^`]+`',f'来自当前模型SHA256 `{source}`',engineering,count=1)
metrics={'整机已建模质量':f'{mass/1000:.3f} kg','本体打印件':f'{eng["totals"]["prints"]["mass_g"]:.1f} g',
 '俯仰总成':f'{eng["totals"]["pitch"]["mass_g"]:.1f} g','Yaw总成（含俯仰）':f'{eng["totals"]["yaw"]["mass_g"]:.1f} g',
 '零位重心高度':f'{eng["totals"]["whole"]["COM_mm"][2]:.2f} mm',
 '最大采样俯仰重力矩':f'{max(abs(r["pitch_gravity_Nm"]) for r in eng["head_poses"]):.5f} N·m'}
for label,value in metrics.items():
    engineering,n=re.subn(r'\| '+re.escape(label)+r' \| [^\n]+ \|',f'| {label} | {value} |',engineering);assert n==1
engineering=re.sub(r'当前超出的[0-9.]+g',f'当前超出的{mass-1200:.1f}g',engineering)
torques={r['axis']:r['stress_scenario_Nm'] for r in eng['head_scenarios'] if r['acceleration_rad_s2']==20}
engineering=re.sub(r'20rad/s²时俯仰约[0-9.]+N·m、Yaw约[0-9.]+N·m',
    f'20rad/s²时俯仰约{torques["pitch"]:.5f}N·m、Yaw约{torques["yaw"]:.5f}N·m',engineering)
(S/'ENGINEERING.md').write_text(engineering)

style='''<style>*{box-sizing:border-box}body{background:#edf1f0;color:#243a33;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;margin:0}main{max-width:1120px;margin:auto;padding:28px 24px 64px}h1{font-size:32px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border:1px solid #ccd8d1;border-radius:9px;overflow:hidden}img{width:100%;display:block}figcaption{padding:14px}a{color:#146c53}.notice{background:#fff2d8;padding:16px;border-radius:8px}.done{background:#dcece3}td,th{padding:11px;border-bottom:1px solid #ccd8d1;text-align:left;vertical-align:top}table{width:100%;border-collapse:collapse}nav{display:flex;gap:16px;flex-wrap:wrap}code{overflow-wrap:anywhere}@media(max-width:760px){.grid{grid-template-columns:1fr}h1{font-size:26px}}</style>'''
def page(title,body):return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>{style}<main>{body}</main></html>'
description='CAM相机排线入口修正为朝上（+Z），屏幕排线入口修正为朝板外（−X）。保留板卡、安装孔、打印件和原插座包络；屏幕插座的白色壳体/黑色拨片位置没有整体翻转。'
limits='照片只支持入口方向。示意插槽及触点仍为ASSUMED，真实插深、接触面、补强片和供货版本未确认，不能用于放行实际插接。'
figures=''.join(f'<figure><img src="{name}.png"><figcaption>{label}</figcaption></figure>' for name,label in [
    ('camera_entry','当前主模型：相机入口朝上。'),('display_entry','当前主模型：屏幕入口朝板外，未翻转整个插座。')])
remaining=''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}</td></tr>' for r in work['remaining'])
body=f'''<nav><a href="../../../index.html?revision={rev}#cam-entry">当前总装</a><a href="../../../animation/index.html?revision={am['animation_revision']}">新版视频</a></nav><h1>CAM两处排线入口已修正</h1><p>{rev} · {stamp}</p><p class="notice done">主模型、电子细模、预览与装配视频已同步。C5＋K1结构保留。</p><p>{description}</p><div class="grid">{figures}</div><p class="notice">{limits}</p><h2>改动范围与检查</h2><p>209个机器人零件中仅CAM_Mainboard变化，另外208件实体及CAM板内130个元件组保持。实际保存模型与独立候选的最大坐标差为{check['candidate_max_coordinate_error_mm']:.8f}mm（浮点存储），面连接相同；132个元件组没有删减。262组同板新增材料检查及130个头部姿态未检出新增干涉。</p><p>21件主STL与M1.49逐文件相同，机器人仍为16件打印件。主检查{v['counts']['PASS']} PASS / 0 FAIL；{v['counts']['BLOCKED']} BLOCKED、{v['counts']['NOT_TESTED']} NOT_TESTED继续保留。</p><p><a href="check.json">实际保存模型比对</a> · <a href="commands.json">命令与日志</a> · <a href="../../../reports/validation.json">当前检查</a> · <a href="../head_harness_M1_49/remaining_routes/static_flex/connector_faces/direction_receipt.json">官方照片资料接收记录</a></p><h2>历史资料与未完成工作</h2><p>M1.49研究按原版本阅读，未宣称整套线束已重新通过。已保存M1.49模型、脚本、配置、STL与视频快照。C6、导线约束和前后分壳均未应用。</p><p><a href="../head_harness_M1_49/remaining_routes/cam_restraints/body_front_rear_split/index.html">待确认的前后分壳候选（M1.49）</a> · <a href="../work_status.json">完整工作状态</a></p><table>{remaining}</table><p class="notice">PROTOTYPE / UNVALIDATED；没有制造、采购或实物配合放行。</p><small>当前主模型 SHA256：<code>{source}</code></small>'''
(OUT/'index.html').write_text(page('MORI M1.50 · CAM入口修正',body))
index=M/'index.html';text=index.read_text()
text=re.sub(r'<title>MORI V1\.2-M1\.\d+</title>',f'<title>MORI {rev}</title>',text,count=1)
text=re.sub(r'<b>MORI V1\.2-M1\.\d+</b>',f'<b>MORI {rev}</b>',text,count=1)
text=re.sub(r'<h1>.*?</h1>','<h1>CAM排线入口已修正。</h1>',text,count=1,flags=re.S)
section=f'''<section id="cam-entry"><h2>本轮：CAM排线入口</h2><p>{description}</p><p>{limits}</p><div class="grid">{figures.replace('src="','src="studies/prearrival_finish/cam_entry_adoption/')}</div><p><a href="studies/prearrival_finish/cam_entry_adoption/index.html">范围、来源与检查</a></p></section>'''
text=re.sub(r'<section id="cam-entry">.*?</section>','',text,flags=re.S)
text=text.replace('<section id="neck-capacity">',section+'<section id="neck-capacity">',1)
text=text.replace('<a href="#neck-capacity">本轮颈部修正</a>','<a href="#cam-entry">本轮CAM入口</a><a href="#neck-capacity">已采用颈部修正</a>',1)
text=re.sub(r'(renders/(?!p5r7/)[^"?]+\.png)\?revision=V1\.2-M1\.\d+',r'\1?revision='+rev,text)
text,n=re.subn(r'<section id="remaining">.*?</section>',f'<section id="remaining"><h2>当前剩余项目</h2><table>{remaining}</table><p><a href="studies/prearrival_finish/work_status.json">完整状态</a></p></section>',text,flags=re.S);assert n==1
text,n=re.subn(r'<section id="checks">.*?</section>',f'<section id="checks"><h2>检查与文件</h2><p>{v["counts"]["PASS"]} PASS / 0 FAIL；{v["counts"]["BLOCKED"]} BLOCKED、{v["counts"]["NOT_TESTED"]} NOT_TESTED保留。21件STL与M1.49相同；当前模型、预览、电子细模与视频已同步。</p><p>完整线束、反力连接初装、供应商接口与质量预算尚未关闭；几何通过不等于实物通过。</p></section>',text,flags=re.S);assert n==1
index.write_text(text)
overview=S/'index.html';t=overview.read_text()
t=re.sub(r'<div class="notice done" id="M1-50-adopted">.*?</div>','',t,flags=re.S)
t=t.replace('<main>',f'<main><div class="notice done" id="M1-50-adopted"><b>{rev}：CAM两处排线入口已同步到主模型。</b> <a href="cam_entry_adoption/index.html">本轮交付</a>。下方研究保留其原始版本；完整线束及结构候选仍未完成或未采用。</div>',1);overview.write_text(t)
previews=read(M/'reports/parts_preview_manifest.json');bom=read(M/'reports/bom.json')
manufacturing=parts_view(M,rev,bom,previews,ex)
(M/'manufacturing.html').write_text(page(f'{rev}打印件与五金',f'<a href="index.html#cam-entry">当前模型</a><h1>{rev}打印件与五金</h1><p class="notice">本体16件PA12打印件，本轮打印几何不变；21件STL与M1.49一致。未制造放行。</p><p><a href="studies/prearrival_finish/neck_adoption/fit_coupons/index.html">6806试配片（M1.49，配合尺寸未改变）</a></p>{manufacturing}'))
(M/'parts.html').write_text(page(f'{rev}部件预览',f'<a href="index.html">当前总装</a><h1>{rev}部件预览</h1><div class="grid">'+''.join(f'<figure><img loading="lazy" src="{r["file"]}?revision={rev}"><figcaption>{html.escape(r["id"]+" · "+r["name"])}</figcaption></figure>' for r in previews)+'</div>'))
readme=f'''# MORI {rev}

CAM相机与屏幕排线入口按官方照片修正；仅两个重建插座变化，另外208件实体及130组板内元件保持。C5＋K1、全部打印件与安装孔保持；21件STL与M1.49逐文件相同。

主模型、电子细模、预览及{am['animation_revision']}已同步。主检查{v['counts']['PASS']} PASS / 0 FAIL；未确认接口仍为BLOCKED/NOT_TESTED。排线接触面、插深、补强片和实物版本尚未确认。

完整线束、反力连接初装、部分供应商接口和质量预算尚未完成。前后分壳、C6及导线约束仍是未采用候选。PROTOTYPE / UNVALIDATED。
'''
(M/'README.md').write_text(readme+'\n[本轮详情](studies/prearrival_finish/cam_entry_adoption/index.html) · [装配动画](animation/index.html) · [未完成工作](studies/prearrival_finish/work_status.json)\n')
(OUT/'README.md').write_text(readme+'\n[保存模型比对](check.json) · [执行命令](commands.json) · [快照清单](preparation.json)\n')
changelog=M/'animation'/('CHANGELOG_'+am['animation_revision'].removeprefix('V1.2-').replace('-','_')+'.md')
changelog.write_text(f'''# {am['animation_revision']}

来源：{rev}主模型 SHA256 `{source}`。

CAM两处排线入口按官方已插线照片修正。打印件、板卡位置、孔位和装配步骤保持；视频重新渲染并回读，{am['duration_seconds']}秒/{am['frame_range'][1]}帧。

插槽和触点仍是示意；完整线束、反力连接初装与最终舵盘接口未完成。视频不能作为完整带线工艺已通过的证明。
''')
subprocess.run([sys.executable,str(M/'scripts/publish_animation_update.py')],cwd=ROOT,check=True)
write(OUT/'publication.json',dict(status='PASS',revision=rev,utc=stamp,source_blend_sha256=source,
    animation_revision=am['animation_revision'],printed_geometry_changed=False,STL_bytes_unchanged=21,
    full_harness='BLOCKED',manufacturing_release=False,historical_snapshot=prep['snapshot_root']))
print('CAM_ENTRY_M1_50_PUBLISHED',v['counts'],flush=True)
