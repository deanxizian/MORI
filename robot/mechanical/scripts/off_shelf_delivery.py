"""Publish the executed off-shelf adoption, without reusing old fit claims."""
import argparse
import datetime
import hashlib
import html
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


STYLE = '''*{box-sizing:border-box}body{margin:0;background:#eff1ef;color:#263238;font:16px/1.75 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:28px}h1{font-size:34px;line-height:1.25}h2{margin-top:38px}a{color:#126774}nav,.links{display:flex;flex-wrap:wrap;gap:18px;margin:20px 0}nav{border-bottom:1px solid #ccd4d4;padding-bottom:12px}figure{margin:0}img,video{display:block;width:100%;border-radius:8px}figcaption{padding:10px 0;color:#4e6168}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.note{padding:16px 20px;background:#e0e8e8;border-left:3px solid #668b90}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #ccd4d4}code{overflow-wrap:anywhere}small{color:#5a6c72}.chapters{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px;margin:20px 0}button{font:inherit;text-align:left;padding:9px 12px;background:#fff;border:1px solid #c5d2d4;border-radius:5px;cursor:pointer}button.active{border-color:#126774;background:#d5e7e7}@media(max-width:700px){main{padding:18px}.grid{grid-template-columns:1fr}h1{font-size:28px}}'''


def document(title, content):
    return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style><main>{content}</main></html>'


def verify(project=PROJECT, check_animation=True):
    """Require current source hashes, successful saved-file checks and exports."""
    project=Path(project);root=project/'mechanical';reports=root/'reports'
    p=read(project/'config/geometry.json');q=p['off_shelf_modules']
    assert q['enabled'] and q['approved']
    model_hash=sha(root/'mori.blend')
    build=read(reports/'build_manifest.json');v=read(reports/'validation.json')
    assert v['revision']==p['revision'] and v['source_blend_sha256']==model_hash
    assert v['counts']['FAIL']==0
    for name,digest in build['input_sha256'].items():
        assert sha(project/name)==digest, 'Stale build input: '+name
    scope=read(reports/'off_shelf_scope.json');mount=read(reports/'off_shelf_mount_validation.json')
    assert scope['status']==mount['status']=='PASS' and not scope['hardware_drift']
    assert read(reports/'body_split_validation.json')['status']=='PASS'
    ex=read(reports/'export_manifest.json')
    assert ex['candidate_count']==ex['exported_count']==20
    for item in ex['parts']:
        assert item['status']==item['blender_reimport']['status']=='PASS'
        assert sha(root/item['file'])==item['sha256']
    assert not (root/'exports/stl/Battery_Tray.stl').exists()
    renders=read(reports/'off_shelf_render_manifest.json')
    assert renders['revision']==p['revision'] and renders['source_blend_sha256']==model_hash
    dc=p.get('dc_inlet_trial',{}).get('enabled',False)
    controls=p.get('ups_rear_controls',{}).get('enabled',False)
    assert len(renders['views'])==(9 if controls else 8 if dc else 6)
    if controls:
        check=read(reports/'ups_controls_validation.json')
        assert check['status']=='PASS' and check['source_blend_sha256']==model_hash
        assert check['unchanged_existing_count']==188 and check['changed_existing_ids']==['Body_Rear']
        assert not set(check['retired_ids']).intersection(read(reports/'assembly_instances.json'))
        gap=read(reports/'ups_controls_clearances.json')
        assert gap['status']=='PASS' and gap['source_blend_sha256']==model_hash
    elif dc:
        check=read(reports/'dc_inlet_validation.json')
        assert check['status']=='PASS' and check['source_blend_sha256']==model_hash
        assert check['unchanged_existing_count']==192 and check['changed_existing_ids']==['Body_Rear']
    for item in renders['views']:
        assert sha(root/item['file'])==item['sha256'] and (root/item['file']).stat().st_size==item['bytes']
    detail=read(reports/'electronics_detail_manifest.json')
    assert detail['revision']==p['revision'] and detail['source_main_sha256']==model_hash
    assert read(reports/'electronics_detail_validation.json')['status']=='PASS'
    ids=set(read(reports/'assembly_instances.json'))
    assert len(ids)==scope['part_count']==build['parts']
    assert not ids.intersection(q['retired_ids'])
    assert {'UPS_Module','IMU_BMI323','Head_Buck_6V'}<=ids
    if not check_animation:
        return p,v,None
    m=read(root/'animation/manifest.json');av=read(root/'animation/validation.json')
    assert m['revision']==p['revision'] and m['source_blend_sha256']==model_hash and m['off_shelf_adopted']
    if dc:
        assert m['dc_inlet_trial_adopted']
        ids=set(p['dc_inlet_trial']['reference_ids'])
        assert ids<=set(m['part_stages'])
        rear=read(reports/'body_split_validation.json')['modules']['rear']
        assert ids<=set(rear)
    assert m['rendered_video'] and av['status']=='PASS' and av['all_actor_meshes_match_source']
    assert av['animation_revision']==m['animation_revision']
    assert sha(root/'mori_assembly_animation.blend')==m['animation_blend_sha256']
    assert sha(root/'animation/MORI_assembly.mp4')==m['video']['sha256']==av['video']['sha256']
    up=read(root/'animation/off_shelf_path_validation.json')
    assert up['status']=='PASS' and up['source_blend_sha256']==model_hash and up['animation_blend_sha256']==m['animation_blend_sha256']
    for key in ['body_sequence_readback','head_retention_readback']:
        assert av[key]['status']=='PASS'
    for s in m['stages']:
        assert (root/'animation'/f'step_{s["index"]:02d}.png').is_file()
    ids=set(read(reports/'assembly_instances.json'))
    assert len(ids)==scope['part_count']==build['parts']
    assert not ids.intersection(q['retired_ids'])
    assert {'UPS_Module','IMU_BMI323','Head_Buck_6V'}<=ids
    return p,v,m


