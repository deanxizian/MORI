"""Current correction, local evidence and explicit retained camera/animation hold."""
import json


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text());s=p.get('head_mount_simplification',{})
    if not s.get('enabled'):return ''
    r=json.loads((root/'reports/simple_head_mounts_validation.json').read_text());v=json.loads((root/'reports/validation.json').read_text());rev=p['revision']
    title='头壳固定孔居中，舵机座恢复平齐'
    note='这次对应的是左右头托侧板顶端的两根头壳固定凸台。保留原8.5×6mm顶面和高度，把两处竖孔与头前壳上的对应导孔一起向内移1.25mm、向前移0.5mm。没有削薄凸台，也没有新增台阶。内部Yaw舵机座撤回误改的0.5mm台阶和轮廓变化，恢复M1.31连续平面；微雪器件仍保留M1.33详细模型。'
    detail='配对孔坐标由凸台原轮廓推导为X±46.75、Y3.5mm；原孔为X±48、Y3mm。头托通孔Ø2.4mm、头壳试配导孔Ø3.2mm及原深度保持。孔轴同时移动，采购件安装孔、舵机和转轴均不移动。'
    restoration=r['yaw_flat_restoration']
    check=f'专项检查{r["status"]}：只有Pitch_Yoke、Pitch_Cradle和Head_Front三件变化；没有新增或删除零件。头托与头壳材料差分限制在旧、新孔柱体内。两处孔轴配对且位于顶面中心；孔周探针未发现缺料。Yaw支架与M1.31实体差分{restoration["solid_symmetric_difference_mm3"]:.4g}mm³，连接臂仍为4.5mm厚；与反力轴夹座名义间隙约{restoration["reaction_link_actual_gap_mm"]:.1f}mm。'
    motion=json.loads((root/'reports/head_motion.json').read_text())
    checks=f'当前整机检查：{v["counts"]["PASS"]} PASS / {v["counts"]["FAIL"]} FAIL。头部联合{motion["poses"]}个姿态、Yaw10°与Pitch5°步长，运动检查发现{len(motion["failures"])}处刚性模型穿插。有限采样不是连续空间证明。'
    hold='M1.33已披露的相机与旧安装座/前壳内侧3对冲突仍在，本轮没有修改相机结构。装配动画保留M1.32，含已撤回的台阶，不代表当前模型；待相机适配确认及整机检查通过后再更新。'
    limit='几何检查不等于打印强度、紧固件和实物装配验证。头壳这组孔仍为试配接口，最终嵌件、螺钉长度、工具路径及打印公差待阶段B复核；走线按要求延后。'
    def pair(key,caption):
        return '<h2>'+caption+'</h2><div class="grid">'+''.join(f'<figure><a href="{tag}_{key}.png"><img src="{tag}_{key}.png?revision={rev}"></a><figcaption>{label}</figcaption></figure>' for tag,label in [('before','M1.33 · 修改前'),('after',rev+' · 修改后')])+'</div>'
    sections=pair('lug','你圈出的凸台顶面：外形保持，孔居中')+pair('cradle','左右两处同时处理')+pair('pads','撤回内部舵机座多出的台阶')+pair('head','当前头部总成')
    style='body{max-width:1200px;margin:30px auto;padding:0 24px 70px;background:#eef0ed;color:#233432;font:16px/1.75 system-ui}a{color:#216556}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0;background:white}img{width:100%;display:block}figcaption{padding:12px}.notice{padding:18px;background:#fff1d7}@media(max-width:700px){.grid{grid-template-columns:1fr}}'
    page=f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 简洁头部固定</title><style>{style}</style><a href="../../index.html?revision={rev}">← 当前总装</a><h1>{title}</h1><p>{note}</p><p>{detail}</p><p><a href="../../mori_v1_2.blend">当前总装 Blender</a> · <a href="../../exports/stl/Pitch_Cradle.stl">头托 STL</a> · <a href="../../exports/stl/Pitch_Yoke.stl">舵机 U 托 STL</a> · <a href="../../exports/stl/Head_Front.stl">头前壳 STL</a></p><div class="notice">{hold}</div>{sections}<h2>实际检查</h2><p>{check}</p><p>{checks}</p><p>{limit}</p><p><a href="../../reports/simple_head_mounts_validation.json">专项数据</a> · <a href="../../reports/simple_head_mounts_commands.json">执行命令</a> · <a href="after_render_manifest.json">实际渲染来源</a></p></html>'
    (root/'studies/simple_head_mounts/index.html').write_text(page)
    (root/'reports/头部固定简化.md').write_text(f'# {title} · {rev}\n\n'+'\n\n'.join([note,detail,check,checks,hold,limit])+'\n\n[实际前后对比](../studies/simple_head_mounts/index.html)\n')
    for path in [root/'README.md',root/'reports/REPORT.md']:
        first,rest=path.read_text().split('\n',1);link='reports/头部固定简化.md' if path.parent==root else '头部固定简化.md'
        path.write_text(first+'\n\n'+note+f' [本轮修改]({link})\n\n'+hold+'\n'+rest)
    # Retire misleading old "current" pages; preserve their comparison images.
    old=root/'studies/yaw_pad_centering/index.html'
    old.write_text(f'<!doctype html><html lang="zh"><meta charset="utf-8"><title>M1.32 已撤回</title><style>{style}</style><h1>M1.32 舵机座改动已撤回</h1><p>此处曾误认用户圈选位置，增加的台阶已在M1.34取消。</p><p><a href="../simple_head_mounts/index.html">查看当前头壳固定孔与平齐舵机座</a></p><figure><img src="after_pads.png"><figcaption>历史M1.32形状，已撤回；不是当前模型。</figcaption></figure></html>')
    (root/'reports/舵机凸台居中.md').write_text('# M1.32 舵机凸台居中改动已撤回\n\n原修改认错了用户截图位置。当前恢复平齐舵机座，另将正确的头壳固定孔配对居中。\n\n[当前说明](头部固定简化.md)\n')
    return f'<section id="simple-head-mounts"><h2>{title}</h2><p>{note}</p><p><a href="studies/simple_head_mounts/index.html?revision={rev}">同视角前后对比与检查</a></p><div class="grid"><a class="card" href="studies/simple_head_mounts/index.html"><img src="studies/simple_head_mounts/after_cradle.png?revision={rev}"><h3>头壳固定孔配对居中</h3></a><a class="card" href="studies/simple_head_mounts/index.html"><img src="studies/simple_head_mounts/after_pads.png?revision={rev}"><h3>舵机座恢复平齐</h3></a></div></section>'
