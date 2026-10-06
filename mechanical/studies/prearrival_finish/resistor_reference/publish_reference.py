"""Document the deliberately limited AC05 model; no thermal or installed claim."""
from pathlib import Path
import json,hashlib,datetime,re,urllib.request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
d=read(HERE/'reference.json')
assert sha(ROOT/d['output_blend'])==d['output_blend_sha256']
assert sha(ROOT/'mechanical/mori_v1_2.blend')==d['main_sha256']
font=FontProperties(fname='/System/Library/Fonts/STHeiti Light.ttc')
font_manager.fontManager.addfont(font.get_file())
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(10.5,5.8),dpi=160,facecolor='#f7f8f7')
ax.set_facecolor('#f7f8f7')
ax.add_patch(Rectangle((-9,-3.75),18,7.5,facecolor='#d8a768',edgecolor='#6c4d26',lw=1.5))
for x in [-12,9]:ax.add_patch(Rectangle((x,-3.75),3,7.5,facecolor='none',edgecolor='#af762d',ls='--',lw=1.4))
ax.annotate('',xy=(-9,-5.5),xytext=(9,-5.5),arrowprops=dict(arrowstyle='<->',color='#304955'))
ax.text(0,-6.5,'本体 L ≤ 18 mm',ha='center',fontsize=12)
ax.annotate('',xy=(14,-3.75),xytext=(14,3.75),arrowprops=dict(arrowstyle='<->',color='#304955'))
ax.text(15,0,'D ≤ 7.5 mm',va='center',fontsize=12)
ax.annotate('两端过渡区：各 x ≤ 3 mm\n虚线是保守占位，不是实际外形',xy=(10.5,3.5),xytext=(-17,9),fontsize=12,
            arrowprops=dict(arrowstyle='-',color='#8a672f'),color='#8a672f')
