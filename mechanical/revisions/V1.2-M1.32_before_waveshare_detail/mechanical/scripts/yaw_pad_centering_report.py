"""Publish actual-model comparisons for the authorized centered seat contours."""
import json


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text())
    if not p.get('head_servo_detail',{}).get('centered_yaw_pads',{}).get('enabled'):return ''
    r=json.loads((root/'reports/yaw_pad_centering_validation.json').read_text());rev=p['revision']
    motion=json.loads((root/'reports/head_motion.json').read_text())
    note='两处Yaw舵机安装座的顶部承压面已围绕原孔位收齐为矩形。孔距、座面高度、舵机及五金位置保持；前侧保持规整直角柱，后侧连接臂保留在承压面下方。不增加打印件、螺钉或走线孔。'
    detail=f'顶部承压面均为11 × 4.8 mm，孔距仍为28.5 mm。后侧连接臂下移{r["rear_arm_drop_mm"]:.1f} mm，实测模型厚度仍为{r["rear_arm_thickness_from_mesh_mm"]:.1f} mm，与转轴夹座的实际网格最小间隙为{r["reaction_link_actual_min_gap_mm"]:.2f} mm。这里的“下移”仅指连接臂，舵机和承压面没有下移。'
    checks=f'局部几何检查 {r["status"]}：与M1.31比较仅Pitch_Yoke变化，所有其他零件的网格和装配矩阵相同；支架为单个连续实体，孔周承压材料及嵌件孔腔保持。顶部孔中心偏差小于0.003 mm数值检查阈值；原直角接角没有重新出现残料。整机{motion["poses"]}个联合姿态（Yaw 10°、Pitch 5°步长）发现{len(motion["failures"])}处模型穿插，有限采样不等于连续运动或完整实物装配认证。'
    limits='上述尺寸为模型几何值。打印强度、嵌件抗拔、实物公差与最终舵盘配合尚未验证；走线仍按要求延后。'
    title='舵机固定凸台：保持孔位，轮廓居中'
    def pair(key,caption):
        return '<h2>'+caption+'</h2><div class="grid">'+''.join(f'<figure><a href="{tag}_{key}.png"><img src="{tag}_{key}.png?revision={rev}" alt="{label}"></a><figcaption>{label}</figcaption></figure>' for tag,label in [('before','M1.31 · 修改前'),('after',rev+' · 修改后')])+'</div>'
    sections=pair('pads','两处顶部承压面')+pair('rear','后侧保留完整连接臂')+pair('mounted','原位安装的Yaw舵机')+pair('yoke','支架整体')
    page=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 舵机座居中</title><style>body{{max-width:1200px;margin:30px auto;padding:0 24px;background:#eef0ed;color:#233432;font:16px/1.75 system-ui}}a{{color:#216556}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}figure{{margin:0;background:white}}img{{width:100%;display:block}}figcaption{{padding:12px}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}</style><a href="../../index.html?revision={rev}#yaw-pad-centering">← 当前总装</a><h1>{title}</h1><p>{note}</p><p>{detail}</p><p><a href="../../mori_v1_2.blend">总装 Blender</a> · <a href="../../animation/index.html?revision={rev}">装配动画</a> · <a href="../../exports/stl/Pitch_Yoke.stl">候选支架 STL</a></p>{sections}<h2>检查结果</h2><p>{checks}</p><p>{limits}</p><p><a href="../../reports/yaw_pad_centering_validation.json">局部检查</a> · <a href="../../reports/validation.json">整机检查</a> · <a href="after_render_manifest.json">实际模型渲染来源</a></p></html>'''
    (root/'studies/yaw_pad_centering/index.html').write_text(page)
    (root/'reports/舵机凸台居中.md').write_text(f'# {title} · {rev}\n\n'+ '\n\n'.join([note,detail,checks,limits])+'\n\n[实际模型对比](../studies/yaw_pad_centering/index.html) · [执行命令](yaw_pad_centering_commands.json)\n')
    for path in [root/'README.md',root/'reports/REPORT.md']:
        first,rest=path.read_text().split('\n',1)
        link='舵机凸台居中.md' if path.parent.name=='reports' else 'reports/舵机凸台居中.md'
        path.write_text(first+f'\n\n{note} [当前修改]({link})\n'+rest)
    return f'<section id="yaw-pad-centering"><h2>{title}</h2><p>{note}</p><div class="links"><a href="studies/yaw_pad_centering/index.html?revision={rev}">同视角前后对比</a><a href="reports/舵机凸台居中.md">尺寸与检查</a></div><div class="grid"><a class="card" href="studies/yaw_pad_centering/index.html"><img src="studies/yaw_pad_centering/after_pads.png?revision={rev}" alt="孔居中的两个承压面"></a><a class="card" href="studies/yaw_pad_centering/index.html"><img src="studies/yaw_pad_centering/after_rear.png?revision={rev}" alt="完整保留的下方连接臂"></a></div></section>'