def current_report(project=PROJECT, model_only=False):
    project=Path(project);root=project/'mechanical'
    errors=[]
    try:
        p,v,m=verify(project,check_animation=not model_only)
    except (AssertionError,KeyError,OSError,ValueError) as error:
        errors=[str(error) or repr(error)]
        p=read(project/'config/geometry.json');v=read(root/'reports/validation.json')
    rows=['build_manifest','validation','off_shelf_scope','off_shelf_mount_validation','body_split_validation',
          'export_manifest','off_shelf_render_manifest','electronics_detail_validation']
    if p.get('ups_rear_controls',{}).get('enabled'):rows+=['ups_controls_geometry','ups_controls_validation','ups_controls_clearances']
    elif p.get('dc_inlet_trial',{}).get('enabled'):rows+=['dc_inlet_geometry','dc_inlet_validation']
    result=dict(revision=p['revision'],status='FAIL' if errors else 'PASS',errors=errors,
        validation_counts=v['counts'],source_blend_sha256=sha(root/'mori.blend'),
        evidence_sha256={f'reports/{n}.json':sha(root/'reports'/f'{n}.json') for n in rows},
        scope=('Current saved main, approved adoption comparison, static views, STL and electronic detail only; no animation regeneration or verification this run.' if model_only else 'Current saved main, approved adoption comparison, actual-model views, 20 STL readbacks, electronic detail and saved animation/video consistency only.'),
        animation_checked_this_run=not model_only,
        whole_product='PROTOTYPE / UNVALIDATED',complete_harness='BLOCKED',electrical_adaptation='BLOCKED',physical_strength='NOT_TESTED',manufacturing_release=False)
    links=''.join(f'<li><a href="reports/{n}.json">{n}</a></li>' for n in rows)
    body=f'<h1>{p["revision"]} · 当前检查</h1><p class="note">文件与执行证据一致性：<b>{result["status"]}</b>。整机仍为 PROTOTYPE / UNVALIDATED，未制造放行。</p>'
    body+=f'<p>本轮几何统计：{v["counts"]["PASS"]} PASS、{v["counts"]["FAIL"]} FAIL、{v["counts"]["BLOCKED"]} BLOCKED、{v["counts"]["NOT_TESTED"]} NOT_TESTED。统计只覆盖报告列出的检查范围。</p>'
    body+=('<p>本轮只更新并核对主模型、静态视图、STL 和电子细模；动画未在本轮生成或检查。待用户确认模型后，再按需更新视频。</p>' if model_only else '<p>当前视图、20 个候选 STL、电子细模与动画均追溯到同一已保存主模型。旧版 delivery_consistency / render_manifest / 线束结果保留为历史，不据此放行新电气架构。</p>')
    if errors:body+='<ul>'+''.join('<li>'+html.escape(e)+'</li>' for e in errors)+'</ul>'
    body+='<ul>'+links+'</ul><p><a href="index.html">当前模型</a> · <a href="animation/index.html">当前动画</a> · <a href="../docs/CURRENT_STATUS.md">未完成事项</a></p>'
    (root/'current_report.html').write_text(document('MORI 当前检查',body))
    result['html_sha256']=sha(root/'current_report.html');write(root/'reports/current_report.json',result)
    if errors:raise RuntimeError('Off-shelf delivery evidence failed: '+str(errors))
    return result