ax.text(0,0,'最大本体包络\n实际腰部与圆角未标尺寸',ha='center',va='center',fontsize=13,color='#4f3519')
ax.set(xlim=(-22,26),ylim=(-8,12),aspect='equal');ax.axis('off')
fig.suptitle('AC05 候选：补齐尺寸包络，尚未确定安装',x=.07,y=.96,ha='left',fontsize=18)
fig.text(.07,.20,'两款共用 AC05 本体：5.6 Ω / AC05000005608JAC00；10 Ω / AC05000001009JAC00。',fontsize=10.5)
fig.text(.07,.14,'引线直径 0.8 ± 0.03 mm；目录名义质量 1.90 g/只。引线成形、固定与热间距仍待定。',fontsize=10.5)
fig.text(.07,.075,'原图 B = 63 ± 1 mm 是图示端部／编带基准尺寸；这里不把它当作安装节距或剪线长度。',fontsize=10,color='#67716d')
fig.subplots_adjust(left=.05,right=.95,bottom=.25,top=.85)
for ext in ['png','svg']:fig.savefig(HERE/('dimensions.'+ext),facecolor=fig.get_facecolor())
plt.close(fig)
notes='''# AC05 两款制动电阻候选：独立尺寸包络

本记录仅补齐已交接候选的可追溯尺寸模型，不选择安装位置，不改MORI主模型。

- 轮驱候选：Vishay AC05000005608JAC00，5.6 Ω ±5%。
- 头部候选：Vishay AC05000001009JAC00，10 Ω ±5%。
- 来源：Vishay文件28730，05-Dec-2024，第10页；输入PDF哈希见reference.json。
- 本体最大长度18 mm、最大直径7.5 mm；两端过渡区各最长3 mm。过渡区径向形状未标，模型用与本体等径的线框保守占位。
- 引线直径0.8 ±0.03 mm，名义质量每只1.90 g。模型质量不按最大圆柱体体积反推。
- B63 ±1 mm依原图保留为图示基准距离，不能直接拿来当成最终安装节距或剪线长度。

`AC05_MAX_ENVELOPE_NOT_INSTALLED.blend`为独立编辑文件：两个最大本体圆柱＋四个端部过渡线框。两候选只是分开摆放以便查看，没有安装到机器人。原图的细腰、端部圆角和引线成形都没有假装精确建出。全部物体为PLACEHOLDER、橙色，逐字段记录VENDOR_DOCUMENTED数据；没有MEASURED项。

仍需硬件给出实际工作点/脉冲及温升限制、导线连接与绝缘方案、安装座或端子型号、邻近PA12和电池的隔热要求。不能根据5 W名称或体积编造一个安全热间距。完整安装包络、载流、温升及实物固定均BLOCKED/NOT_TESTED。

没有导出制造STL，没有采购或加工放行。模型只是规划参考。
'''
(HERE/'README.md').write_text(notes)
page=HERE/'index.html'
page.write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AC05 制动电阻尺寸参考</title><style>body{background:#f3f5f4;color:#253b3c;font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:970px;margin:auto;padding:30px 22px 60px}a{color:#166b70}img{max-width:100%;border:1px solid #d7dfda}aside{background:#fff0d5;padding:18px;border-left:4px solid #b58a33}</style><main><p><a href="../index.html">返回打样前工作</a></p><h1>两只制动电阻：已有独立尺寸包络</h1><p>按Vishay原图补齐两款AC05候选的最大本体和端部过渡区域。原图没有标的细腰、圆角没有伪造为精确尺寸。仍是未选定安装方案的参考件，未放入机器人。</p><img src="dimensions.png" alt="AC05的18毫米最大本体长度，7.5毫米最大直径和两端3毫米过渡区域"><aside>安装座、引线成形、绝缘和热间距尚未确定。图中位置不是机器人安装位置，名义尺寸通过不能替代热和脉冲验证。</aside><p><a href="AC05_MAX_ENVELOPE_NOT_INSTALLED.blend">独立Blender参考模型</a> · <a href="reference.json">逐字段尺寸与源哈希</a> · <a href="README.md">建模范围及缺项</a> · <a href="../../../../hardware/v1_2/prearrival_20261002/sources/vishay_ac.pdf">已保存的厂家PDF</a></p><p><small>来源：Vishay文件28730，05-Dec-2024，第10页。PROTOTYPE / UNVALIDATED。</small></p></main></html>''')
s=read(PARENT/'work_status.json')
entry=dict(id='AC05_reference_envelopes',status='PASS',detail='两款AC05候选的18×Ø7.5最大本体、两端x≤3过渡占位已建立独立Blender模型，源页/哈希留存。完整引线、固定与热间距未定，未放入主模型。')
s['completed']=[r for r in s['completed'] if r['id']!=entry['id']]+[entry]
s['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
write(PARENT/'work_status.json',s)
p=PARENT/'index.html';text=p.read_text()
text=re.sub(r'<section id="AC05-reference">.*?</section>','',text,flags=re.S)
text=text.replace('<main>','<main><section id="AC05-reference"><h2>制动电阻尺寸参考</h2><p><a href="resistor_reference/index.html">两款AC05候选包络已补齐</a>，未放入机器人；安装和热间距仍待硬件输入。</p></section>',1)
p.write_text(text)
for target in [page,p]:
    for link in re.findall(r'(?:href|src)=["\']([^"\']+)',target.read_text()):
        if link.startswith(('http:','https:','#','data:','mailto:')):continue
        assert (target.parent/link.split('#')[0].split('?')[0]).resolve().exists(),(target,link)
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:58201/'+str(target.relative_to(ROOT)),method='HEAD'),timeout=10) as r:assert r.status==200
for name in ['M1_47_delivery.json','harness_A2/delivery.json']:
    doc=read(PARENT/name)
    for target in [PARENT/'work_status.json',p]:
        key=str(target.relative_to(ROOT))
        if key in doc['files']:doc['files'][key]=sha(target)
    write(PARENT/name,doc)
files={str(p.relative_to(ROOT)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='delivery.json' and '__pycache__' not in str(p)}
write(HERE/'delivery.json',dict(status='PASS',scope='AC05 reference only',files=files,
    source_main_sha256=d['main_sha256'],main_geometry_changed=False,manufacturing_release=False,
    commands=['/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python mechanical/studies/prearrival_finish/resistor_reference/build_reference.py',
              '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/resistor_reference/publish_reference.py']))
print('AC05_REFERENCE_PUBLISHED',len(files))
