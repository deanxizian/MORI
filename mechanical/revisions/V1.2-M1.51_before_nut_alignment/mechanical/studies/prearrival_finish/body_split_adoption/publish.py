"""Publish the adopted body split after current files and media pass read-back."""
from pathlib import Path
import json,hashlib,datetime,html,re,sys,subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];M=ROOT/'mechanical';S=OUT.parent
sys.path.insert(0,str(M/'scripts'))
from parts_classification import generate as parts_view
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
p=read(ROOT/'config/geometry.json');rev=p['revision'];assert rev=='V1.2-M1.51'
source=sha(M/'mori_v1_2.blend');stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
c=read(OUT/'check.json');v=read(M/'reports/validation.json');ex=read(M/'reports/export_manifest.json')
r=read(OUT/'render_manifest.json');am=read(M/'animation/manifest.json');av=read(M/'animation/validation.json')
e=read(S/'engineering_current.json');electronics=read(M/'reports/electronics_detail_manifest.json')
coupons=read(OUT/'fit_coupons/manifest.json')
assert coupons['status']=='PASS' and coupons['source_blend_sha256']==source
assert read(OUT/'fit_coupons/readback.json')['status']=='PASS'
assert all(x['status']=='PASS' for x in [c,r,av,e,read(M/'reports/delivery_consistency.json')])
assert all(x['source_blend_sha256']==source for x in [c,r,am,e])
assert electronics['source_main_sha256']==source
assert v['counts']['FAIL']==0 and ex['exported_count']==21
assert all(x['status']=='PASS' for x in ex['parts'])
assert am['animation_revision']==rev+'-A1' and am['rendered_video']
assert c['scope']['unchanged']==199 and not c['scope']['changed']
prep=read(OUT/'preparation.json');prior=read(ROOT/prep['snapshot_root']/'mechanical/reports/export_manifest.json')
a={x['id']:x['sha256'] for x in prior['parts']};b={x['id']:x['sha256'] for x in ex['parts']}
assert set(a)-set(b)=={'Body_Upper','Body_Lower'} and set(b)-set(a)=={'Body_Front','Body_Rear'}
assert all(a[n]==b[n] for n in set(a)&set(b)) and len(set(a)&set(b))==19
assert all(sha(ROOT/n)==h for n,h in prep['protected_hardware'].items())
work=read(S/'work_status.json');work.update(revision=rev,source_blend_sha256=source,updated_utc=stamp,status='BLOCKED',manufacturing_release=False)
done={x['id']:x for x in work['completed']}
done['body_split_M1_51']=dict(id='body_split_M1_51',status='PASS',detail='前后两片身体外壳已采用；底部两组一体定位插舌，四处工具孔，保留原四枚框架螺钉；取消四枚旧拼缝螺钉和四个嵌件。名义模块装入和工具路径通过。',evidence='body_split_adoption/index.html')
done['geometry_delivery']=dict(id='geometry_delivery',status='PASS',detail=f'{rev}主模型、STL、当前预览与电子细模同步。16件本体打印件；仅两片身体外壳改变，另19件STL逐文件不变。新增检查与历史沿用证据已区分。',evidence='body_split_adoption/index.html')
done['animation']=dict(id='animation',status='PASS',detail=f'{am["animation_revision"]}：{am["duration_seconds"]}秒、22步骤；先装内部结构，再前后合壳、底部锁紧，模型与视频回读通过。完整软线束与反力夹初装仍未完成。')
done['engineering']=dict(id='engineering',status='PASS',detail=f'{rev}名义质量与390姿态计算同步，不是实物称重或载荷验证。')
work['completed']=list(done.values())
for row in work['remaining']:
 if row['id']=='harness':
  row['detail']='C5＋K1及前后分壳已采用；C6、滑动导线约束和回弯固定候选尚未采用。新外壳的带附件刚体合装和底部工具路径通过；完整恒定材料长度线束、所有端部、应力释放、FFC/FPC、带线闭壳及供应商裁线图仍未完成。'
  row['latest_body_split_adoption']='body_split_adoption/index.html';row['body_split_approved']=True
 elif row['id']=='reaction_assembly':
  row['detail']='前后分壳已用于当前主模型，内部结构可在身体外壳未装时固定。反力夹本身的初次装配、最终舵盘接口以及与完整线束共存的工序仍需完成；本轮没有改变反力夹。'
 elif row['id']=='load_budget':
  row['detail']=f'{rev}当前已建模名义质量{e["totals"]["whole"]["mass_g"]/1000:.3f}kg，仍不是实物称重；未选电源附件、完整线束和热隔离固定仍缺。'
