"""Dimension key and read-only review page for the separately exported gauges."""
from pathlib import Path
import json, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
HERE=Path(__file__).resolve().parent
OUT=HERE/'fit_coupons'
q=json.loads((OUT/'manifest.json').read_text());assert q['status']=='PASS'
plt.rcParams['font.family']=['Arial Unicode MS','PingFang SC','DejaVu Sans']
fig,axs=plt.subplots(2,1,figsize=(12,6.5),layout='constrained')
fig.patch.set_facecolor('#f3f6f7')
for ax,row in zip(axs,q['parts']):
    w,h,_=row['size_mm']
    ax.add_patch(Rectangle((-w/2,-h/2),w,h,fc='#d4e3e6',ec='#294950'))
    ax.add_patch(Rectangle((-w/2,-h/2),2,2,fc='white',ec='white'))
    for i,(x,d) in enumerate(zip(row['x_centres_mm'],row['diameters_mm'])):
        nominal=q['trial_dimensions']['housing_bore_mm' if row['kind']=='bore' else 'journal_diameter_mm']
        ax.add_patch(Circle((x,0),d/2,fc='white' if row['kind']=='bore' else '#718d94',ec='#224853',lw=1.2))
        color='#075e4c' if d==nominal else '#203d46'
        ax.text(x,-h/2-4,f'{i+1}  Ø{d:g}',ha='center',va='top',fontsize=12,color=color,weight='bold' if d==nominal else 'normal')
        if d==nominal:ax.text(x,0,'当前名义尺寸',ha='center',va='center',fontsize=10,color=color if row['kind']=='bore' else 'white')
    ax.text(-w/2,-h/2-4,'定位缺角 ↗',ha='right',va='top',fontsize=10)
    ax.set_title(('C08 · 6806 外圈座孔试片 162 × 54 × 9 mm' if row['kind']=='bore' else 'C09 · 6806 内圈轴颈试片 176 × 42 mm；底板 3 mm，轴颈露出 8 mm'),fontsize=13)
    ax.set_xlim(-104,94);ax.set_ylim(-h/2-13,h/2+3);ax.set_aspect('equal');ax.axis('off')
fig.savefig(OUT/'dimension_key.png',dpi=150);fig.savefig(OUT/'dimension_key.svg');plt.close(fig)
files=''.join(f'<li><a href="{r["id"]}.stl">{r["id"]}.stl</a>：'+('座孔 ' if r['kind']=='bore' else '轴颈 ')+ ' / '.join(f'{d:g} mm' for d in r['diameters_mm'])+'</li>' for r in q['parts'])
(OUT/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · PA12 / 6806 试配片</title><style>body{margin:0;background:#f2f6f7;color:#243c45;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1100px;margin:auto;padding:28px}img{width:100%;display:block;background:white}a{color:#146b83}h1{font-size:30px}.note{padding:16px;background:#fff0d7;border-radius:10px}figure{margin:20px 0}figcaption{padding:10px;background:white}</style><main><a href="../index.html">← 当前颈部结构</a><h1>6806 轴承的 PA12 试配片</h1><p>独立于机器人总装的两片小样。对应 30 × 42 × 7 mm 轴承；不再使用旧 C04 / C05 的 32 / 20 mm 尺寸来判断当前配合。</p><figure><img src="overview.png" alt="三座孔和四轴颈独立试片的Blender渲染"><figcaption>同一生成脚本导出 STL 与预览。每片左下角的缺角用于辨认方向。</figcaption></figure><figure><img src="dimension_key.png" alt="各座孔及轴颈直径标注"><figcaption>俯视尺寸索引，尺寸单位 mm；绿色标出当前模型名义值，尚未根据实物定配合。</figcaption></figure><h2>文件与记录</h2><ul>'''+files+'''<li><a href="MORI_PA12_6806_fit_coupons.blend">可编辑 Blender 文件</a></li><li><a href="measurements.csv">测量记录 CSV</a> · <a href="manifest.json">拓扑与实际回读记录</a> · <a href="dimension_key.svg">矢量尺寸索引</a></li></ul><h2>试配方法</h2><p>与受影响的打印件采用相同 PA12 工艺，记录厂家、批次及打印方向。先测座孔两个方向、轴颈两个方向和轴承实物，再逐档试配，记录能否装入、松动和转动情况。不要以强行压入的结果认定配合合适。</p><p>座孔片只筛查外圈径向配合，轴颈片只筛查内圈径向配合；原模型的肩部、防脱间隙、螺钉锁紧和承载仍需另行验证。M3 嵌件可使用<a href="../../../../prearrival_preparation/jlc_coupons/index.html">此前独立试片</a>中的 C02，并核对当前 Ø4.05 mm 试验底孔。</p><p class="note">这两片不是新增机器人零件，也未下单。STL 拓扑、连续实体及实际导入检查通过；实物配合、蠕变、冲击和强度均未验证。</p></main></html>'''.replace('../../../../prearrival_preparation','../../../prearrival_preparation'))
manifest={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'dimension_key.png',OUT/'dimension_key.svg',OUT/'index.html']}
(OUT/'review_manifest.json').write_text(json.dumps(dict(status='PASS',source_blend_sha256=q['source_blend_sha256'],files=manifest),indent=2)+'\n')
print('FIT_COUPONS_PUBLISHED')