def animation_page(project, m):
    root=Path(project)/'mechanical';out=root/'animation';esc=html.escape
    rev=m['animation_revision'];tag=rev+'-'+m['video']['sha256'][:12]
    caption=f'{m["duration_seconds"]:g} 秒 · {m["stage_count"]} 步 · {m["frame_range"][1]} 帧 · {m["fps"]} fps · 1280×720'
    buttons=''.join(f'<button data-time="{(s["start"]-1)/m["fps"]:.3f}">{s["index"]:02d}　{esc(s["title"])}</button>' for s in m['stages'])
    video=f'<video id="assembly-video" controls playsinline preload="metadata" poster="step_22.png?revision={tag}"><source src="MORI_assembly.mp4?revision={tag}" type="video/mp4"></video>'
    body=f'<h1>MORI · 装配动画</h1><p>{rev} · {caption}</p><nav><a href="../index.html">当前主模型</a><a href="../mori_assembly_animation.blend">可编辑 Blender 动画</a><a href="MORI_assembly.mp4" download>下载 MP4</a><a href="README.md">使用说明</a></nav>'
    body+='<p class="note">已同步 UPS 直固、居中 WeAct＋载板、两侧 BMI323 与微雪 6 V Buck。独立电池托盘、旧自制电源板、旧 IMU 和两块旧 Buck 已取消。</p>'+video
    body+='<div class="chapters">'+buttons+'</div><p>第 6 步先在台面固定两块小板，再安装承重板；第 7 步从前方送入 UPS、上抬到座面，安装四枚 M3×25 穿栓和四枚螺母。UPS 需人工托住；第 8 步安装居中的主控组。</p>'
    body+=f'<p>已回读全部 {m["actor_count"]} 个动画物体的网格及最终位姿；UPS 装入按半帧抽样 239 次，另复核前后壳、承重桥及头部防脱步骤。没有完成全动画连续扫掠、人手、扳手摆动或完整带线装配验证。</p>'
    body+='<p>内部橙色为未完整确认件：6 V Buck 暂用同系列 7.2 V 原厂 CAD；新紧固件是标准名义外形。后接口板保留旧版几何，DC 电气接入、供电能力及物理断电仍待电气适配。视频不可用作接线或制造放行依据。</p>'
    if m.get('dc_inlet_trial_adopted'):
        body+='<p class="note">M1.57 后壳已增加 Ø8 试配孔及 4 mm 一体座。橙色插座和螺母是样品容量参考，作为已预装后壳一起展示；完整尾线穿孔和实际锁紧仍待试配。<a href="../../docs/M1_57_DC_TRIAL_ADOPTION.md">采用记录</a></p>'
    body+='<p><a href="validation.json">文件与视频检查</a> · <a href="off_shelf_path_validation.json">UPS 动画路径</a> · <a href="manifest.json">帧号与来源</a> · <a href="../../docs/M1_56_OFF_SHELF_ADOPTION.md">M1.56 采用记录</a></p>'
    body+='''<script>const video=document.getElementById('assembly-video');const buttons=[...document.querySelectorAll('[data-time]')];for(const b of buttons)b.addEventListener('click',()=>{video.currentTime=Number(b.dataset.time);video.play().catch(()=>{})});video.addEventListener('timeupdate',()=>{let active=buttons[0];for(const b of buttons)if(Number(b.dataset.time)<=video.currentTime)active=b;for(const b of buttons)b.classList.toggle('active',b===active)});</script>'''
    (out/'index.html').write_text(document('MORI '+rev,body))
    (out/'README.md').write_text(f'''# MORI 装配动画 · {rev}

打开 `mori_assembly_animation.blend`，选择 `MORI_Assembly_Animation` 场景，空格播放。Shift＋左方向键回到开头。原始 `MORI_V1_Assembly` 场景保留真实尺寸总装。

{caption}。22 个中文时间轴标记切换相机；每个零件保留独立关键帧。

本版取消独立 Battery_Tray、旧电源板、旧 IMU 与旧两块 Buck。第 6 步在台面安装侧边 BMI323 和微雪 6 V Buck，再固定承重板。第 7 步托住 UPS 从前方送入，先处于座面下方 0.5 mm，再上抬到位，以四枚 M3×25 和四枚螺母固定。第 8 步安装居中 WeAct＋载板。维修需打开前后身体壳，托住 UPS，再拆固定件、下降并向前退出。

头部保留 CAM USB 朝机器人右侧 +X、C6 通道、R2 裸反力轴装入、防脱压板及 6806ZZ 轴承。实际舵盘、锁紧叠层和完整带线初装仍未验证。

已回读 {m['actor_count']} 个物体网格及最终位姿；UPS 239 次半帧抽样、前后壳／桥和防脱步骤的已声明抽样通过。视频是刚体装配说明，全程连续扫掠、人手／夹具、工具完整操作、柔性线束和物理公差没有完成。内部橙色为未确认件。Buck 暂借同系列 7.2 V CAD，后接口板仍是待适配历史版本。

{('M1.57 后壳已采用 Ø8 试配孔和 4 mm 一体座；插座与螺母作为已预装的样品容量参考展示，未演示或验证完整尾线穿孔。详见[采用记录](../../docs/M1_57_DC_TRIAL_ADOPTION.md)。' if m.get('dc_inlet_trial_adopted') else '')}

当前主模型成功构建后，运行 `python3 mechanical/scripts/run_off_shelf_deliverables.py` 更新检查、导出、视图和动画。依赖恢复见[采用记录](../../docs/M1_56_OFF_SHELF_ADOPTION.md)。这不是上电、采购或制造授权。
''')
    return f'<section id="animation"><h2>装配动画 · {rev}</h2><p>{caption}。<a href="animation/index.html">分步播放</a> · <a href="mori_assembly_animation.blend">Blender 动画</a></p><video controls preload="metadata" poster="animation/step_22.png?revision={tag}"><source src="animation/MORI_assembly.mp4?revision={tag}" type="video/mp4"></video><p>已同步直固 UPS 的支撑、送入和锁紧顺序。完整线束和实际操作工艺仍未验证。</p></section>'


