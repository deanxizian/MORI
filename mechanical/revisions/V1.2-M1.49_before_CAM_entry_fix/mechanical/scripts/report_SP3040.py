"""Publish the user-selected SP3040 model, evidence and shell interface."""
from pathlib import Path
import hashlib
import html
import json


def generate(root, rev, current_report):
    root = Path(root)
    study = root / 'studies/speaker_SP3040_review'
    read = lambda path: json.loads(path.read_text())
    params = read(root.parent / 'config/geometry.json')
    speaker = params['detail_fit']['speaker']
    scope = read(root / 'reports/speaker_SP3040_scope.json')
    fit = read(root / 'reports/speaker_replacement_validation.json')
    validation = read(root / 'reports/validation.json')
    checks = {c['id']: c for c in validation['checks']}
    renders = read(study / 'render_manifest.json')
    animation = read(root / 'animation/manifest.json')
    blend_hash = hashlib.sha256((root / 'mori_v1_2.blend').read_bytes()).hexdigest()
    assert scope['status'] == 'PASS' and validation['counts']['FAIL'] == 0
    assert scope['gasket_triangles_inside_clear_aperture'] == 0
    assert renders['revision'] == animation['revision'] == rev
    assert renders['source_blend_sha256'] == animation['source_blend_sha256'] == blend_hash
    assert animation['source_is_unchanged'] and animation['meshes_share_exact_source_data']
    assert all(hashlib.sha256((study / v['file']).read_bytes()).hexdigest() == v['sha256']
               for v in renders['views'].values())
    checked = ['enclosed_speaker_nominals', 'speaker_shell_attachment',
               'speaker_shell_tool_access', 'speaker_blind_boss_skin',
               'speaker_max_box_envelope', 'speaker_rear_vent_reserve',
               'speaker_removal_path', 'speaker_front_grille_paths', 'speaker_SP3040_scope']
    assert all(checks[n]['status'] == 'PASS' for n in checked)

    gap = fit['attachment']['frame_gap_mm']
    description = ('按用户提供的 WSS-SP3040-08 / YH-SP3040-08 规格书替换喇叭：'
                   '箱体42×30×9mm，比原45×45×25mm喇叭薄16mm；'
                   '总耳长56mm、两孔距49±0.5mm。出声面位置保持，安装座与软垫按新箱体调整。')
    mount = ('喇叭两侧安装耳直接固定到上壳内的一体座，使用两枚M2×6螺钉和两枚试配M2嵌件。'
             '上壳拆下后从喇叭背面拧入；拆下两枚螺钉后可沿背面退出。'
             '新增打印件0，新增紧固件0；本体仍为15件候选打印件。')
    estimates = ('未标注的安装耳先按图示比例估算：耳宽10mm、厚1.5mm、前表面距喇叭出声面5.5mm、'
                 '外角R2.8mm；箱体圆角R5.5mm、振膜图示33×23mm也为估算。'
                 '这些字段为ASSUMED，模型安装耳以橙色提示；没有标记为原厂CAD或实测。')
    limit = ('图中孔标注“2”暂按Ø2mm理解。它与M2螺钉没有名义径向余量，'
             '49±0.5mm孔距公差也尚未完成实物配合校准；没有擅自扩大采购件的孔。'
             '到货后需核实孔径、孔距、耳厚、耳的前后位置，再定安装座与紧固件。')
    evidence = (f'实际网格尺寸、壳内接触、盲孔背部材料、台面工具与装入路径检查通过；'
                f'喇叭距Load_Frame最近约{gap:.2f}mm。41个1mm步长的退出位置和原有15个声孔通路通过。'
                f'上壳仍为一个连续实体，局部喇叭区域以外的实体差异为'
                f'{scope["shell_change_outside_speaker_region_mm3"]:.3g}mm³（数值误差范围）。'
                '软垫开口内另做实际三角面检查，残余薄片为0。'
                '最大箱体公差检查不包含未标注安装耳或孔距公差；几何通过不等于打印强度、声学或实物装配通过。')
    extra = ('厂表为4Ω、额定3W、最大3.5W，实际功放输出未验证。喇叭重量未提供；'
             '质量预算暂留31.5g估算占位，不能当作此型号重量或上限。'
             '线束按用户要求延后；接头具体系列、出线位置与弯曲仍待核。没有采购或制造放行。')
    source_path = '../../sources/SP3040/SP3040_user_specification.pdf'
    source_hash = params['speaker_update']['source_sha256']
    assert hashlib.sha256((root.parent / speaker['source']).read_bytes()).hexdigest() == source_hash
    titles = [
        ('speaker_front', 'SP3040正面：箱体与孔距按厂图；橙色安装耳含估算尺寸'),
        ('speaker_side', '侧面：9mm箱体、软垫与两枚M2×6；安装耳厚度和深度为估算'),
        ('shell_seats', '上壳内的一体安装座；没有新增独立支架'),
        ('shell_mounted', '上壳拆下后的背面装配与螺钉操作方向'),
    ]

    def gallery(prefix=''):
        return '<div class="grid">' + ''.join(
            f'<figure><a href="{prefix}{n}.png"><img loading="lazy" '
            f'src="{prefix}{n}.png?revision={rev}" alt="{html.escape(t)}"></a>'
            f'<figcaption>{html.escape(t)}</figcaption></figure>' for n, t in titles) + '</div>'

    section = (f'<section id="speaker"><h2>本轮：SP3040薄喇叭与壳内安装座</h2>'
               f'<p>{description}</p><p>{mount}</p>{gallery("studies/speaker_SP3040_review/")}'
               f'<p>{estimates}</p><p class="notice">{limit}</p><p>{evidence}</p><p>{extra}</p>'
               '<div class="links"><a href="studies/speaker_SP3040_review/index.html">喇叭安装专题</a>'
               '<a href="sources/SP3040/SP3040_user_specification.pdf">用户提供规格书</a>'
               '<a href="exports/stl/Body_Upper.stl">上壳候选STL</a>'
               '<a href="reports/speaker_SP3040_scope.json">修改范围检查</a></div></section>')
    page_path = root / 'index.html'
    page = page_path.read_text()
    page = page.replace('<h1>CAM 与电池补齐固定，<br>相机由现有零件限位。</h1>',
                        '<h1>SP3040薄喇叭，<br>直接固定在肚子上壳。</h1>')
    page = page.replace('<a href="#completion">本轮固定</a>',
                        '<a href="#speaker">薄喇叭安装</a><a href="#completion">相机与电池固定</a>')
    page = page.replace('<section id="completion">', section + '<section id="completion">', 1)
    page = page.replace('所有图均来自本版实际模型。',
                        '本轮喇叭、整机与动画使用当前模型；CAM/电池专题图保留几何相同的M1.35图。')
    page_path.write_text(page)

    style = ('<style>body{max-width:1120px;margin:30px auto;padding:0 24px 50px;background:#edf0ed;'
             'color:#20312c;font:16px/1.7 system-ui,sans-serif}a{color:#17694f}'
             '.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}'
             'figure{margin:0;background:white;border-radius:10px;overflow:hidden}'
             'img{width:100%;display:block}figcaption{padding:12px}'
             '.notice{background:#fff4d7;padding:16px;border-radius:8px}'
             '@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>')
    (study / 'index.html').write_text(
        f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>MORI {rev} SP3040喇叭</title>{style}'
        f'<a href="../../index.html?revision={rev}#speaker">当前总装</a>'
        f'<h1>{rev} · SP3040喇叭安装</h1><p>{description}</p><p>{mount}</p>'
        f'{gallery()}<p>{estimates}</p><p class="notice">{limit}</p><p>{evidence}</p><p>{extra}</p>'
        f'<p><a href="{source_path}">用户规格书：第3页尺寸、第2页参数</a> · '
        '<a href="../../mori_v1_2.blend">当前Blender</a> · '
        '<a href="../../mori_assembly_animation.blend">可编辑装配动画</a> · '
        '<a href="../../animation/index.html">播放动画</a> · '
        '<a href="../../reports/speaker_replacement_validation.json">检查记录</a></p></html>')

    note = (f'# MORI {rev} · 用户选定SP3040薄喇叭\n\n{description}\n\n{mount}\n\n'
            f'{estimates}\n\n{limit}\n\n{evidence}\n\n{extra}\n\n'
            '资料：mechanical/sources/SP3040/SP3040_user_specification.pdf，第3页尺寸、第2页参数；'
            '制造商深圳市昊林电声科技有限公司；规格书WSSSZ201809110016 / 1.0。'
            f'文件SHA256：`{source_hash}`。本型号没有MEASURED字段。\n\n'
            '所有非喇叭零件的网格和姿态与归档M1.36相同；电路文件保持只读。'
            '主模型、20个候选STL（含维护座/试片）、当前预览与18步装配动画已经重新生成。'
            '实际命令与日志见SP3040_commands.json、commands.json及animation/commands.json；'
            '修改范围见speaker_SP3040_scope.json，安装检查见speaker_replacement_validation.json。\n\n')
    current = (root / 'reports' / current_report).read_text()
    current = current.replace('完整命令见assembly_completion_commands.json和commands.json。',
                              '当前命令见SP3040_commands.json和commands.json；早期补齐记录仍保留。')
    current = note + '以下保留当前整机装配进度及未完成项。\n\n' + current
    (root / 'reports' / current_report).write_text(current)
    (root / 'reports/REPORT.md').write_text(current)
    (root / 'SPEAKER_REPLACEMENT.md').write_text(note)
    for f in ['采购件选型.md', 'purchased_dimensions.md', '外购与自制.md', '设计与选型分工.md']:
        path = root / 'reports' / f
        path.write_text(path.read_text() + '\n' + note)
    assembly = root / 'reports/组装与打印.md'
    assembly.write_text(assembly.read_text().replace(
        '6. 喇叭与后接口板先固定在拆下的上壳，再合壳、装轮。',
        '6. 将SP3040与试配软垫放入拆下的上壳，两耳用两枚M2×6从背面锁到壳内M2嵌件；'
        '耳厚、孔径/孔距与预紧待实物校准。后接口板也先在上壳台面状态装好，再合壳、装轮。'))
    progress_path = root / 'reports/assembly_completion_progress.json'
    progress = read(progress_path)
    progress['rows'].insert(0, {'item': 'SP3040薄喇叭与壳内安装座', 'status': '名义几何PASS；实物配合BLOCKED',
                                'detail': description + mount + limit})
    progress['completed_nominal_items'].insert(0, 'SP3040 speaker and integral shell mounts')
    progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n')

    old_readme = study / 'README_research_before_adoption.md'
    if not old_readme.exists():
        old_readme.write_text((study / 'README.md').read_text())
    (study / 'README.md').write_text(
        note + '\n当前模型已采用用户SP3040。此前立创相似模具检索是选型前研究，未用于混合尺寸：'
        '[历史比较](README_research_before_adoption.md)、[原始数据](source_comparison.json)。\n\n'
        '[当前安装图](index.html) · [用户规格书](SP3040_user_specification.pdf)。\n')
    adoption = {'revision': rev, 'selection': speaker['model'], 'source': speaker['source'],
                'source_sha256': source_hash, 'user_authorized_undimensioned_estimates': True,
                'field_evidence': speaker['field_evidence'], 'scope': scope,
                'nominal_geometry_status': 'PASS', 'physical_fit': 'BLOCKED',
                'strength': 'NOT_TESTED', 'wiring': 'NOT_TESTED',
                'source_blend_sha256': blend_hash, 'checks': checked}
    (study / 'adoption.json').write_text(json.dumps(adoption, ensure_ascii=False, indent=2) + '\n')
    print('SP3040_REPORT_COMPLETE', rev)
