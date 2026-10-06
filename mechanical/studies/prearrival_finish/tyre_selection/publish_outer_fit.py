"""Publish a bounded catalogue-wheel fit study without touching robot geometry."""
from pathlib import Path
import json, hashlib, datetime, re, html
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
PARENT=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
d=read(HERE/'outer_fit.json')
assert d['status']=='PASS' and not d['candidate_adopted']
assert sha(PROJECT/'mechanical/mori_v1_2.blend')==d['source_blend_sha256']
assert sha(PROJECT/'config/geometry.json')==d['config_sha256']
assert len(d['excluded_mating_or_replaced_parts'])==14
assert len(d['ground_screen_excluded_parts'])==4
cases=d['cases']; labels=['现有设计','候选：轮宽中心不动','候选：每侧向外移 1.16 mm']
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':12})
fig=plt.figure(figsize=(14,8.4),facecolor='#f6f8f7')
gs=fig.add_gridspec(3,2,left=.065,right=.97,bottom=.17,top=.79,wspace=.2,hspace=.65,width_ratios=[1.55,1])
for i,(c,label) in enumerate(zip(cases,labels)):
    ax=fig.add_subplot(gs[i,0]); ax.set_facecolor('#f6f8f7')
    ax.set_xlim(51,83);ax.set_ylim(0,1.1);ax.axis('off')
    ax.set_title(label,loc='left',fontsize=14,pad=4)
    inner=c['inner_face_abs_x_mm'];outer=c['tyre_outer_span_mm']/2
    ax.add_patch(Rectangle((52,.08),3,.36,color='#adbdb8'))
    ax.add_patch(Rectangle((inner,.08),c['width_mm'],.36,color='#364c4c' if i==0 else '#bc8742'))
    ax.text(53.5,.25,'壳',ha='center',va='center',color='#253b3c')
    ax.text((inner+outer)/2,.25,f"轮宽 {c['width_mm']:.2f} mm",ha='center',va='center',color='white',fontsize=12)
    ax.annotate('',(inner,.64),(55,.64),arrowprops={'arrowstyle':'<->','color':'#395852','lw':1.5})
    ax.text((55+inner)/2,.77,f"{c['shell_minimum']['gap_mm']:.2f} mm",ha='center',fontsize=12)
    ax.plot([55,55],[.45,.7],color='#718d84',lw=1)
    ax.plot([inner,inner],[.45,.7],color='#718d84',lw=1)
    ax.text(outer+.3,.25,f"Ø{c['diameter_mm']:g}",va='center',fontsize=11)
    bx=fig.add_subplot(gs[i,1]);bx.set_facecolor('#f6f8f7');bx.set_xlim(0,24);bx.set_ylim(-.6,.6)
    bx.barh([0],[c['belly_clearance_mm']],height=.5,color='#517b68' if i==0 else '#bc8742')
    bx.axvline(20,color='#426751',ls='--',lw=1.2)
    bx.text(c['belly_clearance_mm']+.3,0,f"{c['belly_clearance_mm']:.1f} mm",va='center',fontsize=13)
    bx.set_yticks([]);bx.set_xticks([0,10,20]);bx.tick_params(length=0,labelsize=10)
    for s in bx.spines.values():s.set_visible(False)
    if i==0:bx.set_title('名义腹部离地间隙',loc='left',fontsize=14,pad=4)
fig.text(.065,.93,'较小、较宽的软轮：直接替换会损失间隙',fontsize=23,color='#213e36',weight='bold')
fig.text(.065,.865,'左图：右轮横向占用示意  ·  右图：以未受压轮胎接地  ·  M1.47 主模型保持 105 × 18 mm',fontsize=12,color='#526962')
fig.text(.065,.095,'向外移只能恢复轮壳间隙；腹部离地仍少 1.7 mm，整机轮外跨度由 154 增至 158.64 mm。',fontsize=13,color='#213e36')
fig.text(.065,.055,'这是外包络研究，未设计 T81 轮毂、轴端固定或轮胎受压变形；不能据此直接下单或替换。',fontsize=12,color='#64746e')
fig.savefig(HERE/'outer_fit.png',dpi=150,facecolor=fig.get_facecolor())
fig.savefig(HERE/'outer_fit.svg',facecolor=fig.get_facecolor());plt.close(fig)

