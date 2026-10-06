"""Publish M1.48 only after current geometry and real video readback pass."""
import datetime,hashlib,html,json,re,sys,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent;S=OUT.parent;M=OUT.parents[2];P=M.parent
sys.path.insert(0,str(M/'scripts'))
from parts_classification import generate as parts_view
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
g=read(P/'config/geometry.json');rev=g['revision'];assert rev=='V1.2-M1.48'
source=sha(M/'mori_v1_2.blend');audit=read(M/'reports/camera_cam_completion_validation.json')
v=read(M/'reports/validation.json');ex=read(M/'reports/export_manifest.json')
am=read(M/'animation/manifest.json');av=read(M/'animation/validation.json')
delivery=read(M/'reports/delivery_consistency.json');render=read(OUT/'render_manifest.json')
eng=read(S/'engineering_current.json');electronic=read(M/'reports/electronics_detail_manifest.json')
assert audit['status']==av['status']==delivery['status']==eng['status']=='PASS'
assert v['counts']['FAIL']==0 and all(p['status']=='PASS' for p in ex['parts'])
assert am['animation_revision']==rev+'-A1' and am['rendered_video']
assert all(x==source for x in [audit['source_blend_sha256'],am['source_blend_sha256'],render['source_blend_sha256'],eng['source_blend_sha256'],electronic['source_main_sha256']])
assert audit['scope']['unchanged_count']==204
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();gap=audit['camera_clearance']['shell_gap_mm']
engineering_note=S/'ENGINEERING.md';note=engineering_note.read_text()
note=re.sub(r'^# M1\.47 当前质量与载荷计算',f'# {rev} 当前质量与载荷计算',note,count=1)
note=re.sub(r'来自当前模型SHA256 `[^`]+`',f'来自当前模型SHA256 `{source}`',note,count=1)
metrics={
    '整机已建模质量':f'{eng["totals"]["whole"]["mass_g"]/1000:.3f} kg',
    '本体打印件':f'{eng["totals"]["prints"]["mass_g"]:.1f} g',
    '俯仰总成':f'{eng["totals"]["pitch"]["mass_g"]:.1f} g',
    'Yaw总成（含俯仰）':f'{eng["totals"]["yaw"]["mass_g"]:.1f} g',
    '零位重心高度':f'{eng["totals"]["whole"]["COM_mm"][2]:.2f} mm',
    '最大采样俯仰重力矩':f'{max(abs(r["pitch_gravity_Nm"]) for r in eng["head_poses"]):.5f} N·m',
}
for label,value in metrics.items():
    note,n=re.subn(r'\| '+re.escape(label)+r' \| [^\n]+ \|',f'| {label} | {value} |',note);assert n==1
note=re.sub(r'当前超出的[0-9.]+g',f'当前超出的{eng["totals"]["whole"]["mass_g"]-1200:.1f}g',note)
torques={r['axis']:r['stress_scenario_Nm'] for r in eng['head_scenarios'] if r['acceleration_rad_s2']==20}
note=re.sub(r'20rad/s²时俯仰约[0-9.]+N·m、Yaw约[0-9.]+N·m',f'20rad/s²时俯仰约{torques["pitch"]:.5f}N·m、Yaw约{torques["yaw"]:.5f}N·m',note)
engineering_note.write_text(note)
work=read(S/'work_status.json')
work.update(revision=rev,source_blend_sha256=source,updated_utc=stamp,status='BLOCKED',manufacturing_release=False)
work['remaining']=[r for r in work['remaining'] if r['id']!='head_front_contact']
for r in work['remaining']:
    if r['id']=='harness':
        r['detail']=r['detail'].replace('CAM内六角螺钉待确认','CAM内六角螺钉已于M1.48采用，当前无走线阶段工具/装入检查通过')
    elif r['id']=='reaction_assembly':
        r['detail']=r['detail'].replace('M1.47当前实体复核','M1.47局部实体复核（相关反力连接在M1.48保持）')
    elif r['id']=='load_budget':
        mass=eng['totals']['whole']['mass_g']
        r['detail']=f'M1.48名义已建模质量{mass/1000:.3f}kg，超过1.0–1.2kg工程目标。两颗未布置制动电阻另计标称3.8g，候选部分合计{(mass+3.8)/1000:.3f}kg；未选模块、完整线束和热隔离固定仍缺。不是称重或动力学验证。'
