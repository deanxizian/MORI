"""Current two-corner edit, sourced from the actual model and checks."""
import json


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text())
    s=p.get('head_print_cleanup',{})
    if not s.get('cradle_rear_corner_chamfer_mm',0) and s.get('cradle_rear_profile')!='folded_u':return ''
    r=json.loads((root/'reports/head_corner_validation.json').read_text())
    v=json.loads((root/'reports/validation.json').read_text())
    motion=json.loads((root/'reports/head_motion.json').read_text())
    rev=p['revision'];dest=root/'studies/head_corner_chamfer'
    folded=r.get('profile')=='folded_u'
    title='头托后侧 · 连续大折角' if folded else f'头托后侧两角 · {r["chamfer_leg_mm"]:g} mm × 45°倒角'
    note=(f'恢复旧版M1.24的折角轮廓：后横板与左右侧板分别通过一段长约{r["outer_diagonal_length_mm"]:.1f} mm的斜壁连接。'
          f'内外轮廓一起转折，斜壁及直壁保持{r["nominal_adjacent_wall_mm"]:g} mm法向厚度，一体打印。轴孔、头壳安装孔和屏幕连接孔原位保留。') if folded else '两处后侧外角对称小倒角，内壁与孔位保留。'
    checks=f'与{r["baseline_revision"]}逐件比较，只有Pitch_Cradle网格改变。没有增加打印件或紧固件。两侧斜壁共{len(r["corner_rays"])}条实体射线中，最小法向壁厚约{r["minimum_sampled_corner_normal_wall_mm"]:.1f} mm。'
    servo_update=p.get('head_servo_detail',{}).get('enabled')
    if servo_update:
        checks=f'本轮保持M1.28大折角头托几何。两侧斜壁共{len(r["corner_rays"])}条实体射线，最小法向壁厚约{r["minimum_sampled_corner_normal_wall_mm"]:.1f} mm。小舵机、耳座及相关紧固件的变化由head_servo_validation.json单独核对。'
    limit=f'专项检查{r["status"]}；完整模型{v["counts"]["PASS"]} PASS / {v["counts"]["FAIL"]} FAIL。头部联合{motion["poses"]}姿态为有限采样。打印强度、真实公差与未齐全器件的装配仍待验证，不能据此认定实机已合格。'
    style='*{box-sizing:border-box}body{margin:0;background:#eef0ed;color:#233432;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1240px;margin:auto;padding:32px 24px 75px}h1{font-size:34px}h2{margin-top:38px}a{color:#216556}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border-radius:12px;overflow:hidden}img{width:100%;display:block}figcaption{padding:12px 18px}.notice{padding:18px;background:#fff4d9;border-radius:10px}@media(max-width:700px){.grid{grid-template-columns:1fr}}'
    comparisons=''
    for key,label in [('cradle','头托整体'),('corner','外角局部'),('head','同一套头部装配')]:
        comparisons+=f'<h2>{label}</h2><div class="grid"><figure><img src="before_{key}.png?revision={rev}" alt="修改前{label}"><figcaption>修改前 · {r["baseline_revision"]} · 小倒角</figcaption></figure><figure><img src="after_{key}.png?revision={rev}" alt="当前{label}"><figcaption>当前 · {rev} · 大折角</figcaption></figure></div>'
    reference='<h2>旧版轮廓参考 · M1.24</h2><figure><img src="reference_M1_24_cradle.png" alt="旧版斜壁轮廓"><figcaption>本次恢复此折角轮廓；当前两侧仍采用简化后的连续平壁。</figcaption></figure>' if folded else ''
    page=f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 头托大折角</title><style>{style}</style><main><a href="../../index.html#head-corners">← 当前总装</a><h1>{title}</h1><p>{note}</p><p><a href="../../mori_v1_2.blend">当前Blender</a> · <a href="../../animation/index.html?revision={rev}">同步装配动画</a></p>{comparisons}{reference}<h2>检查范围</h2><p>{checks}</p><div class="notice">{limit}</div><p><a href="../../reports/head_corner_validation.json">局部检查数据</a> · <a href="../../reports/validation.json">全局检查</a> · <a href="../../reports/head_corner_commands.json">实际执行命令</a> · <a href="after_render_manifest.json">渲染来源</a></p></main></html>'
    (dest/'index.html').write_text(page)
    md=f'# {title} · {rev}\n\n{note}\n\n{checks}\n\n{limit}\n\n共享尺寸：config/geometry.json#/head_print_cleanup。后部轮廓与旧版参数核对，局部壁厚在实际实体上采样。\n\n[实际模型前后对比](../studies/head_corner_chamfer/index.html)\n'
    (root/'reports/头托后角倒角.md').write_text(md)
    for path in ([] if servo_update else [root/'README.md',root/'reports/REPORT.md']):
        text=path.read_text();first,rest=text.split('\n',1)
        link='头托后角倒角.md' if path.parent.name=='reports' else 'reports/头托后角倒角.md'
        path.write_text(first+f'\n\n本轮修改：{title}，恢复双侧斜壁过渡。 [{title}]({link})\n'+rest)
    return f'<section id="head-corners"><h2>{title}</h2><p>{note}</p><p>{checks}</p><div class="links"><a href="studies/head_corner_chamfer/index.html?revision={rev}">折角修改前后对比</a><a href="reports/头托后角倒角.md">检查与参数</a></div><a class="card" href="studies/head_corner_chamfer/index.html?revision={rev}"><img style="width:100%;max-width:950px" src="studies/head_corner_chamfer/after_cradle.png?revision={rev}" alt="实际头托大折角模型"></a></section>'
