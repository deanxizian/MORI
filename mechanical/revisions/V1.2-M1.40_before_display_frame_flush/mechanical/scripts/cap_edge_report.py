"""Publish the current local cap edit using actual same-camera renders."""
import json,hashlib,html
from pathlib import Path

def generate(root,rev,current_report):
 root=Path(root);study=root/'studies/drive_edge_review'
 r=json.loads((root/'reports/cap_edge_cleanup_validation.json').read_text());assert r['status']=='PASS'
 m=json.loads((study/'after_render_manifest.json').read_text())
 assert m['source_blend_sha256']==hashlib.sha256((root/'mori_v1_2.blend').read_bytes()).hexdigest()
 for name,v in m['views'].items():assert hashlib.sha256((study/v['file']).read_bytes()).hexdigest()==v['sha256']
 description='仅收齐圈出的右侧底盖窄边，去除约1.5×18×2.3mm外露台阶。轴承承托面、底盖以内连接根部、左侧及全部五金/器件保持；没有新增打印件、孔或紧固件。'
 evidence=f'实际实体比较仅Motor_Retainer发生变化；新增材料{r["added_volume_mm3"]:.2g}mm³，批准范围以外的改变{r["change_outside_approved_region_mm3"]:.2g}mm³，去除约{r["removed_volume_mm3"]:.1f}mm³。底盖仍为一个闭合连续实体；轴承座邻域保持。强度、蠕变与实物配合未验证。'
 def gallery(prefix=''):
  return '<div class="grid">'+''.join(f'<figure><a href="{prefix}{name}.png"><img loading="lazy" src="{prefix}{name}.png?revision={rev}" alt="{title}"></a><figcaption>{title}</figcaption></figure>' for name,title in [('before_cap_close','修改前：外露窄边'),('after_cap_close','修改后：过渡与底盖外沿对齐'),('before_underside','修改前：轮驱底面'),('after_underside','修改后：同一视角')])+'</div>'
 section=f'<section id="cap-edge"><h2>本轮：底盖右侧外沿收齐</h2><p>{description}</p>{gallery("studies/drive_edge_review/")}<p>{evidence}</p><p><a href="studies/drive_edge_review/index.html">局部对照</a> · <a href="exports/stl/Motor_Retainer.stl">更新后的候选底盖STL</a> · <a href="reports/cap_edge_cleanup_validation.json">修改范围检查</a></p></section>'
 page=(root/'index.html').read_text()
 page=page.replace('<h1>CAM 与电池补齐固定，<br>相机由现有零件限位。</h1>','<h1>底盖右侧窄凸边已收齐。</h1>')
 page=page.replace('<a href="#completion">本轮固定</a>','<a href="#cap-edge">本轮外沿</a><a href="#completion">相机与电池固定</a>')
 page=page.replace('<section id="completion">',section+'<section id="completion">',1)
 (root/'index.html').write_text(page)
 style='<style>body{max-width:1120px;margin:30px auto;padding:0 24px 50px;background:#edf0ed;color:#20312c;font:16px/1.7 system-ui,sans-serif}a{color:#17694f}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border-radius:10px;overflow:hidden}img{width:100%;display:block}figcaption{padding:12px}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>'
 (study/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} 底盖外沿</title>{style}<a href="../../index.html?revision={rev}#cap-edge">当前总装</a><h1>{rev} · 底盖右侧外沿收齐</h1><p>{description}</p>{gallery()}<p>{evidence}</p><p>渲染仅切换可见性与审查材质，使用相同相机，未为展示缩放或变形零件。</p><p><a href="../../mori_v1_2.blend">当前Blender</a> · <a href="../../exports/stl/Motor_Retainer.stl">候选STL</a> · <a href="../../reports/cap_edge_cleanup_validation.json">检查记录</a></p></html>')
 current=(root/'reports'/current_report).read_text()
 current=f'# MORI {rev} · 底盖外沿整理\n\n{description}\n\n{evidence}\n\n此前CAM、电池、相机候选结构与全部硬件几何保持。本轮运行build.py、重复生成检查、validate.py、render.py、export.py及装配动画重建/视频回读；明细见commands.json、animation/commands.json和cap_edge_cleanup_validation.json。\n\n下面保留当前整机装配状态与未完成项。\n\n'+current
 (root/'reports'/current_report).write_text(current);(root/'reports/REPORT.md').write_text(current)
 progress=root/'reports/assembly_completion_progress.json';q=json.loads(progress.read_text())
 q['rows'].insert(0,{'item':'圈出右侧底盖窄边','status':'已收齐；几何检查通过','detail':description})
 q['completed_nominal_items'].insert(0,'Right cap-edge local cleanup');progress.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
