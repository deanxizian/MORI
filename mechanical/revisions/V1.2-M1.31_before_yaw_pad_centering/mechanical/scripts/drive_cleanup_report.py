"""Publish the executed lower drive-print cleanup and its retained interfaces."""
import json
from pathlib import Path


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text())
    if not p.get('drive_print_cleanup',{}).get('enabled'):return ''
    rev=p['revision'];dest=root/'studies/drive_cleanup'
    r=json.loads((root/'reports/drive_cleanup_validation.json').read_text())
    v=json.loads((root/'reports/validation.json').read_text())
    wheel=json.loads((root/'reports/wheel_interface_validation.json').read_text())
    static=json.loads((root/'reports/static_interference.json').read_text())
    export=json.loads((root/'reports/export_manifest.json').read_text())
    summary='轮驱上座改成连续平面侧壁，把四根锁紧凸柱并入壁内；共用底盖改为平板和左右连续轴承座，去掉叠加的小垫块与顶沿，四角接缝接平。'
    retained='轴承孔内的定位挡肩、底盖拆装分界、电池托盘的承托面继续保留。主托板和电池托盘本轮没有改变；两个电机、轮轴、轴承、全部螺钉及头部、电子器件都保持原位。'
    if p.get('head_servo_detail',{}).get('enabled'):
        retained='M1.26的轮驱、主托板、电池托盘和相关五金保持原几何与位置。轴承挡肩、底盖分界和电池承托面保留。本轮头部小舵机与固定座的独立变更见小舵机专项，不能把轮驱保留检查解读为头部全部未改。'
    cut=json.loads((root/'reports/drive_retained_interfaces.json').read_text())
    corners='底盖仅在底面四角保留2.5 mm三角避让面，上缘和接缝均为直角平齐；轴承座仅在外端底边保留0.9 mm避让。全部做方的试算与下壳穿插约1.32 mm³，其中底板角部约0.60 mm³、轴承座底边约0.72 mm³。这两处切角有球壳避让用途，没有保留装饰性倒角。'
    corners+=f' 当前底盖与下壳的最小名义网格间隙约{cut["current_minimum_cap_shell_gap_mm"]:.2f} mm，仍需按实际打印公差试配。'
    delta=sum(r['after'][n]['volume_mm3']-r['before'][n]['volume_mm3'] for n in r['changed_prints'])/1000
    material=f'修改的是2个既有打印件，打印件与紧固件数量均不变。理顺壁面后，模型实体体积合计变化约{delta:+.1f} cm³；这是几何体积，不是实际耗材或称重。'
    service_ok=sum(not c['failures'] for c in wheel['service_cases'])
    checks=f'专项检查{r["status"]}；下壳、共用底盖、左右电机/轴承组件的4条拆出路径，按1 mm步长检查，{service_ok}/4通过。整套轮驱每5°转一周；当前名义刚性实体穿插{len(static["failed_pairs"])}项。全局{v["counts"]["PASS"]} PASS / {v["counts"]["FAIL"]} FAIL，另有{v["counts"]["BLOCKED"]} BLOCKED / {v["counts"]["NOT_TESTED"]} NOT_TESTED。'
    limits='闭合实体、螺钉孔后的承压材料、软垫接触面、有限拆出路径与轮驱转动已检查。没有验证打印强度、预紧力、蠕变、实物公差、完整线束与实机平衡；几何通过不代表已可量产。'
    details=[('assembly','电池托盘下方的整体变化',summary),('drive','轮驱上座：连续侧壁','取消窄盒外叠四根锁紧柱和多余顶沿。M3孔与螺母收在原有宽度以内；轴输出向下取出的开口保留。'),('cap','共用底盖：一块平板与连续轴承座','两只电机软垫仍落在原来的Z=42 mm平面，没有新增浅槽或垫块。四枚M3仍从底面锁紧，头部收进沉孔。轴承中心与0.3 mm分型间隙不变，均为待实配尺寸。'),('frame','托板承托边：保留实际承重面','上方Load_Frame与Battery_Tray保持原几何；托盘由已有内侧承托面支撑。图中变动来自下方轮驱上座和底盖，不把重建网格的变化计作结构修改。')]
    sections=''.join(f'<section><h2>{title}</h2><p>{note}</p><div class="grid"><figure><img src="before_{key}.png?revision={rev}" alt="修改前{title}"><figcaption>修改前 · M1.25</figcaption></figure><figure><img src="after_{key}.png?revision={rev}" alt="修改后{title}"><figcaption>当前 · {rev}（沿用M1.26轮驱几何）</figcaption></figure></div></section>' for key,title,note in details)
    style='*{box-sizing:border-box}body{margin:0;background:#eef0ed;color:#233432;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1240px;margin:auto;padding:32px 24px 80px}h1{font-size:34px}h2{margin-top:42px}a{color:#216556}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border-radius:12px;overflow:hidden}img{width:100%;display:block}figcaption{padding:12px 18px}.notice{padding:18px;background:#fff4d9;border-radius:10px}@media(max-width:700px){.grid{grid-template-columns:1fr}}'
    page=f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 轮驱支架简化</title><style>{style}</style><main><a href="../../index.html#drive-cleanup">← 当前总装</a><h1>轮驱支架去掉多余凸条和台阶。</h1><p>{summary}</p><p>{material}</p><p><a href="../../mori_v1_2.blend">总装 Blender</a> · <a href="../../animation/index.html?revision={rev}">更新后的装配动画</a> · <a href="../../mori_assembly_animation.blend">动画 Blender</a></p>'+sections+f'<h2>留下哪些结构，为什么</h2><p>{retained}</p><p>{corners}</p><h2>实际运行与验证</h2><p>{checks}</p><p>{export["exported_count"]}个候选STL已重新导出并回读核对单位尺寸；采购件未混入STL。</p><div class="notice">{limits}</div><p>当前PCB仍为已接入的P5R2；另有硬件更新待交接，不能把本轮结构检查当作新版电路板已适配。</p><p><a href="../../reports/drive_cleanup_validation.json">专项数据</a> · <a href="../../reports/wheel_interface_validation.json">轮驱与拆装检查</a> · <a href="../../reports/drive_cleanup_commands.json">实际执行命令</a> · <a href="../../reports/drive_retained_interfaces.json">保留切角的实体试算</a></p></main></html>'
    (dest/'index.html').write_text(page)
    md=f'# 轮驱支架与底盖简化 · {rev}\n\n{summary}\n\n{material}\n\n{retained}\n\n{corners}\n\n{checks}\n\n{limits}\n\n先卸外壳、车轮和四枚底盖螺钉；底盖向下移出后，再向下拆出两组电机/轮轴/轴承。装配按逆序进行。四枚M3螺母从上方预装，锁紧预载与软垫压缩仍须试验。\n\n[实际模型修改前后](../studies/drive_cleanup/index.html) · [当前共享参数](../../config/geometry.json) · [接口与未测事项](../../contracts/mechanical_interfaces.json)\n'
    (root/'reports/轮驱打印件简化.md').write_text(md)
    for path in ([] if p.get('head_servo_detail',{}).get('enabled') else [root/'reports/REPORT.md',root/'README.md']):
        text=path.read_text();first,rest=text.split('\n',1)
        link='轮驱打印件简化.md' if path.parent.name=='reports' else 'reports/轮驱打印件简化.md'
        path.write_text(first+'\n\n'+summary+' '+material+f' [轮驱简化与验证]({link})\n'+rest)
    return f'<section id="drive-cleanup"><h2>轮驱支架已去掉多余凸条和台阶</h2><p>{summary}</p><p>{material}</p><div class="links"><a href="studies/drive_cleanup/index.html?revision={rev}">查看修改前后</a><a href="reports/轮驱打印件简化.md">保留结构的用途与检查</a></div><a class="card" href="studies/drive_cleanup/index.html?revision={rev}"><img style="width:100%;max-width:1000px" src="studies/drive_cleanup/after_assembly.png?revision={rev}" alt="M1.26 实际轮驱支架渲染"></a></section>'