notes=['保留当前设计','轮壳间隙与20 mm离地目标均不满足','恢复轮壳间隙；离地与轴端接口仍待处理']
rows=''.join(f'<tr><td>{label}</td><td>{c["diameter_mm"]:g} × {c["width_mm"]:g}</td><td>{c["shell_minimum"]["gap_mm"]:.2f}</td><td>{c["belly_clearance_mm"]:.1f}</td><td>{c["tyre_outer_span_mm"]:.2f}</td><td>{note}</td></tr>' for label,c,note in zip(labels,cases,notes))
style='body{margin:0;background:#f2f5f3;color:#253d34;font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1120px;margin:auto;padding:30px 24px 60px}h1{font-size:30px}h2{margin-top:28px}a{color:#166957}aside{background:#fff0d6;border-left:4px solid #b38542;padding:16px 20px}table{border-collapse:collapse;width:100%}th,td{text-align:left;vertical-align:top;padding:11px;border-bottom:1px solid #ced8d2}img{width:100%;border:1px solid #d1dbd5}code{word-break:break-all}.table{overflow-x:auto}'
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 软轮候选外形适配</title><style>'''+style+'''</style><main>
<p><a href="index.html">返回产品筛选</a> · <a href="../index.html">打样前工作</a></p>
<h1>最近尺寸候选还不能直接替换</h1>
<aside>101.6 × 20.32 mm 候选会使轮壳最小间隙变为约2.84 mm，名义腹部离地变为18.3 mm。每侧向外移1.16 mm可恢复约4 mm轮壳间隙，但不会恢复20 mm离地目标。主模型、轮轴、轮毂与装配视频均未因本研究改变。</aside>
<p>研究对象为 <a href="https://banebots.com/banebots-compliant-wheel-4-x-0-8-hub-mount-60a-black/">BaneBots T81P-406BB 官方尺寸</a>：4 × 0.8 in，换算101.6 × 20.32 mm。它是成品轮；T81圆＋方中心和卡簧接口不同于当前双D轮毂。下列数据是原主模型与目录外包络的计算，不是实测。</p>
<img src="outer_fit.png" alt="三种位置的轮壳间隙与离地间隙对比">
<div class="table"><table><tr><th>方案</th><th>轮径×轮宽/mm</th><th>轮壳最小间隙/mm</th><th>腹部离地/mm</th><th>双轮外侧跨度/mm</th><th>结论</th></tr>'''+rows+'''</table></div>
<h2>已检查的范围</h2>
<p>对当前209件装配中的身体外壳和下部结构，以512边外包圆柱检查候选轮胎的整体旋转占用；最大径向多包约0.001 mm。六类邻近结构的实体未与该外包络相交。原轮胎、轮毂、轮轴、隔圈及轴端锁紧共14件从接口适配判断中剔除，明确保留为待设计项；共用电机底盖的螺钉和螺母仍参与检查。</p>
<p>130个组合头部姿态的包围盒与轮胎保持分离。前后倾斜−15°至+15°的31个离散位置中，候选最低离地约16.98 mm，现有约18.68 mm，最低处均为下壳。该检查只表示给定几何未触地，不是平衡、稳定性或断电站立验证。</p>
<h2>采用前仍要处理</h2>
<ul><li>取得匹配T81轮毂的完整尺寸、公差、轴端锁紧及装配资料，才能形成可安装的方案。</li><li>若采用该轮径，需处理减少的1.7 mm离地间隙，再检查轴承、电机、底盖和电池相关接口；本研究未移动这些部件。</li><li>轮胎受压半径、跳动、工作范围及重量范围仍未确认。厂家成品轮约90.7 g与现有“仅胎圈”估重不可直接相减。</li><li>国内可交付渠道和含运价仍未确认；轮径及轮毂结构变化须先提交用户审阅。</li></ul>
<p><a href="outer_fit.json">逐项计算结果</a> · <a href="check_outer_fit.py">可重复运行脚本</a> · <a href="outer_fit.log">实际运行记录</a> · <a href="outer_fit.svg">矢量图</a></p>
<p>PROTOTYPE / UNVALIDATED。外形筛查完成，完整替换方案 BLOCKED。<br><small>主模型SHA256：<code>'''+d['source_blend_sha256']+'''</code></small></p></main></html>'''
(HERE/'outer_fit.html').write_text(page)
for p in [HERE/'index.html',PARENT/'index.html']:
    text=p.read_text();text=re.sub(r'<section id="tyre-outer-fit">.*?</section>','',text,flags=re.S)
    prefix='' if p.parent==HERE else 'tyre_selection/'
    section=f'<section id="tyre-outer-fit"><h2>软轮候选空间复核</h2><p><a href="{prefix}outer_fit.html">查看三种尺寸与位置的对比</a>：最近尺寸候选直接替换会将轮壳间隙降至2.84 mm、腹部离地降至18.3 mm；仍缺轮毂与轴端接口，主模型保持。</p></section>'
    text=text.replace('</main>',section+'</main>');p.write_text(text)
s=read(PARENT/'work_status.json')
entry=dict(id='tyre_outer_fit',status='PASS',detail='最近尺寸软轮候选的外包络、130头部姿态及31身体倾角检查完成。直接替换不满足既有轮壳/离地目标，外移仅恢复轮壳间隙。轮毂和轴端接口未设计，未应用主模型。')
s['completed']=[r for r in s['completed'] if r['id']!=entry['id']]+[entry]
s['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
s['tyre_outer_fit']=dict(study_status='PASS',replacement_status='BLOCKED',applied=False,review='tyre_selection/outer_fit.html',
    source_sha256=d['source_blend_sha256'],minimum_shell_gap_mm=cases[1]['shell_minimum']['gap_mm'],nominal_belly_clearance_mm=cases[1]['belly_clearance_mm'])
write(PARENT/'work_status.json',s)
# These existing delivery records own only the listed current documentation.
for filename in ['M1_47_delivery.json','harness_A2/delivery.json']:
    p=PARENT/filename;manifest=read(p)
    for changed in [PARENT/'work_status.json',PARENT/'index.html',HERE/'index.html']:
        key=str(changed.relative_to(PROJECT))
        if key in manifest['files']:manifest['files'][key]=sha(changed)
    write(p,manifest)
files=[p for p in HERE.iterdir() if p.is_file() and p.name not in ['delivery.json']]
files += list((HERE/'sources').glob('*'))
write(HERE/'delivery.json',dict(status='PASS',scope='Wheel screening sources and outer-size study only',source_blend_sha256=d['source_blend_sha256'],
    main_geometry_changed=False,candidate_adopted=False,manufacturing_release=False,
    commands=['/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/tyre_selection/check_outer_fit.py','/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/tyre_selection/publish_outer_fit.py'],
    files={str(p.relative_to(PROJECT)):sha(p) for p in files if p.is_file()}))
print('TYRE_OUTER_FIT_PUBLISHED')
