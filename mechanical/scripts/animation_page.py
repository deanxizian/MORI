"""Publish the actual native Blender assembly-animation deliverables."""
from pathlib import Path
import json,html,hashlib,re


def generate(root):
    root=Path(root);out=root/'animation';mp=out/'manifest.json'
    if not mp.exists():return ''
    m=json.loads(mp.read_text());source=root/'mori_v1_2.blend'
    if not m.get('rendered_video'):
        return ''
    if hashlib.sha256(source.read_bytes()).hexdigest()!=m['source_blend_sha256']:
        config=json.loads((root.parent/'config/geometry.json').read_text())
        if not config.get('waveshare_detail',{}).get('enabled'):return ''
        # Keep the last verified video explicitly historical; never relabel its
        # old component geometry as the current Waveshare reconstruction.
        video=out/m['video']['file'];oldblend=root/'mori_assembly_animation.blend'
        assert hashlib.sha256(video.read_bytes()).hexdigest()==m['video']['sha256']
        assert hashlib.sha256(oldblend.read_bytes()).hexdigest()==m['animation_blend_sha256']
        oldrev=html.escape(m['revision']);rev=html.escape(config['revision'])
        notice=f'当前总装为{rev}；相机安装干涉待适配，动画保留已验证的{oldrev}，不包含本轮微雪器件细节。'
        if config.get('head_mount_simplification',{}).get('enabled'):
            notice+=' 动画中的旧舵机座台阶已在当前模型撤回，头壳固定孔也已重新居中；该视频不能用来确认这些当前结构。'
        page=f'<!doctype html><html lang=zh><meta charset=utf-8><title>MORI {oldrev} 历史动画</title><style>body{{max-width:1100px;margin:30px auto;padding:24px;font:16px/1.7 system-ui;background:#edf0ef;color:#234}}video{{width:100%}}.notice{{padding:20px;background:#fff1d7}}</style><h1>MORI 装配动画 · {oldrev}</h1><p class=notice>{notice}</p><video controls preload=metadata poster=step_18.png><source src=MORI_assembly.mp4 type=video/mp4></video><p><a href=../mori_assembly_animation.blend>上一版动画Blender</a> · <a href=../studies/waveshare_detail/index.html>当前微雪模型与安装冲突</a> · <a href=../index.html>当前总装</a></p><p>动画仅为步骤说明，未证明连续装配路径、工具与真实线束空间。</p></html>'
        (out/'index.html').write_text(page)
        return f'<section id="animation"><h2>装配动画保留{oldrev}</h2><p>{notice}</p><p><a href="animation/index.html">查看上一版动画</a></p></section>'
    v=json.loads((out/'validation.json').read_text());assert v['status']=='PASS'
    video=out/m['video']['file']
    assert video.exists() and hashlib.sha256(video.read_bytes()).hexdigest()==m['video']['sha256']==v['video']['sha256']
    assert hashlib.sha256((root/'mori_assembly_animation.blend').read_bytes()).hexdigest()==m['animation_blend_sha256']
    esc=html.escape
    animation_revision=m.get('animation_revision',m['revision'])
    asset_tag=esc(animation_revision+'-'+m['video']['sha256'][:12])
    poster=f'step_{m["stage_count"]:02d}.png'
    buttons=''.join(f'<button type="button" data-time="{(s["start"]-1)/m["fps"]:.3f}"><span>{s["index"]:02d}</span>{esc(s["title"])}</button>' for s in m['stages'])
    caption=f'{m["duration_seconds"]:g} 秒 · {m["fps"]} fps · {m["resolution"][0]}×{m["resolution"][1]} · {m["stage_count"]} 个步骤'
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI 装配动画</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#12181e;color:#e5edf3;font:16px/1.75 system-ui,sans-serif}}main{{max-width:1220px;margin:auto;padding:28px}}h1{{margin:0;font-size:32px}}p{{color:#b4c4cf}}a{{color:#88dde5}}video{{width:100%;display:block;border-radius:12px;background:#313b43}}.links{{display:flex;flex-wrap:wrap;gap:20px;margin:18px 0}}.chapters{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px;margin:18px 0}}button{{display:flex;align-items:center;gap:14px;text-align:left;color:#dbe6ed;background:#26323d;border:1px solid #394c59;border-radius:9px;padding:12px;cursor:pointer;font:inherit}}button:hover,button.active{{border-color:#81d6de;background:#2d454e}}button span{{color:#8bdddf}}.note{{padding:16px 20px;background:#25313c;border-radius:10px}}@media(max-width:700px){{main{{padding:16px}}}}</style>
<main><h1>MORI · 装配动画</h1><p>{esc(animation_revision)} · {caption}。由 {esc(m['revision'])} 主模型渲染。</p>
<div class="links"><a href="../mori_assembly_animation.blend">打开可编辑动画 .blend</a><a href="MORI_assembly.mp4" download>下载 MP4</a><a href="README.md">Blender 使用与重新生成</a><a href="../index.html?revision={esc(m['revision'])}">返回机械项目</a></div>
<video id="assembly-video" controls playsinline preload="metadata" poster="{poster}?revision={asset_tag}"><source src="MORI_assembly.mp4?revision={asset_tag}" type="video/mp4"></video>
<div class="chapters">{buttons}</div>
<p class="note">在 Blender 中打开动画文件，选择 <b>MORI_Assembly_Animation</b> 场景，按空格播放。时间轴有中文步骤标记，零件保留独立关键帧；原始总装场景也保留，可切回检查尺寸。</p>
<p>第6步的独立模块为轮驱9V、头部6V；运动5V和CAM 5V已集成在第7步的电源板上（U60/U70），没有重复装外置5V模块。依据当前已交接的P5R6电源电路。</p>
<p>动画中的位移用于装配讲解，未做整段连续扫掠或人手验证。上壳附件在独立镜头预装后切换到装入起点。内部橙色仍表示未确认件；实际配合、紧固和装配工艺需样件验证。</p>
<p><a href="validation.json">动画文件与视频检查</a> · <a href="manifest.json">步骤、帧号与来源记录</a> · <a href="../scripts/assembly_animation.py">可重复生成脚本</a></p></main>
<script>const video=document.getElementById('assembly-video');const buttons=[...document.querySelectorAll('[data-time]')];for(const b of buttons)b.addEventListener('click',()=>{{video.currentTime=Number(b.dataset.time);video.play().catch(()=>{{}})}});video.addEventListener('timeupdate',()=>{{let active=buttons[0];for(const b of buttons)if(Number(b.dataset.time)<=video.currentTime)active=b;for(const b of buttons)b.classList.toggle('active',b===active)}});</script></html>'''
    config=json.loads((root.parent/'config/geometry.json').read_text())
    if m.get('body_sequence_readback',{}).get('status')=='PASS':
        notice='<p class="note"><b>本次已更新完整视频：</b>第9–11步改为上壳与承重桥分别支承、共同下放；桥单独下降18mm并锁两枚M3，上壳最后回正落位。第13–15步为双舵机离机预装，连同C压板一起下放；第16步转动座转60°露出孔位，从上方锁两枚M3后回正，再装俯仰头部。<a href="upper_shell_path_validation.json">已检查保存后的动画关键帧</a>；线束随动和人工支承仍待验证。</p>'
        page=page.replace('<video id="assembly-video"',notice+'<video id="assembly-video"')
        page=page.replace('<div class="chapters">','<p>本视频已应用P5R7运动基板、后接口板及元件朝上的WeAct插接候选，电源保持P5R6、IMU保持P5R4。E针/孔资料矛盾、实物插合与舵盘／短轴、完整线束仍待核，不能据视频接线或下单。</p><div class="chapters">')
    elif config.get('interface_completion',{}).get('enabled'):
        notice='<p class="note"><b>当前整机装配路径审查尚未通过。</b>机身上壳仍有明确的取出干涉，改孔位候选尚未应用。此视频展示当前零件与步骤，不能据此认定整机可以按动画装好。</p>'
        page=page.replace('<video id="assembly-video"',notice+'<video id="assembly-video"')
    reaction_review=root/'studies/prearrival_finish/reaction_link_entry_baseline.json'
    reaction_open=False
    if reaction_review.exists():
        review=json.loads(reaction_review.read_text())
        sources={m['source_blend_sha256']}
        equivalence_file=root/'studies/prearrival_finish/interface_sync/source_equivalence.json'
        if equivalence_file.exists():
            eq=json.loads(equivalence_file.read_text())
            if eq.get('status')=='PASS' and eq.get('current_source_blend_sha256')==m['source_blend_sha256'] and not eq.get('changed_objects'):
                sources.add(eq['original_source_blend_sha256'])
        reaction_open=(review.get('source_blend_sha256') in sources and review.get('status')=='BLOCKED')
    if reaction_open:
        page=page.replace('<video id="assembly-video"','<p class="note"><b>新增检查：反力夹口初次装配尚未闭合。</b>螺钉工具与预装穿入会被头座挡住；此视频把它作为已预装总成展示，不能作为该处初装验证。<a href="../studies/prearrival_finish/reaction_assembly_review.html">查看现有主模型的阻挡剖面</a>。</p><video id="assembly-video"')
    if m.get('body_sequence_kind')=='front_rear':
        notice='<p class="note"><b>本版已采用前后分壳：</b>先安装并锁紧内部承重桥与头部，再分别预装前壳喇叭和后壳接口板。前后壳平移合入，由四个底部工具孔锁紧原框架螺钉；两组壳内插舌定位，旧拼缝五金取消。<a href="front_rear_path_validation.json">已回读检查保存的动画路径</a>。完整软线束随动、反力夹初装和实物配合仍未闭合。</p>'
        page=re.sub(r'<p class="note"><b>本次已更新完整视频：.*?</p>',notice,page,flags=re.S)
        page=page.replace('上壳附件在独立镜头预装后切换到装入起点。','身体前后壳附件分别在台面预装后平移合入。')
    if config.get('reaction_nut_alignment',{}).get('enabled'):
        note='<p class="note"><b>M1.52已同步两枚试配螺母的30°转正：</b>打印件与螺钉轴不动。下部横向锁紧的螺母、螺钉和名义工具进入路径通过；上部舵盘夹口仍按预装总成演示，初装工序及最终接口未完成。<a href="../studies/prearrival_finish/reaction_access_M1_51/index.html">查看剖面与检查范围</a>。</p>'
        page=page.replace('<div class="chapters">',note+'<div class="chapters">')
    (out/'index.html').write_text(page)
    section=f'''<section id="animation"><h2>Blender 装配动画</h2><p>{esc(animation_revision)} · {caption}。<a href="mori_assembly_animation.blend">打开可编辑动画文件</a> · <a href="animation/index.html">分步骤播放</a> · <a href="animation/README.md">使用说明</a></p><video controls playsinline preload="metadata" poster="animation/{poster}?revision={asset_tag}" style="width:100%;border-radius:12px"><source src="animation/MORI_assembly.mp4?revision={asset_tag}" type="video/mp4"></video><p>实际模型、独立关键帧与中文时间轴标记。装配移动是示意，尚未完成全程路径及手工工艺验证。</p></section>'''
    if m.get('body_sequence_readback',{}).get('status')=='PASS':
        section=section.replace('<h2>Blender 装配动画</h2>','<h2>Blender 装配动画</h2><p class="notice">完整视频已并入上壳／承重桥的独立分步运动，以及小舵机离机预装顺序。保留M1.44防脱压板，已应用P5R7板卡与插接候选；完整线束和舵盘资料仍待完成。</p>')
    elif config.get('interface_completion',{}).get('enabled'):
        section=section.replace('<h2>Blender 装配动画</h2>','<h2>Blender 装配动画</h2><p class="notice">当前上壳服务路径尚未通过，视频是零件与步骤展示；待确认的候选没有混入动画。</p>')
    if reaction_open:
        section=section.replace('<h2>Blender 装配动画</h2>','<h2>Blender 装配动画</h2><p class="notice">反力夹口初装与工具路线仍受头座阻挡；视频中的预装总成不构成该处装配证明。<a href="studies/prearrival_finish/reaction_assembly_review.html">查看检查剖面</a>。</p>')
    if m.get('body_sequence_kind')=='front_rear':
        section=re.sub(r'<p class="notice">完整视频已并入上壳.*?</p>',
            '<p class="notice">已同步前后分壳、底部插舌及四枚框架螺钉的装配顺序。完整线束和反力夹初装仍待完成；视频不作为整机可制造或实物装配证明。</p>',section,flags=re.S)
    if config.get('reaction_nut_alignment',{}).get('enabled'):
        section=section.replace('已同步前后分壳、底部插舌及四枚框架螺钉的装配顺序。','已同步两枚试配螺母方向，以及前后分壳、底部插舌及四枚框架螺钉的装配顺序。')
    return section


if __name__=='__main__':generate(Path(__file__).resolve().parents[1])
