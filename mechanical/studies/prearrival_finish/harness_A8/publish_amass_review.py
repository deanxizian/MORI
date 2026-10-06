"""Publish the official source and bounded replay without overwriting history."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import font_manager
HERE=Path(__file__).resolve().parent;OUT=HERE/'amass_mating';PARENT=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
nom=read(OUT/'nominal_replay.json');upper=read(OUT/'upper_with_thickness_allocation_replay.json')
prefix=read(HERE/'body_leads/documented_mate_prefix_pools.json')
assert nom['status']=='PASS' and upper['status']==prefix['status']=='BLOCKED'
assert all(r['status']=='PASS' for r in nom['installed_wire_vs_mates']+nom['temporary_contact_sweep_vs_mates'])
assert sha(ROOT/'mechanical/mori_v1_2.blend')==nom['source_blend_sha256']
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(10,6.2),dpi=160)
colors=['#bcc6cc','#549bac','#dfa659']
for x,h,title,c in zip([0,4,8],[23.1,17.1,17.9],['旧分配\n未扣除插合量','原厂尺寸推导\n名义插合高度','公差叠加\n高度上界'],colors):
    ax.add_patch(Rectangle((x,0),2,h,fc=c,ec='#50636d',lw=1.2))
    ax.text(x+1,h+.55,f'{h:.1f} mm',ha='center',fontsize=13,bbox={'facecolor':'white','edgecolor':'none','pad':2})
    ax.text(x+1,-1,title,ha='center',va='top',fontsize=11)
ax.axhspan(17.9-.3302,17.9+.3302,color='#7b3e85',alpha=.3)
ax.axhline(17.9,color='#7b3e85',lw=1.5)
ax.text(11.1,18.7,'旧导线中心\n距板端基面17.9 mm',va='bottom',color='#693274',fontsize=11)
ax.axhline(0,color='#425966',lw=1.4)
ax.text(11.1,1.,'板端塑壳底面\nZ = 121.1 mm',va='bottom',fontsize=10)
ax.set(xlim=(-.8,15.5),ylim=(-4,26.5),ylabel='相对板端塑壳底面的高度 / mm',xticks=[])
ax.spines[['top','right','bottom']].set_visible(False);ax.grid(axis='y',alpha=.12)
ax.set_title('原厂图消除了过大的插头分配，但没有消除公差要求',fontsize=16,pad=14)
fig.text(.09,.03,'仅比较轴向高度。上界厚度5.9 mm仍为项目分配；焊点、热缩管及出线弯曲另行设计。',fontsize=10.5)
fig.tight_layout(rect=[0,.065,1,1]);fig.savefig(OUT/'height_comparison.png',facecolor='#f6f8f7');plt.close(fig)

review='''
<!-- mating-replay:start -->
## 已按新资料复核

七个电源板XT30对插研究包络已在独立计算中重建；其余22个研究包络保持。主模型、PCB及真实硬件模型没有改。

| 检查 | 结果 | 范围 |
|---|---|---|
| 名义10.2×5.6×17.1mm插合包络 | PASS | 52个局部导线/Yaw实例及4条临时参考端子扫掠，对29个插头研究包络 |
| 10.5×5.9×17.9mm上界研究包络 | BLOCKED | 52个局部导线检查均未满足分配间隙，4条端子扫掠均占用预留空间；5.9mm线端厚度是显式假设 |
| 内收板端过渡，保留上界插头包络 | BLOCKED | 内收端点过渡已避开插头，但未找到完整四线方案；剩余受承重桥、既有线束及弯曲半径限制 |

![轴向高度对比](height_comparison.png)

这证明旧23.1mm空间确实过大；也说明只按名义尺寸放线不够。新的检查仍不包含焊锡、热缩管与实际出线，不能用名义PASS发布加工图。

[名义结果](nominal_replay.json) · [上界结果](upper_with_thickness_allocation_replay.json) · [身体端新尝试](../body_leads/documented_mate_prefix_pools.json) · [命令与版本](commands.json)。有限曲线家族失败不表示所有路线无解。需要继续完成走线和固定，这部分不能归入“等实物”。
<!-- mating-replay:end -->
'''
path=OUT/'README.md';text=path.read_text()
text=text.replace('尚未更新主模型、29个插接研究包络或正式板卡。','主模型和正式板卡未改；对插研究包络的最新独立复核见下方。')
if '<!-- mating-replay:start -->' in text:text=re.sub(r'<!-- mating-replay:start -->.*?<!-- mating-replay:end -->',review.strip(),text,flags=re.S)
else:text+=review
path.write_text(text)
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>已查到的原厂插合资料 · MORI</title>
<style>body{font:16px/1.8 -apple-system,BlinkMacSystemFont,sans-serif;max-width:1000px;margin:30px auto;padding:0 24px;background:#f5f8f7;color:#283d49}h1{font-size:30px}h2{font-size:23px}img{width:100%;background:white;border-radius:8px}a{color:#086e7c}.note{padding:12px 18px;background:#fff1dc;border-left:4px solid #ba8139}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #cfdadc;text-align:left}</style>
<p><a href="../index.html">← A8原厂资料与线束研究</a></p><h1>原厂互配图已找到，并已重跑空间检查</h1>
<p>艾迈斯XT30UPB-M与XT30U-F，2025V1原厂图。互配总长20.10±0.50mm，扣除3.00±0.30mm板端焊脚，板上名义高度为17.10mm，独立公差上界17.90mm。</p>
<img src="matching_detail.png" alt="AMASS原厂互配尺寸图，明确标注XT30UPB-M与XT30U-F及20.10正负0.50mm">
<p><a href="sources/XT30UPB_M_2025V1.pdf">打开原厂完整PDF</a> · <a href="https://www.china-amass.net/xt30upb-m-product/">官方产品下载页</a> · <a href="source_receipt.json">下载时间与来源记录</a></p>
<h2>比旧分配小，仍需留公差和出线空间</h2><img src="height_comparison.png" alt="23.1mm旧分配与17.1mm名义插合高度、17.9mm上界对比">
<table><tr><th>本次复核</th><th>结果</th></tr><tr><td>7个XT30用名义插合尺寸；其他22个插头保留</td><td>局部线形与4条端子穿入扫掠PASS</td></tr><tr><td>计入高度公差、宽度公差和厚度分配</td><td>原径向段和端子扫掠仍有包络冲突</td></tr><tr><td>内收身体端过渡</td><td>已避开插头，完整四线方案仍受其他结构、既有线束和弯曲半径限制</td></tr></table>
<p class="note">整体线束仍为BLOCKED。需要继续完成路线、固定、出线及逐线长度；这些属于现在可做的设计工作。主模型未改，未发布加工图。</p>
<p>线端厚度公差未由厂家标明，5.9mm上界厚度属于研究分配；焊点和热缩管尚未纳入。不能把名义包络检查等同于实物装配通过。</p>
<p><a href="README.md">尺寸与结果完整说明</a> · <a href="nominal_replay.json">名义结果</a> · <a href="upper_with_thickness_allocation_replay.json">上界结果</a> · <a href="../body_leads/documented_mate_prefix_pools.json">身体端研究</a> · <a href="../TOOLING_DETAILS.md">JST完整端子工艺资料</a></p></html>'''
(OUT/'index.html').write_text(page)
cmd=' /Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/'
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':[
    cmd.strip()+'replay_amass_mating.py',cmd.strip()+'replay_amass_mating.py -- --upper',
    cmd.strip()+'plan_h06_documented_mates.py',
    '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/publish_amass_review.py',
    '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/verify_delivery.py'],
    'versions':{'blender':'5.2.2 LTS d13f752e3b9c','plot_python':'3.12.14'},
    'initial_script_error':'Expected8 historical XT30 boxes; current29-plug dataset contains7. Assert corrected to exact native ref set; initial error logs retained.',
    'main_model_applied':False},ensure_ascii=False,indent=2)+'\n')
detail='A8已取得JST完整端子工艺参考和AMASS 2025V1互配图。7个XT30按17.1mm名义插合高度复跑，原局部线形/端子扫掠对29个插头包络通过；按17.9mm高度上界及厚度分配仍有冲突。内收身体端过渡已避开插头，但四线成组路线、俯仰段、CAM接口、固定和逐线长度未完成。J2为独立候选，主模型未改。'
sp=PARENT/'work_status.json';state=read(sp)
old=next(r['detail'] for r in state['remaining'] if r['id']=='harness')
for row in state['remaining']:
    if row['id']=='harness':row.update(detail=detail,evidence='harness_A8/amass_mating/index.html')
state['A8_harness_research'].update(latest_review='harness_A8/amass_mating/index.html',
    AMASS_new_mating_envelope_replay='BLOCKED',
    AMASS_nominal_mating_replay='PASS',AMASS_upper_allocation_mating_replay='BLOCKED',
    AMASS_upper_depth_evidence='ASSUMED',body_prefix_after_mating_update='BLOCKED',complete_UART_harness='BLOCKED')
state['updated_utc']=datetime.now(timezone.utc).isoformat();sp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
for path,href in [(HERE/'index.html','amass_mating/index.html'),(PARENT/'index.html','harness_A8/amass_mating/index.html')]:
    text=path.read_text();block=f'<section id="threading-update"><h2>最新：已查到原厂插合图并复核</h2><p>{detail}</p><p><a href="{href}">查看原厂图、尺寸与最新复核</a>。下方保留早期研究记录。</p></section>'
    text=re.sub(r'<section id="threading-update">.*?</section>',block,text,flags=re.S).replace(old,detail);path.write_text(text)
for path in [HERE/'README.md',HERE/'terminal_threading/README.md']:
    text=path.read_text();note='\n<!-- amass-latest:start -->\n**最新补充：**新互配尺寸已复跑，名义包络通过、上界分配未通过。[查看原厂图和最新结果]('+('amass_mating/README.md' if path.parent==HERE else '../amass_mating/README.md')+')。以下首次J2记录保留为历史，完整线束仍未完成。\n<!-- amass-latest:end -->\n'
    if '<!-- amass-latest:start -->' in text:text=re.sub(r'<!-- amass-latest:start -->.*?<!-- amass-latest:end -->',note.strip(),text,flags=re.S)
    else:text=text.split('\n',1)[0]+'\n'+note+'\n'+text.split('\n',1)[1]
    path.write_text(text)
path=HERE/'terminal_threading/index.html';text=path.read_text()
note='<section id="amass-latest"><p class="note">最新补充：原厂互配尺寸已复跑。名义包络通过、上界分配仍未通过。<a href="../amass_mating/index.html">查看原厂图和最新复核</a>；下方首次J2结果保留为历史。</p></section>'
if 'id="amass-latest"' in text:text=re.sub(r'<section id="amass-latest">.*?</section>',note,text,flags=re.S)
else:text=text.replace('<table>',note+'<table>',1)
path.write_text(text)
print('AMASS_REVIEW_PUBLISHED_MAIN_UNCHANGED')