work['body_split_adoption']=dict(status='PASS',revision=rev,source_blend_sha256=source,evidence='body_split_adoption/index.html',full_wired_assembly='BLOCKED',physical_fit='NOT_TESTED')
write(S/'work_status.json',work)
style='<style>*{box-sizing:border-box}body{margin:0;background:#edf2f0;color:#263c36;font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1160px;margin:auto;padding:26px 24px 64px}a{color:#146e63}nav{display:flex;gap:22px;flex-wrap:wrap}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;border:1px solid #cbd7d1;border-radius:10px;overflow:hidden;background:white}img{width:100%;display:block}figcaption{padding:12px}.notice{padding:18px;background:#fff0d6;border-radius:8px}.done{background:#dceee3}td,th{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #c7d4cd}table{width:100%;border-collapse:collapse}code{word-break:break-all}h1{font-size:32px}@media(max-width:700px){.grid{grid-template-columns:1fr}main{padding:18px}}</style>'
def page(title,body):return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title>'+style+'<main>'+body+'</main></html>'
description='身体改为前后两片壳，打印件数量保持。底部增加两组一体插舌负责定位，保留四枚原框架螺钉负责锁紧；螺钉和工具经四个底部孔进入。原来的四枚拼缝螺钉和四个嵌件取消。'
figures=''.join(f'<figure><img src="{n}.png?revision={rev}"><figcaption>{label}</figcaption></figure>' for n,label in [('current_bottom_locators_open','底部局部剖切与展开：两组插舌和接收座，均与壳体一体打印。'),('current_bottom_locators_closed_section','底部局部剖切与闭合：插舌负责对齐；0.3mm单边试配间隙待PA12样件验证。')])
remaining=''.join(f'<tr><td>{html.escape(x["item"])}</td><td>{html.escape(x["detail"])}</td></tr>' for x in work['remaining'])
body=f'''<nav><a href="../../../index.html?revision={rev}#body-split">当前总装</a><a href="../../../animation/index.html?revision={am['animation_revision']}">新版装配视频</a><a href="../../../manufacturing.html">打印件与五金</a></nav><h1>前后分壳已应用</h1><p>{rev} · {stamp}</p><p class="notice done">主模型、21件STL、电子细模、预览和{am['animation_revision']}视频已同步。机器人本体仍为16件打印件。</p><p>{description}</p><div class="grid">{figures}</div><figure><img src="../../../renders/45_assembled.png?revision={rev}"><figcaption>当前总装。外形母面、头部、屏幕、轮轴和电子件位置保持。</figcaption></figure><h2>装配方式</h2><ol><li>身体壳未装时，完成轮驱、内部框架、承重桥与头部结构的装配。</li><li>前壳预装喇叭，后壳预装接口板；原安装座和孔轴保留。</li><li>前壳从正前方平移合入，后壳从后方合入，底部插舌对齐。</li><li>四枚原框架螺钉从底部工具孔进入并锁紧。图示工序仍需结合最终断电方式、线束和实物公差验证。</li></ol><h2>本轮实际检查</h2><table><tr><th>范围</th><th>证据与界限</th></tr><tr><td>改动范围</td><td>2片新外壳替换旧上下壳，移除8件旧拼缝五金；另外199件机器人实体的坐标和面连接保持。19件其余STL逐文件不变。</td></tr><tr><td>带附件合装</td><td>每片模块275个平移位置，保留车轮且另一片壳闭合；含喇叭、后接口板及已建插头包络，未检出刚体碰撞。</td></tr><tr><td>螺钉与工具</td><td>四处底部通道采用实际螺钉与名义Ø5×125mm刀杆／Ø20×60mm手柄，检查150mm连续轴向进入包络；实物工具、人手和螺纹配合未验证。</td></tr><tr><td>整机</td><td>当前实体静态检查、130个头部姿态、车轮转动、外壳采样壁厚、嵌件孔壁和拓扑已重跑。原厂模型及插接资料问题仍保留BLOCKED。</td></tr><tr><td>动画</td><td>{am['duration_seconds']}秒／{am['frame_range'][1]}帧／22步骤。当前前后壳与承重桥关键帧半帧回读通过；连续柔性线束与全部人工工艺未通过。</td></tr></table><p><a href="check.json">保存模型与路径检查</a> · <a href="../../../reports/validation.json">当前检查及历史证据边界</a> · <a href="../../../animation/front_rear_path_validation.json">动画路径回读</a> · <a href="commands.json">命令日志</a> · <a href="contract_receipt.json">机械服务要求更新记录</a></p><p class="notice">完整线束、反力夹初装和供应商接口仍未完成。插舌间隙、PA12强度与紧固需试件验证；本轮未制造放行。</p><h2>后续事项</h2><table>{remaining}</table><small>来源主模型 SHA256：<code>{source}</code></small>'''
body=body.replace('<h2>后续事项</h2>','<h2>PA12试配小样</h2><p>已从当前接口截取一对小样，包含插舌和接收座；可先检验0.3mm单边间隙，再评估整壳配合。<a href="fit_coupons/index.html">小样预览、STL与测量记录</a>。局部试配不能替代整壳强度与变形验证。</p><h2>后续事项</h2>')
(OUT/'index.html').write_text(page('MORI M1.51 · 前后分壳',body))
index=M/'index.html';s=index.read_text();s=re.sub(r'<title>MORI V1\.2-M1\.\d+</title>',f'<title>MORI {rev}</title>',s,count=1);s=re.sub(r'<b>MORI V1\.2-M1\.\d+</b>',f'<b>MORI {rev}</b>',s,count=1);s=re.sub(r'<h1>.*?</h1>','<h1>身体前后分壳已应用。</h1>',s,count=1,flags=re.S)
s=s.replace('<a href="#cam-entry">本轮CAM入口</a>','<a href="#body-split">本轮前后分壳</a><a href="#cam-entry">已采用CAM入口</a>');s=s.replace('<h2>本轮：CAM排线入口</h2>','<h2>已采用：M1.50 CAM排线入口</h2>')
main_figures=figures.replace('src="','src="studies/prearrival_finish/body_split_adoption/')
section=f'<section id="body-split"><h2>本轮：前后分壳</h2><p>{description}</p><div class="grid">{main_figures}</div><p><a href="studies/prearrival_finish/body_split_adoption/index.html">当前模型、装配方式与完整检查</a></p></section>'
s=re.sub(r'<section id="body-split">.*?</section>','',s,flags=re.S);s=s.replace('<section id="cam-entry">',section+'<section id="cam-entry">',1)
s=re.sub(r'(renders/(?!p5r7/)[^"?]+\.png)\?revision=V1\.2-M1\.\d+',r'\1?revision='+rev,s)
s,n=re.subn(r'<section id="remaining">.*?</section>',f'<section id="remaining"><h2>当前剩余项目</h2><table>{remaining}</table><p><a href="studies/prearrival_finish/work_status.json">完整状态</a></p></section>',s,flags=re.S);assert n==1
s,n=re.subn(r'<section id="checks">.*?</section>',f'<section id="checks"><h2>检查与文件</h2><p>本轮重跑{len(v["current_rerun_ids"])}项，未出现几何FAIL；不受改动影响的历史证据保留原版本。21件STL导出通过，其中2片身体外壳更新、19件逐文件保持。</p><p>主模型、当前预览、电子细模与新版装配动画同步。完整线束、反力夹初装和供应商资料仍有未完成项。</p></section>',s,flags=re.S);assert n==1;index.write_text(s)
previews=read(M/'reports/parts_preview_manifest.json');bom=read(M/'reports/bom.json');manufacturing=parts_view(M,rev,bom,previews,ex)
(M/'manufacturing.html').write_text(page(rev+'打印件与五金',f'<a href="index.html#body-split">当前总装</a><h1>{rev}打印件与五金</h1><p class="notice">本体16件PA12打印件。两片身体外壳更新；旧拼缝的4枚螺钉与4个嵌件取消。未制造放行。</p>{manufacturing}'))
t=(M/'manufacturing.html').read_text();t=t.replace('</main>','<h2>新增局部试配小样</h2><p><a href="studies/prearrival_finish/body_split_adoption/fit_coupons/index.html">身体底部插舌与接收座试配件</a>，与整机21件STL分开保存，不计入机器人零件数。</p></main>');(M/'manufacturing.html').write_text(t)
(M/'parts.html').write_text(page(rev+'部件预览',f'<a href="index.html">当前总装</a><h1>{rev}部件预览</h1><div class="grid">'+''.join(f'<figure><img loading="lazy" src="{x["file"]}?revision={rev}"><figcaption>{html.escape(x["id"]+" · "+x["name"])}</figcaption></figure>' for x in previews)+'</div>'))
readme=f'''# MORI {rev}

前后两片身体外壳已替换旧上下壳；两组一体底部插舌定位，原四枚框架螺钉通过四个底部工具孔锁紧。取消四枚旧拼缝螺钉与四个嵌件，不增加打印件。

主模型、21件STL、电子细模、预览和{am['animation_revision']}装配动画同步。两片外壳改变，另外199个机器人实体和19件STL保持；581个硬件文件未改。

每片带附件模块275位置、底部螺钉/工具进入、整机静态/头部130姿态/车轮/孔壁和STL检查已完成。验证文件区分本轮重跑和M1.50沿用证据，不将旧上下壳工序当作当前检查。

完整软线束、反力夹初装、供应商接口和质量预算仍未关闭。PA12试配/强度与实物配合未验证。PROTOTYPE / UNVALIDATED；无制造放行。
'''
(M/'README.md').write_text(readme+'\n[本轮详情](studies/prearrival_finish/body_split_adoption/index.html) · [装配动画](animation/index.html) · [工作状态](studies/prearrival_finish/work_status.json)\n')
(OUT/'README.md').write_text(readme+'\n[保存模型检查](check.json) · [快照](preparation.json) · [执行命令](commands.json)\n')
eng=S/'ENGINEERING.md';old_engineering=eng.read_text()
old_engineering=re.sub(r'^# V1\.2-M1\.\d+ 当前质量与载荷计算',f'# {rev} 当前质量与载荷计算',old_engineering)
old_engineering=re.sub(r'模型SHA256 `[^`]+`；\d+个实体、\d+姿态',f'模型SHA256 `{source}`；{e["coverage"]["count"]}个实体、{len(e["head_poses"])}姿态',old_engineering)
old_engineering=re.sub(r'(整机已建模质量 \| )[^|]+',lambda _:f'整机已建模质量 | {e["totals"]["whole"]["mass_g"]/1000:.3f} kg ',old_engineering)
old_engineering=re.sub(r'(本体打印件 \| )[^|]+',lambda _:f'本体打印件 | {e["totals"]["prints"]["mass_g"]:.1f} g ',old_engineering)
old_engineering=re.sub(r'(零位重心高度 \| )[^|]+',lambda _:f'零位重心高度 | {e["totals"]["whole"]["COM_mm"][2]:.2f} mm ',old_engineering)
old_engineering=re.sub(r'超出的[0-9.]+g',f'超出的{e["totals"]["whole"]["mass_g"]-1200:.1f}g',old_engineering)
eng.write_text(old_engineering)
assembly=f'''# MORI {rev} · 组装与候选打印文件

当前主模型 SHA256：`{source}`。当前板卡来源仍为运动及后接口 P5R7、电源 P5R6、IMU P5R4；硬件文件未改。

身体现为前后分壳。先固定内部框架与承重桥，再从前后合壳；原来的上下壳联动工序已废止。机器人本体保持16件PA12打印件，取消4枚旧拼缝螺钉和4个嵌件。详见[当前分壳结构](../studies/prearrival_finish/body_split_adoption/index.html)。

## 当前装配示意

1. 在身体壳未装时，装轮驱、内部框架、板卡和承重桥。承重桥横向螺钉在装车轮前操作。
2. 头部座与防脱压板采用已批准方案；相关名义装入与工具检查保留。反力夹本身的初装及最终舵盘接口仍未完成，不能把预装总成演示当成完整工艺。
3. 前壳预装喇叭，后壳预装接口板。原附件孔位保持。
4. 前壳沿-Y、后壳沿+Y平移合入，底部两组一体插舌对齐。原4枚框架螺钉从底部工具孔送入并锁紧。
5. 当前几何允许车轮保留时拆装身体壳；视频先合壳后装车轮，便于观察内部工序。带线合壳仍需完成。

[装配动画 {am['animation_revision']}](../animation/index.html)：{am['duration_seconds']}秒，22步骤。附件台面镜头将前后壳转向内侧展示，下一镜恢复真实装配方向；这一镜头切换不是机器人内部的转动路径。

## 打印文件与验证边界

[21件候选STL记录](export_manifest.json)全部通过拓扑及1:1重导入；其中两片身体壳更新，另外19件文件不变。[底部插舌小样](../studies/prearrival_finish/body_split_adoption/fit_coupons/index.html)另存两件，按同批次PA12验证0.3mm单边间隙，不计入机器人零件数。

两半壳带附件各275个位置、四处螺钉/工具路径、当前头部130姿态及相关实体检查通过。完整柔性线束、反力夹初装、SCS0009舵盘/锁紧、WeAct插接资料、未选采购件和质量目标仍未关闭。完整状态见[工作状态](../studies/prearrival_finish/work_status.json)。

局部试配不能替代整壳变形、紧固预紧、承载或疲劳试验。模型仍为PROTOTYPE / UNVALIDATED；当前无制造放行。
'''
(M/'reports/组装与打印.md').write_text(assembly)
overview=S/'index.html';t=overview.read_text();t=re.sub(r'<div class="notice done" id="M1-51-adopted">.*?</div>','',t,flags=re.S);t=t.replace('<main>',f'<main><div class="notice done" id="M1-51-adopted"><b>{rev}：前后分壳已采用。</b> <a href="body_split_adoption/index.html">当前模型、装配和检查</a>。下方早期研究按各自版本阅读，不能用于当前上下壳工序；完整线束仍未完成。</div>',1);overview.write_text(t)
changelog=M/'animation'/('CHANGELOG_'+am['animation_revision'].removeprefix('V1.2-').replace('-','_')+'.md');changelog.write_text(f'# {am["animation_revision"]}\n\n来源主模型 SHA256 `{source}`。\n\n身体改为前后平移合壳，取消旧上下壳联动和拼缝五金工序。内部桥先固定；原四枚框架螺钉经底部工具孔锁紧。{am["duration_seconds"]}秒、22步骤，保存矩阵与视频回读通过。\n\n完整软线束和反力夹初装仍未完成；动画不是实际制造与装配放行。\n')
subprocess.run([sys.executable,str(M/'scripts/publish_animation_update.py')],cwd=ROOT,check=True)
write(OUT/'publication.json',dict(status='PASS',revision=rev,utc=stamp,source_blend_sha256=source,animation_revision=am['animation_revision'],changed_prints=['Body_Front','Body_Rear'],unchanged_STL=19,full_harness='BLOCKED',manufacturing_release=False,historical_snapshot=prep['snapshot_root']))
print('BODY_SPLIT_M1_51_PUBLISHED',flush=True)