def publish(project=PROJECT):
    project=Path(project);root=project/'mechanical';p,v,m=verify(project)
    current_report(project)
    from animation_page import generate
    section=generate(root)
    # Preserve the previous gallery at its original relative resource depth.
    history=root/'index_M1_55_history.html'
    if not history.exists():
        old=(root/'index.html').read_text()
        assert 'V1.2-M1.55' in old
        notice='<p style="padding:20px;background:#ffe4b0;color:#222">历史 M1.55 图册，不代表当前 UPS 架构。<a href="index.html">返回当前 M1.56</a>。其中模型下载入口指向历史 Git 提交；当前文件请从新首页进入。</p>'
        old=old.replace('<main>', '<main>'+notice, 1)
        commit='7e75d8d9dec161207fe49ef85508f86ca6dd731e'
        for name in ['mori.blend','mori_electronics_detail.blend','mori_assembly_animation.blend','animation/index.html','animation/MORI_assembly.mp4']:
            old=old.replace('href="'+name+'"','href="https://github.com/deanxizian/MORI/blob/'+commit+'/mechanical/'+name+'"')
        history.write_text(old)
    dc=p.get('dc_inlet_trial',{}).get('enabled',False)
    image_folder='dc_trial_M1_57' if dc else 'off_shelf_M1_56'
    images=lambda name,label:f'<figure><a href="renders/{image_folder}/{name}.png"><img loading="lazy" src="renders/{image_folder}/{name}.png" alt="{label}"></a><figcaption>{label}</figcaption></figure>'
    body=f'<h1>MORI <small>{p["revision"]}</small></h1><p>UPS 直接固定 · 主控居中 · BMI323 与 6 V Buck 分列两侧</p><nav><a href="#layout">当前结构</a><a href="#ups">UPS 固定</a><a href="#animation">装配动画</a><a href="#files">模型文件</a><a href="#checks">检查与待办</a></nav>'
    body+='<p class="note">用户已确认并应用到正式主模型，候选与当前文件已分清。PROTOTYPE / UNVALIDATED；本轮尚未提交或发布到 GitHub。</p>'
    if dc:
        body+='<section id="dc"><h2>后壳充电试配孔座 · M1.57</h2><p>只改 Body_Rear：后侧中线、原壳面高度约 130 mm，Ø8 试孔、Ø15×4 mm 一体座；外侧座面内收 0.5 mm，无新增打印件。安装关系为插座从外向内穿入、螺母在内侧锁紧。</p><div class="grid">'+images('dc_seat','当前主模型的试配孔；隐藏参考插座以查看座面')+images('dc_inside','从后壳内侧看一体座和橙色样品插座／螺母参考')+'</div><p>其余 192 件原件网格与位姿保持。新增两件参考对象代表样品原有插座和螺母，完整尾线穿孔、孔径公差与实际锁紧仍需试配；未新增电源开关孔。<a href="../docs/M1_57_DC_TRIAL_ADOPTION.md">采用记录</a> · <a href="exports/stl/Body_Rear.stl">当前后壳 STL</a></p></section>'
    body+='<section id="layout"><h2>当前结构</h2><div class="grid">'+images('assembled','外形与四个执行器保留')+images('internal','当前主模型内部结构，独立电池托盘已移除')+'</div><p>WeAct＋载板整组居中，BMI323 位于左侧，微雪 6 V Buck 位于右侧。原电源板、旧 IMU 和旧降压模块从机械总装移除；原生 PCB 与电气合同保持不动，后续功能适配单独交接。</p>'+images('top_modules','上层布局：左 BMI323，中间主控＋载板，右 6 V Buck（同系列 CAD 占位）')+'</section>'
    body+='<section id="ups"><h2>UPS 无托盘直固</h2><p>UPS 后移 12 mm；四个短座并入 Load_Frame，用四枚 M3×25 穿栓和四枚 M3 螺母固定原厂四孔。少一件打印件，原两枚托盘侧锁螺钉及两个嵌件取消。机器人本体打印件为 15 件。</p><div class="grid">'+images('ups_direct','UPS 与承重板的直接固定关系')+images('ups_joint','原厂固定孔、承压短座与穿栓螺母')+'</div><p>维修：打开前后身体壳，托住 UPS，使用短 L 扳手与下方套筒拆四组固定件，下降 0.5 mm 后向前退出。长直螺丝刀通道受遮挡；人手支撑与扳手完整摆动需实物验证。</p></section>'
    body+=section
    body+='<section id="files"><h2>当前文件</h2><div class="links"><a href="mori.blend">完整主模型 .blend</a><a href="mori_electronics_detail.blend">电子细模 .blend</a><a href="mori_assembly_animation.blend">装配动画 .blend</a><a href="exports/stl/Load_Frame.stl">承重板 STL</a><a href="reports/export_manifest.json">20 个候选 STL 清单</a><a href="LATEST_MODEL.md">文件位置说明</a></div><p>20 个 STL 包括 15 件机器人打印件、1 件维护底座和 4 件试片。场景另有四块软接触垫参考，未导出为 STL；软垫不作为 PA12 本体件计重。新增螺钉和螺母是采购五金，不是打印件。</p></section>'
    body+=f'<section id="checks"><h2>检查与未完成项</h2><p>当前名义几何记录：{v["counts"]["PASS"]} PASS、0 FAIL、{v["counts"]["BLOCKED"]} BLOCKED、{v["counts"]["NOT_TESTED"]} NOT_TESTED。已核对批准候选和逐件范围、20 个 STL 回读及 130 个组合头姿态。分项限制见当前检查报告。</p>'
    body+='<p>UPS 固定、短工具直线进入、板卡装入及 UPS 向前取出通过名义检查。完整线束、DC 尾线穿孔及电气接入、电源同时负载能力、物理断电／互锁、6 V Buck 实物版本、实际舵盘与 PA12 强度仍待完成；不能据此认定已经可以完整制造或上电。</p><div class="links"><a href="current_report.html">当前检查报告</a><a href="../docs/M1_56_OFF_SHELF_ADOPTION.md">M1.56 采用记录</a><a href="../docs/CURRENT_STATUS.md">当前未完成事项</a><a href="index_M1_55_history.html">历史 M1.55 图册</a></div></section>'
    (root/'index.html').write_text(document('MORI '+p['revision'],body))
    paths=[root/'index.html',root/'current_report.html',root/'animation/index.html',root/'animation/README.md',root/'mori.blend',root/'mori_electronics_detail.blend',root/'mori_assembly_animation.blend',root/'animation/MORI_assembly.mp4']
    write(root/'reports/off_shelf_delivery.json',dict(status='PASS',revision=p['revision'],animation_revision=m['animation_revision'],
        finalized_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_blend_sha256=sha(root/'mori.blend'),
        files={str(f.relative_to(project)):sha(f) for f in paths},scope='Local approved mechanical adoption and current deliverable consistency; no GitHub publication or manufacturing release.',manufacturing_release=False))
    animation_files=[root/'mori_assembly_animation.blend',root/'scripts/assembly_animation.py',root/'scripts/render_current_animation.py',
                     root/'scripts/check_assembly_animation.py',root/'scripts/check_off_shelf_animation.py',Path(__file__)]
    animation_files += [root/'animation'/n for n in ['MORI_assembly.mp4','manifest.json','validation.json','index.html','README.md',
                         'commands.json','CHANGELOG_M1_56_A1.md','off_shelf_path_validation.json','front_rear_path_validation.json','head_retention_path_validation.json']]
    animation_files += sorted((root/'animation').glob('step_*.png'))
    if dc:
        animation_files += [root/'animation/CHANGELOG_M1_57_A1.md',root/'scripts/dc_inlet_trial.py',root/'scripts/validate_dc_inlet_trial.py',
                            root/'reports/dc_inlet_validation.json']
    write(root/'animation/delivery.json',dict(animation_revision=m['animation_revision'],source_revision=p['revision'],
        source_blend_sha256=m['source_blend_sha256'],source_unchanged=True,video_status='PASS',off_shelf_adopted=True,
        body_sequence_readback=m['body_sequence_readback'],head_retention_readback=m['head_retention_readback'],
        files={str(f.relative_to(root)):sha(f) for f in animation_files},
        scope='Local files only; declared rigid paths and video decode checked, full wired/manual process not qualified.',manufacturing_release=False))
    print('OFF_SHELF_DELIVERY_PUBLISHED',p['revision'],flush=True)


