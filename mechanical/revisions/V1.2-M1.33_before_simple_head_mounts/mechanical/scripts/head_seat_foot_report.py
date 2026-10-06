"""Publish the local front-foot correction with actual-model comparison views."""
import json


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text())
    if not p.get('head_servo_detail',{}).get('front_corner_cleanup',{}).get('enabled'):return ''
    r=json.loads((root/'reports/head_seat_foot_validation.json').read_text());rev=p['revision']
    title='直角接合处的多余填充已清除'
    note='保留原来的直角安装座，只清除接角处旧几何叠加留下的窄条和弧形残料。安装座外形、座面、螺孔、嵌件和舵机位置保持，没有增加斜撑、零件或螺钉。'
    check=f'局部检查 {r["status"]}：与M1.30逐件对比，仅Pitch_Yoke接角处减少材料，没有新增结构。原矩形柱体、安装座面及孔腔在0.005 mm³布尔运算数值容差内保持一致。支架仍为单个连续实体。打印强度和实物装配未验证，走线继续延后。'
    if p['head_servo_detail'].get('centered_yaw_pads',{}).get('enabled'):
        note='M1.31清除的直角接角残料继续保持清除。当前M1.32另按确认方案将两处舵机座顶部轮廓以孔为中心收齐，并保留下方连接臂；此处不再宣称安装座整个外形与M1.30相同。孔位、舵机和直角接合形式保持。'
        check=f'接角残料检查 {r["status"]}：当前支架仍为单个连续实体，未新增斜撑。凸台的新轮廓、承压面及连接间隙见舵机座居中检查。打印强度和实物装配未验证，走线继续延后。'
    def pair(key,caption):
        return '<h2>'+caption+'</h2><div class="grid">'+''.join(f'<figure><img src="{tag}_{key}.png?revision={rev}" alt="{label}"><figcaption>{label}</figcaption></figure>' for tag,label in [('before','M1.30 · 修改前'),('after',rev+' · 修改后')])+'</div>'
    sections=pair('head','同一视角的头部总成')+pair('foot','原直角接合处局部')+pair('side','侧向正交检查')
    page=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 舵机座底脚</title><style>body{{max-width:1200px;margin:30px auto;padding:0 24px;background:#eef0ed;color:#233432;font:16px/1.75 system-ui}}a{{color:#216556}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}figure{{margin:0;background:white}}img{{width:100%;display:block}}figcaption{{padding:12px}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}</style><a href="../../index.html?revision={rev}#head-seat-foot">← 当前总装</a><h1>{title}</h1><p>{note}</p><p><a href="../../mori_v1_2.blend">总装 Blender</a> · <a href="../../animation/index.html?revision={rev}">装配动画版本说明</a></p>{sections}<h2>检查范围</h2><p>{check}</p><p><a href="../../reports/head_seat_foot_validation.json">局部网格检查</a> · <a href="../../reports/validation.json">完整几何检查</a> · <a href="after_render_manifest.json">渲染来源</a></p></html>'''
    (root/'studies/head_seat_foot/index.html').write_text(page)
    (root/'reports/舵机座直角清理.md').write_text(f'# {title} · {rev}\n\n{note}\n\n{check}\n\n[前后对比](../studies/head_seat_foot/index.html) · [局部检查](head_seat_foot_validation.json)\n')
    for path in [root/'README.md',root/'reports/REPORT.md']:
        first,rest=path.read_text().split('\n',1)
        link='舵机座直角清理.md' if path.parent.name=='reports' else 'reports/舵机座直角清理.md'
        path.write_text(first+f'\n\n{note} [本轮修改]({link})\n'+rest)
    return f'<section id="head-seat-foot"><h2>{title}</h2><p>{note}</p><div class="links"><a href="studies/head_seat_foot/index.html?revision={rev}">同视角前后对比</a><a href="reports/舵机座直角清理.md">局部检查</a></div><div class="grid"><a class="card" href="studies/head_seat_foot/index.html"><img src="studies/head_seat_foot/before_foot.png?revision={rev}" alt="旧接角残料"></a><a class="card" href="studies/head_seat_foot/index.html"><img src="studies/head_seat_foot/after_foot.png?revision={rev}" alt="清理后的直角"></a></div></section>'
