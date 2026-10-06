"""Publish the approved C5 + K1 neck, after current geometry/media readback."""
import datetime, hashlib, html, json, re, subprocess, sys
from pathlib import Path
OUT=Path(__file__).resolve().parent; S=OUT.parent; M=OUT.parents[2]; P=M.parent
sys.path.insert(0,str(M/'scripts'))
from parts_classification import generate as parts_view
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,q):p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
g=read(P/'config/geometry.json');rev=g['revision'];assert rev=='V1.2-M1.49'
source=sha(M/'mori_v1_2.blend')
audit=read(M/'reports/neck_capacity_validation.json');ret=read(M/'reports/head_axial_retention_validation.json')
v=read(M/'reports/validation.json');ex=read(M/'reports/export_manifest.json')
am=read(M/'animation/manifest.json');av=read(M/'animation/validation.json')
delivery=read(M/'reports/delivery_consistency.json');render=read(OUT/'render_manifest.json')
eng=read(S/'engineering_current.json');electronic=read(M/'reports/electronics_detail_manifest.json')
coupon=read(OUT/'fit_coupons/manifest.json')
assert all(r['status']=='PASS' for r in [audit,ret,av,delivery,eng,coupon])
assert v['counts']['FAIL']==0 and ex['exported_count']==21 and all(r['status']=='PASS' for r in ex['parts'])
assert am['animation_revision']==rev+'-A1' and am['rendered_video']
assert all(h==source for h in [audit['source_blend_sha256'],ret['source_blend_sha256'],am['source_blend_sha256'],render['source_blend_sha256'],eng['source_blend_sha256'],electronic['source_main_sha256'],coupon['source_blend_sha256']])
assert audit['scope']['unchanged_count']==201 and len(audit['scope']['changed'])==8
assert sha(OUT/'keeper_wall_verification.json')==read(OUT/'keeper_wall_approval.json')['verification_sha256']
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
gap=audit['head_shell_gaps']['minimum']['gap_mm'];wall=min(r['minimum_mm'] for r in audit['generated_side_wall']['rows'])
mass=eng['totals']['whole']['mass_g']

note=(S/'ENGINEERING.md').read_text()
note=re.sub(r'^# .*? 当前质量与载荷计算',f'# {rev} 当前质量与载荷计算',note,count=1)
note=re.sub(r'来自当前模型SHA256 `[^`]+`',f'来自当前模型SHA256 `{source}`',note,count=1)
metrics={'整机已建模质量':f'{mass/1000:.3f} kg','本体打印件':f'{eng["totals"]["prints"]["mass_g"]:.1f} g','俯仰总成':f'{eng["totals"]["pitch"]["mass_g"]:.1f} g','Yaw总成（含俯仰）':f'{eng["totals"]["yaw"]["mass_g"]:.1f} g','零位重心高度':f'{eng["totals"]["whole"]["COM_mm"][2]:.2f} mm','最大采样俯仰重力矩':f'{max(abs(r["pitch_gravity_Nm"]) for r in eng["head_poses"]):.5f} N·m'}
for label,value in metrics.items():
    note,n=re.subn(r'\| '+re.escape(label)+r' \| [^\n]+ \|',f'| {label} | {value} |',note);assert n==1
note=re.sub(r'当前超出的[0-9.]+g',f'当前超出的{mass-1200:.1f}g',note)
torques={r['axis']:r['stress_scenario_Nm'] for r in eng['head_scenarios'] if r['acceleration_rad_s2']==20}
note=re.sub(r'20rad/s²时俯仰约[0-9.]+N·m、Yaw约[0-9.]+N·m',f'20rad/s²时俯仰约{torques["pitch"]:.5f}N·m、Yaw约{torques["yaw"]:.5f}N·m',note)
(S/'ENGINEERING.md').write_text(note)