def publish_model_review(project=PROJECT):
    """Publish static review without relabeling or replacing the last video."""
    project=Path(project);root=project/'mechanical';p,v,_=verify(project,check_animation=False)
    current_report(project,model_only=True)
    views=read(root/'reports/off_shelf_render_manifest.json')['views']
    labels={'assembled':'当前总装','internal':'当前内部结构','top_modules':'上层板卡',
            'ups_direct':'UPS 直固','ups_joint':'UPS 固定细节','load_frame':'承重板',
            'dc_seat':'后壳 DC 试配孔座','dc_inside':'DC 内侧样品容量参考',
            'controls_rear':'后侧：上充电、下开关','controls_inside':'内侧：两个原配器件容量参考','controls_shell':'后壳：旧 Type-C 孔与接口板固定座已删除'}
    body=f'<h1>MORI <small>{p["revision"]}</small></h1><p class="note">本轮更新模型与静态图，先核对方案和模型，再按需更新视频。现有视频没有在本轮重新生成。</p>'
    if p.get('ups_rear_controls',{}).get('enabled'):
        body+='<p>已采用上充电、下开关；取消旧 Type-C 孔、接口板及其固定座。只改后壳，不增加打印件。两只原配器件按样品容量建模，实际孔径及尾线穿入待试配。<a href="../docs/M1_58_UPS_CONTROLS_ADOPTION.md">采用记录</a>。</p>'
    body+='<p>当前 20 个 STL 为 15 件本体件、1 件维护底座和 4 件试片；四块软接触垫仅为未导出的场景参考。</p>'
    mass_path=root/'studies/mass_inertia_M1_58/mass_ledger.json'
    if mass_path.exists():
        mass=read(mass_path)
        if mass.get('source_main_sha256')==sha(root/'mori.blend') and mass.get('calculation_status')=='PASS':
            body+=f'<p id="mass_current">本体 PA12 打印件参考重量 {mass["subtotal_components_g"]["PA12_SOLID_ESTIMATE"]:.1f} g；完整整机重量、重心和惯量待补。<a href="studies/mass_inertia_M1_58/index.html">当前质量账目与缺项</a>。</p>'
    body+='<nav><a href="mori.blend">完整主模型</a><a href="mori_electronics_detail.blend">电子细模</a><a href="reports/export_manifest.json">STL 清单</a><a href="current_report.html">本轮检查</a><a href="../docs/CURRENT_STATUS.md">当前状态</a></nav><div class="grid">'
    for view in views:
        file=html.escape(view['file']);label=labels.get(Path(view['file']).stem,Path(view['file']).stem)
        body+=f'<figure id="{Path(view["file"]).stem}"><a href="{file}"><img src="{file}" alt="{label}"></a><figcaption>{label}</figcaption></figure>'
    body+='</div><p>PROTOTYPE / UNVALIDATED。完整线束、实物配合与强度等限制仍按当前检查保留；本页不是制造或上电放行。</p>'
    old=root/'animation/manifest.json'
    if old.exists():
        m=read(old);rev=html.escape(m.get('animation_revision',m['revision']))
        body+=f'<p>上一次视频：{rev}，未在本轮更新，可能与当前模型有差异。<a href="animation/index.html">查看上次视频及其原始版本记录</a>。</p>'
    (root/'index.html').write_text(document('MORI '+p['revision']+' 模型检查',body))
    files=[root/'index.html',root/'current_report.html',root/'mori.blend',root/'mori_electronics_detail.blend']
    write(root/'reports/model_review_delivery.json',dict(status='PASS',revision=p['revision'],
        source_blend_sha256=sha(root/'mori.blend'),animation_regenerated=False,
        files={str(f.relative_to(project)):sha(f) for f in files},manufacturing_release=False))
    print('MODEL_REVIEW_PUBLISHED_WITHOUT_VIDEO',p['revision'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');parser.add_argument('--model-only',action='store_true');args=parser.parse_args()
    if args.check_only:verify(check_animation=not args.model_only);print('OFF_SHELF_DELIVERY_PASS',flush=True)
    elif args.model_only:publish_model_review()
    else:publish()
