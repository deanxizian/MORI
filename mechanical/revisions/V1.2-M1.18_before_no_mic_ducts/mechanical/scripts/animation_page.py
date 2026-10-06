"""Publish the actual native Blender assembly-animation deliverables."""
from pathlib import Path
import json,html,hashlib


def generate(root):
    root=Path(root);out=root/'animation';mp=out/'manifest.json'
    if not mp.exists():return ''
    m=json.loads(mp.read_text());source=root/'mori_v1_2.blend'
    if not m.get('rendered_video') or hashlib.sha256(source.read_bytes()).hexdigest()!=m['source_blend_sha256']:
        return ''
    v=json.loads((out/'validation.json').read_text());assert v['status']=='PASS'
    esc=html.escape
    buttons=''.join(f'<button type="button" data-time="{(s["start"]-1)/m["fps"]:.3f}"><span>{s["index"]:02d}</span>{esc(s["title"])}</button>' for s in m['stages'])
    caption=f'{m["duration_seconds"]:g} 秒 · {m["fps"]} fps · {m["resolution"][0]}×{m["resolution"][1]} · {m["stage_count"]} 个步骤'
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI 装配动画</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#12181e;color:#e5edf3;font:16px/1.75 system-ui,sans-serif}}main{{max-width:1220px;margin:auto;padding:28px}}h1{{margin:0;font-size:32px}}p{{color:#b4c4cf}}a{{color:#88dde5}}video{{width:100%;display:block;border-radius:12px;background:#313b43}}.links{{display:flex;flex-wrap:wrap;gap:20px;margin:18px 0}}.chapters{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px;margin:18px 0}}button{{display:flex;align-items:center;gap:14px;text-align:left;color:#dbe6ed;background:#26323d;border:1px solid #394c59;border-radius:9px;padding:12px;cursor:pointer;font:inherit}}button:hover,button.active{{border-color:#81d6de;background:#2d454e}}button span{{color:#8bdddf}}.note{{padding:16px 20px;background:#25313c;border-radius:10px}}@media(max-width:700px){{main{{padding:16px}}}}</style>
<main><h1>MORI · 装配动画</h1><p>{caption}。由 {esc(m['revision'])} 的实际模型渲染。</p>
<div class="links"><a href="../mori_assembly_animation.blend">打开可编辑动画 .blend</a><a href="MORI_assembly.mp4" download>下载 MP4</a><a href="README.md">Blender 使用与重新生成</a><a href="../index.html?revision={esc(m['revision'])}">返回机械项目</a></div>
<video id="assembly-video" controls playsinline preload="metadata" poster="step_18.png?revision={esc(m['revision'])}"><source src="MORI_assembly.mp4?revision={esc(m['revision'])}" type="video/mp4"></video>
<div class="chapters">{buttons}</div>
<p class="note">在 Blender 中打开动画文件，选择 <b>MORI_Assembly_Animation</b> 场景，按空格播放。时间轴有中文步骤标记，零件保留独立关键帧；原始总装场景也保留，可切回检查尺寸。</p>
<p>动画中的位移用于装配讲解，未做全程路径碰撞、工具或人手验证。上壳附件在独立镜头预装后切换到总装姿态，没有用穿过完整头部的运动冒充可行装配路径。内部橙色仍表示未确认件；实际配合、紧固和装配工艺需样件验证。</p>
<p><a href="validation.json">动画文件与视频检查</a> · <a href="manifest.json">步骤、帧号与来源记录</a> · <a href="../scripts/assembly_animation.py">可重复生成脚本</a></p></main>
<script>const video=document.getElementById('assembly-video');const buttons=[...document.querySelectorAll('[data-time]')];for(const b of buttons)b.addEventListener('click',()=>{{video.currentTime=Number(b.dataset.time);video.play().catch(()=>{{}})}});video.addEventListener('timeupdate',()=>{{let active=buttons[0];for(const b of buttons)if(Number(b.dataset.time)<=video.currentTime)active=b;for(const b of buttons)b.classList.toggle('active',b===active)}});</script></html>'''
    (out/'index.html').write_text(page)
    section=f'''<section id="animation"><h2>Blender 装配动画</h2><p>{caption}。<a href="mori_assembly_animation.blend">打开可编辑动画文件</a> · <a href="animation/index.html">分步骤播放</a> · <a href="animation/README.md">使用说明</a></p><video controls playsinline preload="metadata" poster="animation/step_18.png?revision={esc(m['revision'])}" style="width:100%;border-radius:12px"><source src="animation/MORI_assembly.mp4?revision={esc(m['revision'])}" type="video/mp4"></video><p>实际模型、独立关键帧与中文时间轴标记。装配移动是示意，尚未完成全程路径及手工工艺验证。</p></section>'''
    return section


if __name__=='__main__':generate(Path(__file__).resolve().parents[1])