work=read(S/'work_status.json')
work.update(revision=rev,source_blend_sha256=source,updated_utc=stamp,status='BLOCKED',manufacturing_release=False)
harness_detail=f'C5颈部容量方案与K1孔壁修正已应用M1.49：6806ZZ30×42×7轴承、三件现有打印件及四枚配对紧固件位置同步。11条局部规划导线通过当前模型的130姿态检查；头壳最小采样净距{gap:.3f}mm、过渡侧壁采样{wall:.3f}mm。七条Ø1.4224仍为规划包络，并非已选SH/GH线材。完整端部连接、线间排布、固定/应力释放、带线装配和供应商制作图仍未完成。'
for r in work['remaining']:
    if r['id']=='harness':
        r.update(detail=harness_detail,evidence='neck_adoption/index.html',latest_capacity_detail=harness_detail,latest_capacity_evidence='neck_adoption/index.html')
    elif r['id']=='reaction_assembly':
        r['detail']='反力夹口局部薄边及初装仍未修复。历史M1.47复核中的直柄工具及反力件上移路线失败；本轮颈部调整未改反力夹本身，但必须在当前总成上重新规划并检查初装。不能把无软线的压板/轴承装入PASS当作反力连接已完成；最终舵盘资料仍缺。'
    elif r['id']=='load_budget':
        r['detail']=f'M1.49名义已建模质量{mass/1000:.3f}kg，超过1.0–1.2kg工程目标。两颗未布置制动电阻另计标称3.8g，候选部分合计{(mass+3.8)/1000:.3f}kg；未选模块、完整线束和热隔离固定仍缺。不是称重或动力学验证。'
completed={r['id']:r for r in work['completed']}
completed['neck_capacity_M1_49']=dict(id='neck_capacity_M1_49',status='PASS',detail='已采用C5与K1。配对孔X±26.2mm，压板外径60.4mm，外围环内径61.0mm/外径65.4mm；嵌件孔名义最薄侧壁1.675mm。未增加机器人零件。',evidence='neck_adoption/index.html')
completed['geometry_delivery']=dict(id='geometry_delivery',status='PASS',detail=f'M1.49主模型、21件STL、当前常规渲染及电子细模同步；主检查{v["counts"]["PASS"]} PASS / 0 FAIL；既有BLOCKED/NOT_TESTED保留。')
completed['animation']=dict(id='animation',status='PASS',detail=f'{am["animation_revision"]}，{am["duration_seconds"]}秒、{am["frame_range"][1]}帧、22章，实体与字幕更新并回读。反力夹初装及完整线束未完成的限制保留。')
completed['engineering']=dict(id='engineering',status='PASS',detail='M1.49的209实体名义质量与390姿态计算已同步；质量目标及执行器能力仍未关闭。')
completed['6806_coupons']=dict(id='6806_coupons',status='PASS',detail='新建两片独立PA12试配片，包含42.1mm座孔及29.9mm轴颈当前名义尺寸；STL实际回读通过，尚未打印或试配。',evidence='neck_adoption/fit_coupons/index.html')
work['completed']=list(completed.values())
work['neck_adoption']=dict(status='PASS',revision=rev,source_blend_sha256=source,source_approval='neck_adoption/approval.json',wall_approval='neck_adoption/keeper_wall_approval.json',evidence='neck_adoption/index.html',full_harness='BLOCKED')
write(S/'work_status.json',work)
sp=M/'reports/interface_completion_status.json';status=read(sp)
status.update(revision=rev,source_blend_sha256=source,project_digital_release='BLOCKED')
status['pending']=[dict(item='7',status='BLOCKED',detail='P5R7已应用；WeAct E针孔及真实啮合仍待资料。')]+work['remaining'];write(sp,status)