completed={r['id']:r for r in work['completed']}
completed['camera_CAM_M1_48']={'id':'camera_CAM_M1_48','status':'PASS','detail':f'相机支架上沿整条降低0.6mm，名义上壁1.2mm、前壳间隙{gap:.3f}mm；四枚CAM螺钉改为DIN912 M2×5。五件匹配确认候选，其余204件几何与位置保持。','evidence':'camera_cam_adoption/index.html'}
completed['geometry_delivery']={'id':'geometry_delivery','status':'PASS','detail':f'M1.48主模型、21件STL、当前常规渲染及电子细模同步；主检查{v["counts"]["PASS"]} PASS / 0 FAIL，既有BLOCKED/NOT_TESTED保留。'}
completed['animation']={'id':'animation','status':'PASS','detail':f'{am["animation_revision"]}，{am["duration_seconds"]}秒、{am["frame_range"][1]}帧、22章。实体与字幕已更新并回读；反力夹预装及完整线束未完成的限制保留。'}
completed['engineering']={'id':'engineering','status':'PASS','detail':'M1.48的209实体名义质量与390姿态计算已同步；质量目标及执行器能力仍未关闭。'}
work['completed']=list(completed.values())
work['camera_top_clearance_candidate'].update(main_applied=True,adopted_revision=rev,adoption_evidence='camera_cam_adoption/index.html',historical_candidate_source_revision='V1.2-M1.47')
work['camera_CAM_adoption']={'status':'PASS','revision':rev,'source_blend_sha256':source,'evidence':'camera_cam_adoption/index.html','scope':'Only two user-approved local changes; no wire/channel/electrical candidate adopted'}
write(S/'work_status.json',work)
statuspath=M/'reports/interface_completion_status.json';status=read(statuspath)
status.update(revision=rev,source_blend_sha256=source,project_digital_release='BLOCKED')
status['pending']=[dict(item='7',status='BLOCKED',detail='P5R7已应用；WeAct E针孔及真实啮合仍待资料。')]+work['remaining'];write(statuspath,status)
style='''<style>*{box-sizing:border-box}body{background:#edf1f0;color:#243a33;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;margin:0}main{max-width:1100px;margin:auto;padding:30px 24px 64px}h1{font-size:32px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border:1px solid #ccd8d1;border-radius:9px;overflow:hidden}img{width:100%;display:block}figcaption{padding:14px}a{color:#146c53}.notice{background:#fff2d8;padding:16px;border-radius:8px}.done{background:#dcece3}td,th{padding:12px;border-bottom:1px solid #ccd8d1;text-align:left;vertical-align:top}table{width:100%;border-collapse:collapse}nav,.links{display:flex;gap:16px;flex-wrap:wrap}@media(max-width:760px){.grid{grid-template-columns:1fr}h1{font-size:26px}}</style>'''
section=f'''<section id="camera-cam"><h2>相机与CAM固定修正已应用</h2><p>相机支架上沿整条降低0.6mm，上壁名义1.2mm；与前壳间隙约{gap:.3f}mm。四枚CAM固定螺钉改为DIN912 M2×5，头部Ø3.8×2mm。孔位、相机和板卡位置保持，零件数量不变。</p><div class="grid"><figure><img src="studies/prearrival_finish/camera_cam_adoption/camera_top.png?revision={rev}" alt="正式模型相机座连续平直上沿"><figcaption>正式Display Frame局部；没有增加台阶或开孔。</figcaption></figure><figure><img src="studies/prearrival_finish/camera_cam_adoption/cam_screws.png?revision={rev}" alt="正式CAM螺钉和短边L扳手包络"><figcaption>四枚内六角螺钉。绿色为工具示意，不是新增机器人零件。</figcaption></figure></div><p><a href="studies/prearrival_finish/camera_cam_adoption/index.html">本轮检查与装配说明</a> · <a href="reports/camera_cam_completion_validation.json">当前模型检查记录</a></p></section>'''
index=M/'index.html';text=index.read_text()
text=text.replace('<title>MORI V1.2-M1.47</title>',f'<title>MORI {rev}</title>').replace('<b>MORI V1.2-M1.47</b>',f'<b>MORI {rev}</b>')
text=re.sub(r'<h1>.*?</h1>','<h1>相机间隙与CAM螺钉已修正。</h1>',text,count=1,flags=re.S)
text=re.sub(r'<section id="camera-cam">.*?</section>','',text,flags=re.S)
text=text.replace('<section id="p5r7">',section+'<section id="p5r7">',1)
text=text.replace('<a href="#camera-cam">本轮相机/CAM</a>','')
text=text.replace('<a href="#p5r7">P5R7板卡</a>','<a href="#camera-cam">本轮相机/CAM</a><a href="#p5r7">P5R7板卡</a>',1)
# Only ordinary render assets are rerendered; retain historical study image tags.
text=re.sub(r'(renders/(?!p5r7/)[^"?]+\.png)\?revision=V1\.2-M1\.47',r'\1?revision='+rev,text)
checks=f'<section id="checks"><h2>检查与文件</h2><p>当前主检查{v["counts"]["PASS"]} PASS / 0 FAIL；{v["counts"]["BLOCKED"]} BLOCKED、{v["counts"]["NOT_TESTED"]} NOT_TESTED保留。21/21候选STL拓扑及实际回读通过。两次重建、当前预览、电子细模与视频来源检查通过。</p><p class="notice">完整线束、反力连接初装、部分供应商接口和质量预算仍未关闭。<a href="studies/prearrival_finish/index.html">查看剩余项目</a>。数字检查不代表实物配合或打印强度通过。</p></section>'
text,n=re.subn(r'<section id="checks">.*?</section>',checks,text,flags=re.S);assert n==1
remaining='<section id="remaining"><h2>当前剩余项目</h2><table>'+''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}</td></tr>' for r in work['remaining'])+'</table><p><a href="studies/prearrival_finish/work_status.json">完整状态记录</a></p></section>'
text,n=re.subn(r'<section id="remaining">.*?</section>',remaining,text,flags=re.S);assert n==1
index.write_text(text)
rows=''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}</td></tr>' for r in work['remaining'])
body=f'''<p class="notice done">已按两项确认应用到主模型，修正范围仅Display_Frame及四枚CAM螺钉。Blender、STL、预览、电子细模和装配视频同步到{rev}。</p><p>相机、孔轴、插座、嵌件与其余204件几何和位置保持。相机座名义顶壁1.2mm；当前相机尺寸仍含照片估算。</p><div class="grid"><figure><img src="camera_top.png"><figcaption>连续平直上沿，移除0.6mm外侧材料。</figcaption></figure><figure><img src="cam_screws.png"><figcaption>正式M2×5内六角与绿色短边工具包络。</figcaption></figure></div><h2>CAM安装方法</h2><p>用1.5mm短边L扳手锁紧；参考Wera950PKLS05022040001，长边90mm、短边4.5mm。显示架和头壳后装。三枚螺钉可从上方送入；右下方CAM_Mount_Screw_2从前方沿轴线送入。工具包络有连续60°转动及8mm轴向空间，实际拧紧扭矩和工具弯角仍待到货验证。</p><h2>本轮检查</h2><p>五件与已确认候选的实体比对、其余204件逐件网格/位姿比对、相机三条具名装配路径、四枚螺钉与工具路径、130个头部姿态检查通过。零件数量保持；581份硬件原生源/合同哈希保持。</p><p><a href="../../../reports/camera_cam_completion_validation.json">几何记录</a> · <a href="../../../reports/export_manifest.json">STL清单</a> · <a href="commands.json">执行命令</a> · <a href="../../../animation/index.html?revision={rev}-A1">更新后的装配视频</a></p><h2>仍未关闭</h2><table>{rows}</table><p class="notice">完整线束和供应商加工图尚未完成，未将任何走线候选应用到主模型。本轮是名义几何检查，实物配合、PA12强度和装配工艺未验证。</p>'''
(OUT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.48 · 相机与CAM</title>{style}<main><nav><a href="../../../index.html?revision={rev}#camera-cam">当前总装</a><a href="../index.html">到货前工作</a></nav><h1>相机与CAM固定修正已应用</h1><p>{rev} · {stamp}</p>{body}</main></html>')
# Keep research pages and their hashes unchanged; point the current overview at adoption.
overview=S/'index.html';t=overview.read_text()
banner=f'<div class="notice done" id="M1-48-adopted"><b>{rev}：相机上沿和CAM内六角螺钉已应用。</b> <a href="camera_cam_adoption/index.html">查看当前交付</a>。下方旧研究按其记录版本阅读；相机间隙及CAM螺钉不再待确认。完整线束仍未完成。</div>'
t=re.sub(r'<div class="notice done" id="M1-48-adopted">.*?</div>','',t,flags=re.S)
t=t.replace('<main>','<main>'+banner,1);overview.write_text(t)
previews=read(M/'reports/parts_preview_manifest.json');bom=read(M/'reports/bom.json')
manufacturing=parts_view(M,rev,bom,previews,ex)
(M/'manufacturing.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html#camera-cam">当前模型</a><h1>{rev}打印件与五金</h1><p class="notice">16件本体PA12打印件。CAM四枚DIN912 M2×5为采购五金，不是打印件。此页为分类及候选文件，未制造放行。</p>{manufacturing}</main></html>')
(M/'parts.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html">当前总装</a><h1>{rev}部件预览</h1><div class="grid">'+''.join(f'<figure><img loading="lazy" src="{r["file"]}?revision={rev}"><figcaption>{html.escape(r["id"]+" · "+r["name"])}</figcaption></figure>' for r in previews)+'</div></main></html>')
(M/'README.md').write_text(f'''# MORI {rev}

已应用相机支架连续上沿降低0.6mm、四枚CAM螺钉改为DIN912 M2×5。仅五个对象变化；其余204件机器人实体的几何与位置保持。名义上壁1.2mm、前壳间隙{gap:.3f}mm。16件本体打印件数量不变。

[本轮模型与装配说明](studies/prearrival_finish/camera_cam_adoption/index.html) · [当前Blender](mori_v1_2.blend) · [电子细模](mori_electronics_detail.blend) · [装配视频](animation/index.html) · [剩余任务](studies/prearrival_finish/work_status.json) · [轮胎筛选](studies/prearrival_finish/tyre_selection/index.html)

主检查{v['counts']['PASS']} PASS / 0 FAIL；{v['counts']['BLOCKED']} BLOCKED、{v['counts']['NOT_TESTED']} NOT_TESTED保留。21件STL与{am['animation_revision']}已同步。反力夹初装、完整线束、供应商接口和质量预算尚未完成。PROTOTYPE / UNVALIDATED；几何检查不代表实物配合或打印强度。
''')
(OUT/'README.md').write_text(f'''# {rev} 两项确认的应用

- 相机座连续上沿降低0.6mm，名义上壁1.2mm，与前壳间隙{gap:.6f}mm。
- 四枚CAM固定件：DIN912/ISO4762 M2×5，头Ø3.8×2mm，1.5mm短边L扳手。
- 孔轴、内侧夹持、镜头、PCB、嵌件不动；共五件匹配批准候选，204件保持。
- 未采用走线开孔、扎带座或电路候选。完整线束仍BLOCKED。

主模型、STL、预览、电子细模、{am['animation_revision']}同步。实物工具/配合/打印强度NOT_TESTED。

检查：[当前实体](../../../reports/camera_cam_completion_validation.json)；[命令](commands.json)；[确认原文与硬件源哈希](approval.json)。
''')
changelog=M/'animation'/('CHANGELOG_'+am['animation_revision'].removeprefix('V1.2-').replace('-','_')+'.md')
changelog.write_text(f'''# {am['animation_revision']}

来源为已保存的{rev}主模型，SHA256 `{source}`。

- 相机支架上沿整条降低0.6mm，名义顶壁1.2mm；相机、孔位和前壳保持。
- 四枚CAM固定螺钉替换为DIN912 M2×5内六角，头部Ø3.8×2mm。
- 第17章安装字幕改为1.5mm短边L扳手锁紧，显示架和头壳后装。
- 视频{am['duration_seconds']}秒、{am['frame_range'][1]}帧、24fps、1280×720，22章；渲染和视频回读通过。

各动画实体与当前主模型的顶点及面连接一致；分解位移仅供装配演示。保留反力夹预装、完整线束及供应商接口尚未完成的提示，未宣称完整装配工艺或实物配合通过。
''')
subprocess.run([sys.executable,str(M/'scripts/publish_animation_update.py')],cwd=P,check=True)
write(OUT/'publication.json',{'status':'PASS','revision':rev,'utc':stamp,'source_blend_sha256':source,'animation_revision':am['animation_revision'],'scope':'Approved two edits and current deliverables only','manufacturing_release':False})
print('M1_48_PUBLISHED',source,v['counts'])
