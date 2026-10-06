"""Current two-corner edit, sourced from the actual model and checks."""
import json


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text())
    if not p.get('head_print_cleanup',{}).get('cradle_rear_corner_chamfer_mm',0):return ''
    r=json.loads((root/'reports/head_corner_validation.json').read_text())
    v=json.loads((root/'reports/validation.json').read_text())
    motion=json.loads((root/'reports/head_motion.json').read_text())
    rev=p['revision'];c=r['chamfer_leg_mm'];dest=root/'studies/head_corner_chamfer'
    title=f'头托后侧两角 · {c:g} mm × 45°倒角'
    note=f'按标记，仅削去Pitch_Cradle后侧两个外角。两侧对称，倒角沿后侧竖边贯穿；内壁平面、轴孔、头壳安装孔和屏幕连接孔原位保留。'
    checks=f'与M1.26逐件比较，只有Pitch_Cradle网格改变。现有两件轮驱修改保持；没有增加打印件或紧固件。角部18条实体射线中，最小法向壁厚约{r["minimum_sampled_corner_normal_wall_mm"]:.1f} mm，相邻直壁仍为{r["nominal_adjacent_wall_mm"]:g} mm。'
    limit=f'专项检查{r["status"]}；完整模型{v["counts"]["PASS"]} PASS / {v["counts"]["FAIL"]} FAIL。头部联合{motion["poses"]}姿态为有限采样。打印强度、真实公差与未齐全器件的装配仍待验证，不能据此认定实机已合格。'
    style='*{box-sizing:border-box}body{margin:0;background:#eef0ed;color:#233432;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1240px;margin:auto;padding:32px 24px 75px}h1{font-size:34px}h2{margin-top:38px}a{color:#216556}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border-radius:12px;overflow:hidden}img{width:100%;display:block}figcaption{padding:12px 18px}.notice{padding:18px;background:#fff4d9;border-radius:10px}@media(max-width:700px){.grid{grid-template-columns:1fr}}'
    comparisons=''
    for key,label in [('cradle','头托整体'),('corner','外角局部'),('head','同一套头部装配')]:
        comparisons+=f'<h2>{label}</h2><div class="grid"><figure><img src="before_{key}.png?revision={rev}" alt="倒角前{label}"><figcaption>修改前 · M1.26</figcaption></figure><figure><img src="after_{key}.png?revision={rev}" alt="倒角后{label}"><figcaption>当前 · M1.27</figcaption></figure></div>'
    page=f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 头托后角倒角</title><style>{style}</style><main><a href="../../index.html#head-corners">← 当前总装</a><h1>{title}</h1><p>{note}</p><p><a href="../../mori_v1_2.blend">当前Blender</a> · <a href="../../animation/index.html?revision={rev}">同步装配动画</a></p>{comparisons}<h2>检查范围</h2><p>{checks}</p><div class="notice">{limit}</div><p><a href="../../reports/head_corner_validation.json">局部检查数据</a> · <a href="../../reports/validation.json">全局检查</a> · <a href="../../reports/head_corner_commands.json">实际执行命令</a> · <a href="after_render_manifest.json">渲染来源</a></p></main></html>'
    (dest/'index.html').write_text(page)
    md=f'# {title} · {rev}\n\n{note}\n\n{checks}\n\n{limit}\n\n共享尺寸：config/geometry.json#/head_print_cleanup/cradle_rear_corner_chamfer_mm。仅两条后侧外角；没有恢复其他切角或台阶。\n\n[实际模型前后对比](../studies/head_corner_chamfer/index.html)\n'
    (root/'reports/头托后角倒角.md').write_text(md)
    for path in [root/'README.md',root/'reports/REPORT.md']:
        text=path.read_text();first,rest=text.split('\n',1)
        link='头托后角倒角.md' if path.parent.name=='reports' else 'reports/头托后角倒角.md'
        path.write_text(first+f'\n\n本轮修改：{title}，只改变头托后侧外角。 [{title}]({link})\n'+rest)
    return f'<section id="head-corners"><h2>{title}</h2><p>{note}</p><p>{checks}</p><div class="links"><a href="studies/head_corner_chamfer/index.html?revision={rev}">倒角前后对比</a><a href="reports/头托后角倒角.md">检查与参数</a></div><a class="card" href="studies/head_corner_chamfer/index.html?revision={rev}"><img style="width:100%;max-width:950px" src="studies/head_corner_chamfer/after_cradle.png?revision={rev}" alt="实际头托两角倒角模型"></a></section>'
