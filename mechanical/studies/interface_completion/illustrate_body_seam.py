"""Exact shell sections and the unadopted nominal service path for review."""
import sys,math,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
candidate={n:Solid(bpy.data.objects[PREFIX+n]).m for n in ['Body_Upper','Body_Lower','Load_Frame']}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'mori_v1_2.blend'))
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
current={n:Solid(bpy.data.objects[PREFIX+n]).m for n in candidate}
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="1170" viewBox="0 0 1320 1170"><rect width="1320" height="1170" fill="#f7f9fa"/><g font-family="PingFang SC,Arial,sans-serif" fill="#263c46"><text x="40" y="42" font-size="26">机身拼缝位置与取壳路径候选</text><text x="40" y="73" font-size="16">尚未应用 · 保留四枚螺钉和四个嵌件 · 电路板、外壳母形和分缝高度不变</text>']
def path(polys,ox,oy,scale):
 return ' '.join('M '+' L '.join(f'{ox+x*scale:.2f},{oy-y*scale:.2f}' for x,y in poly)+' Z' for poly in polys)
for col,(label,solids,coords) in enumerate([('当前：X±49 / Y±54',current,[(x,y) for x in [-49,49] for y in [-54,54]]),('候选：X±22 / Y±71',candidate,[(x,y) for x in [-22,22] for y in [-71,71]])]):
 ox=320+col*660;oy=386;sc=3.05
 svg.append(f'<text x="{40+col*660}" y="112" font-size="21">{label}</text>')
 # The deck bounds are explicitly a plan envelope, not a slice or a claim
 # of whole-volume intersection with the body seam at its installed height.
 svg.append(f'<rect x="{ox-52*sc}" y="{oy-50*sc}" width="{104*sc}" height="{114*sc}" fill="#e2e8eb" stroke="#a4b3ba" stroke-dasharray="5 4"/>')
 svg.append(f'<path d="{path(solids["Body_Upper"].slice(103.5).to_polygons(),ox,oy,sc)}" fill="#80a3aa" stroke="#355560" fill-rule="evenodd"/>')
 for x,y in coords:svg.append(f'<circle cx="{ox+x*sc}" cy="{oy-y*sc}" r="11" fill="none" stroke="{"#c96251" if col==0 else "#25806b"}" stroke-width="3"/>')
 svg.append(f'<text x="{ox-31}" y="{oy-244}" font-size="16">前 +Y</text><text x="{40+col*660}" y="659" font-size="15">上壳 Z=103.5 mm 实体切片；灰色虚框为 Load Frame 平面包络</text>')
svg.append('<line x1="35" y1="680" x2="1285" y2="680" stroke="#ccd6db"/><text x="40" y="720" font-size="21">候选拆卸：卸车轮、下壳及头部/固定桥后，喇叭与后接口板随上壳保留</text>')
rot=np.array([[0,1,0],[0,0,1],[1,0,0]])
def section(m):return m.transform(np.c_[rot,[0,0,0]]).slice(22).to_polygons()
origin=Vector((0,0,D['body_z']))
spec=[(0,0,0,'就位'),(15,0,14,'倾斜 15° + 抬高 14 mm'),(15,-14,14,'向后 14 mm，再向上取出')]
for idx,(a,y,z,label) in enumerate(spec):
 ox=205+idx*425;oy=1102;sc=1.95
 tr=Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
 m=candidate['Body_Upper'].transform(np.array(tr)[:3,:])
 svg.append(f'<path d="{path(section(candidate["Load_Frame"]),ox,oy,sc)}" fill="#c7ced2" stroke="#7b8a92" fill-rule="evenodd"/><path d="{path(section(m),ox,oy,sc)}" fill="#80a3aa" stroke="#355560" fill-rule="evenodd"/>')
 svg.append(f'<text x="{40+idx*425}" y="1118" font-size="17">{idx+1}. {label}</text>')
svg.append('<text x="40" y="1155" font-size="15">有限实体路径与工具包络检查通过；试打配合、手持操作及连续轨迹仍待验证。候选不增加打印件。</text></g></svg>')
(HERE/'body_seam_comparison.svg').write_text(''.join(svg))
print('BODY_SEAM_ILLUSTRATION',flush=True)