style='''<style>*{box-sizing:border-box}body{background:#edf1f0;color:#243a33;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;margin:0}main{max-width:1120px;margin:auto;padding:28px 24px 64px}h1{font-size:32px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border:1px solid #ccd8d1;border-radius:9px;overflow:hidden}img{width:100%;display:block}figcaption{padding:14px}a{color:#146c53}.notice{background:#fff2d8;padding:16px;border-radius:8px}.done{background:#dcece3}td,th{padding:11px;border-bottom:1px solid #ccd8d1;text-align:left;vertical-align:top}table{width:100%;border-collapse:collapse}nav{display:flex;gap:16px;flex-wrap:wrap}code{overflow-wrap:anywhere}@media(max-width:760px){.grid{grid-template-columns:1fr}h1{font-size:26px}}</style>'''
change='偏航轴承改为6806ZZ（30×42×7mm）；沿用三件现有颈部打印件。两侧配对孔及螺钉/嵌件各向外移动0.2mm，嵌件孔最薄侧壁恢复至名义1.675mm。压板外径60.4mm，外围环内径61.0mm、外径65.4mm。'
assembly='''<ol><li>桥座离机预装嵌件、螺母与6806轴承。</li><li>C形压板从侧面套入偏航转动座，与预装舵机的转动座一起下放；俯仰头托后装。</li><li>偏航转动座转至+60°，用2mm内六角扳手从上方锁紧两枚M3×8，再回零位。压板固定在桥座上，不随头部转动。</li><li>再装俯仰头托与头壳。维修时先拆俯仰总成；反力夹初装与完整带线工序仍待完成。</li></ol>'''
section=f'''<section id="neck-capacity"><h2>颈部通道与压板孔壁已修正</h2><p>{change}机器人打印件仍为16件；头壳、光学与舵机位置保持。</p><div class="grid"><figure><img src="studies/prearrival_finish/neck_adoption/supports.png?revision={rev}" alt="当前颈部支撑与防脱压板"><figcaption>当前主模型：6806轴承与配对移动后的压板螺钉。</figcaption></figure><figure><img src="studies/prearrival_finish/neck_adoption/local_wires.png?revision={rev}" alt="颈部11条局部规划导线"><figcaption>橙色是11条局部空间样线，未作为完整线束加入主模型。</figcaption></figure></div><p><a href="studies/prearrival_finish/neck_adoption/index.html">本轮检查与装配说明</a> · <a href="studies/prearrival_finish/neck_adoption/keeper_wall_index.html">孔壁实际剖面对比</a> · <a href="studies/prearrival_finish/neck_adoption/fit_coupons/index.html">6806试配片</a></p></section>'''
index=M/'index.html';text=index.read_text()
text=re.sub(r'<title>MORI V1\.2-M1\.\d+</title>',f'<title>MORI {rev}</title>',text,count=1)
text=re.sub(r'<b>MORI V1\.2-M1\.\d+</b>',f'<b>MORI {rev}</b>',text,count=1)
text=re.sub(r'<h1>.*?</h1>','<h1>颈部通道与压板孔壁已修正。</h1>',text,count=1,flags=re.S)
text=re.sub(r'<aside id="M1-48-[^"]+".*?</aside>','',text,flags=re.S)
text=re.sub(r'<section id="neck-capacity">.*?</section>','',text,flags=re.S)
text=text.replace('<section id="camera-cam">',section+'<section id="camera-cam">',1)
text=text.replace('<a href="#neck-capacity">本轮颈部修正</a>','')
text=text.replace('<a href="#camera-cam">本轮相机/CAM</a>','<a href="#neck-capacity">本轮颈部修正</a><a href="#camera-cam">相机/CAM</a>',1)
text=re.sub(r'(renders/(?!p5r7/)[^"?]+\.png)\?revision=V1\.2-M1\.\d+',r'\1?revision='+rev,text)
text=text.replace('当前主模型实际坐标；隐藏外壳便于检查，未移动或缩放硬件。','M1.47板卡交接视图；板卡尺寸与位置沿用，桥座以当前颈部视图为准。')
head=f'''<section id="head-retention"><h2>头部与身体如何防脱</h2><p>C形PA12压板通过两枚M3×8和SL-M3×4嵌件锁在固定桥座上，挡住偏航转动座的轴肩。保留0.4mm名义轴向间隙，不是轴承预紧。当前轴承6806ZZ，压板固定孔X±26.2mm。</p>{assembly}<p><a href="studies/prearrival_finish/neck_adoption/keeper_wall_index.html">当前孔壁剖面</a> · <a href="reports/head_axial_retention_validation.json">当前实体及装入检查</a> · <a href="animation/index.html">装配视频</a>。实际承载与PA12蠕变需试件验证。</p></section>'''
text,n=re.subn(r'<section id="head-retention">.*?</section>',head,text,flags=re.S);assert n==1
rows=''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}</td></tr>' for r in work['remaining'])
text,n=re.subn(r'<section id="remaining">.*?</section>',f'<section id="remaining"><h2>当前剩余项目</h2><table>{rows}</table><p><a href="studies/prearrival_finish/work_status.json">完整状态记录</a></p></section>',text,flags=re.S);assert n==1
checks=f'''<section id="checks"><h2>检查与文件</h2><p>主检查{v['counts']['PASS']} PASS / 0 FAIL；{v['counts']['BLOCKED']} BLOCKED、{v['counts']['NOT_TESTED']} NOT_TESTED保留。21/21主导出STL拓扑及实际回读通过；新轴承另有2片独立试配片。重建、当前预览、电子细模与视频来源已核对。</p><p class="notice">完整线束、反力连接初装、部分供应商接口和质量预算仍未关闭。名义几何检查不代表实物配合或打印强度通过。</p></section>'''
text,n=re.subn(r'<section id="checks">.*?</section>',checks,text,flags=re.S);assert n==1
index.write_text(text)
body=f'''<p class="notice done">C5与K1均已按用户确认应用。主模型、STL、预览、电子细模与{am['animation_revision']}已同步。</p><p>{change}</p><p>与M1.48逐件比较，共8个现有对象变化，其余201件实体几何与位置保持。机器人仍为16件打印件，未增加螺钉。七条粗线只是容量规划，不能当作已选微型连接器线材。</p><div class="grid"><figure><img src="supports.png"><figcaption>当前保存模型的颈部与防脱结构。</figcaption></figure><figure><img src="local_wires.png"><figcaption>11条局部样线；尚未连接两端，也未完成固定和带线装配。</figcaption></figure></div><h2>压板孔壁修正</h2><figure><img src="keeper_wall_comparison.png"><figcaption>原C5与已采用K1实体剖面。1.6mm是设计预留，不是强度认证。</figcaption></figure><h2>装配方法</h2>{assembly}<h2>本轮检查</h2><p>125项通过、0项失败。批准候选实体比对、配对孔/嵌件材料、130个头部组合姿态、压板侧向装入、轴承和头座下放、螺钉与工具空间及21件STL回读通过。局部头壳最小采样净距{gap:.3f}mm；生成过渡侧壁采样{wall:.3f}mm。硬件原生文件及合同581份哈希保持。</p><p><a href="../../../reports/neck_capacity_validation.json">颈部实体检查</a> · <a href="../../../reports/head_axial_retention_validation.json">防脱与装入检查</a> · <a href="keeper_wall_index.html">孔壁修正与确认</a> · <a href="commands.json">执行命令</a> · <a href="fit_coupons/index.html">6806 PA12试配片</a> · <a href="../../../animation/index.html?revision={am['animation_revision']}">当前装配视频</a></p><h2>仍未关闭</h2><table>{rows}</table><p class="notice">PROTOTYPE / UNVALIDATED。没有制造或采购放行；完整线束及反力连接初装仍有数字设计工作。PA12强度、实际配合与动态验证待实物。</p><small>当前主模型 SHA256：<code>{source}</code></small>'''
(OUT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.49 · 颈部与压板</title>{style}<main><nav><a href="../../../index.html?revision={rev}#neck-capacity">当前总装</a><a href="../index.html">到货前工作</a></nav><h1>颈部通道与压板孔壁已修正</h1><p>{rev} · {stamp}</p>{body}</main></html>')
overview=S/'index.html';t=overview.read_text()
t=re.sub(r'<div class="notice done" id="M1-49-adopted">.*?</div>','',t,flags=re.S)
t=t.replace('<main>',f'<main><div class="notice done" id="M1-49-adopted"><b>{rev}：6806颈部与压板孔壁修正已应用。</b> <a href="neck_adoption/index.html">当前交付</a> · <a href="neck_adoption/fit_coupons/index.html">新轴承试配片</a>。下方旧研究按其记录版本阅读；完整线束仍未完成。</div>',1);overview.write_text(t)
previews=read(M/'reports/parts_preview_manifest.json');bom=read(M/'reports/bom.json')
manufacturing=parts_view(M,rev,bom,previews,ex)
(M/'manufacturing.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html#neck-capacity">当前模型</a><h1>{rev}打印件与五金</h1><p class="notice">本体16件PA12打印件。Yaw轴承为采购件6806ZZ30×42×7；压板螺钉和嵌件也是五金。此页是候选文件，未制造放行。</p><p><a href="studies/prearrival_finish/neck_adoption/fit_coupons/index.html">另附2片6806试配片</a>，不计入机器人零件。原32/20mm试片不用于当前Yaw配合。</p>{manufacturing}</main></html>')
(M/'parts.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html">当前总装</a><h1>{rev}部件预览</h1><div class="grid">'+''.join(f'<figure><img loading="lazy" src="{r["file"]}?revision={rev}"><figcaption>{html.escape(r["id"]+" · "+r["name"])}</figcaption></figure>' for r in previews)+'</div></main></html>')
readme=f'''# MORI {rev}

已应用C5颈部容量方案与K1孔壁修正：6806ZZ30×42×7轴承；配对孔X±26.2mm，压板OD60.4、外围环ID61.0/OD65.4，嵌件孔名义最薄侧壁1.675mm。机器人仍16件打印件；无新增紧固件。

当前209件机器人实体中8件相对M1.48变化，其余201件几何和位置保持。主检查{v['counts']['PASS']} PASS / 0 FAIL；{v['counts']['BLOCKED']} BLOCKED、{v['counts']['NOT_TESTED']} NOT_TESTED保留。主STL21件与{am['animation_revision']}同步。另附2片独立6806试配片。

完整端部走线、固定/应力释放、带线装配、反力夹初装及部分供应商资料仍未完成。局部11线通过不是完整线束通过。PROTOTYPE / UNVALIDATED；几何检查不代表实物配合或打印强度。
'''
(M/'README.md').write_text(readme+'\n[本轮说明](studies/prearrival_finish/neck_adoption/index.html) · [当前Blender](mori_v1_2.blend) · [装配动画](animation/index.html) · [6806试配片](studies/prearrival_finish/neck_adoption/fit_coupons/index.html) · [剩余任务](studies/prearrival_finish/work_status.json)\n')
(OUT/'README.md').write_text(readme+'\n[本轮确认](approval.json) · [K1确认](keeper_wall_approval.json) · [执行命令](commands.json) · [当前几何检查](../../../reports/neck_capacity_validation.json)\n')
changelog=M/'animation'/('CHANGELOG_'+am['animation_revision'].removeprefix('V1.2-').replace('-','_')+'.md')
changelog.write_text(f'''# {am['animation_revision']}

来源：当前{rev}主模型，SHA256 `{source}`。

- 应用6806ZZ轴承、三件颈部打印件及K1配对孔/紧固件位置修正。
- 第9章字幕指定6806轴承；保留C压板侧套、随转动座下放、转60°锁紧的顺序。
- 视频{am['duration_seconds']}秒、{am['frame_range'][1]}帧、24fps、1280×720、22章。原生实体与视频回读通过。

分解位移是装配讲解。完整线束、反力夹初装、供应商传动接口和实物配合未完成；不得据视频认定完整工艺已验证。
''')
subprocess.run([sys.executable,str(M/'scripts/publish_animation_update.py')],cwd=P,check=True)
write(OUT/'publication.json',dict(status='PASS',revision=rev,utc=stamp,source_blend_sha256=source,animation_revision=am['animation_revision'],scope='User-approved C5 and K1 only, plus current deliverables and independent fit coupons',full_harness='BLOCKED',manufacturing_release=False))
print('M1_49_PUBLISHED',source,v['counts'])
