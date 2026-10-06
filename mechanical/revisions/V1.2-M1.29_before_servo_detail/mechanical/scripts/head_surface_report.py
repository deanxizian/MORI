"""Explain the display-normal repair with fixed-camera model renders."""
import json


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text());s=p.get('head_surface_display',{})
    if not s.get('enabled'):return ''
    r=json.loads((root/'reports/head_surface_validation.json').read_text());rev=p['revision']
    title='头部平面 · 消除假折皱'
    note='圈出的尖三角、波纹状明暗没有结构作用，来自显示法线：孔边及耳座过渡处的平滑法线被插值到相邻平面，少量细小布尔三角面还存在法线数值偏差。已显式保存结构平面的实际面法线，并明确分开曲面边界；圆孔、轴颈与弧形挡边继续平滑显示。'
    facts=f'与{s["baseline_revision"]}逐件核对，全部零件的顶点、三角面和装配位置一致。这次修正显示法线，实际4.5 mm壁厚、大折角和安装孔均保留。'
    detail='前座的圆孔、斜向线束让位和下部运动接口属于实际几何，仍保留；本次没有把功能孔槽填平。'
    checks=f'专项检查：{r["status"]}。检查了'+str(sum(x['checked_planar_faces'] for x in r['parts']))+'个平面三角面在Blender中的显示法线，同时确认曲面仍使用平滑着色。强度及实际装配公差仍待实物验证。'
    style='*{box-sizing:border-box}body{margin:0;background:#eef0ed;color:#233432;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1240px;margin:auto;padding:32px 24px 70px}h1{font-size:34px}h2{margin-top:36px}a{color:#216556}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border-radius:12px;overflow:hidden}img{display:block;width:100%}figcaption{padding:12px 18px}.notice{padding:18px;background:#fff4d9;border-radius:10px}@media(max-width:700px){.grid{grid-template-columns:1fr}}'
    sections=''
    for key,label in [('cradle','头托侧板与安装耳'),('front_seat','前座与下方平面'),('yoke','双轴支架整体')]:
        sections+=f'<h2>{label}</h2><div class="grid"><figure><img src="before_{key}.png?revision={rev}" alt="修正前{label}"><figcaption>修正前 · {s["baseline_revision"]}</figcaption></figure><figure><img src="after_{key}.png?revision={rev}" alt="修正后{label}"><figcaption>修正后 · {rev}</figcaption></figure></div>'
    page=f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 头部表面修正</title><style>{style}</style><main><a href="../../index.html#head-surfaces">← 当前总装</a><h1>{title}</h1><p>{note}</p><p>{facts}</p><p><a href="../../mori_v1_2.blend">当前Blender模型</a> · <a href="../../animation/index.html?revision={rev}">同步装配动画</a></p>{sections}<h2>检查范围</h2><p>{detail}</p><div class="notice">{checks}</div><p><a href="../../reports/head_surface_validation.json">专项检查</a> · <a href="../../reports/head_surface_commands.json">实际执行命令</a> · <a href="after_render_manifest.json">渲染来源</a></p></main></html>'
    (root/'studies/head_surface_cleanup/index.html').write_text(page)
    (root/'reports/头部表面显示修正.md').write_text(f'# {title} · {rev}\n\n{note}\n\n{facts}\n\n{detail}\n\n{checks}\n\n[实际模型前后对比](../studies/head_surface_cleanup/index.html)\n')
    for file in [root/'README.md',root/'reports/REPORT.md']:
        text=file.read_text();first,rest=text.split('\n',1);link='头部表面显示修正.md' if file.parent.name=='reports' else 'reports/头部表面显示修正.md'
        file.write_text(first+f'\n\n本轮修改：头部平面显示法线修正，消除假折皱。 [修正说明]({link})\n'+rest)
    return f'<section id="head-surfaces"><h2>{title}</h2><p>{note}</p><p>{facts}</p><div class="links"><a href="studies/head_surface_cleanup/index.html?revision={rev}">修正前后对比</a><a href="reports/头部表面显示修正.md">检查说明</a></div><a class="card" href="studies/head_surface_cleanup/index.html?revision={rev}"><img style="width:100%;max-width:950px" src="studies/head_surface_cleanup/after_cradle.png?revision={rev}" alt="头托平面显示修正后的实际模型"></a></section>'
