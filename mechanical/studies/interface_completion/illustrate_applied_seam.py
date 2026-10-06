"""Compare the adopted main seam solid with its immutable M1.41 baseline."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
def read(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
 return Solid(bpy.data.objects[PREFIX+'Head_Front']).m
before=read(ROOT/'revisions/V1.2-M1.41_before_interface_completion/mechanical/mori_v1_2.blend')
after=read(ROOT/'mori_v1_2.blend')
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="780" viewBox="0 0 1200 780"><rect width="1200" height="780" fill="#f4f6f8"/><g font-family="PingFang SC,Arial,sans-serif" fill="#263c46"><text x="40" y="46" font-size="28">头壳拼缝孔：已应用的配对移位</text><text x="40" y="80" font-size="17">实际实体剖面 Y=2.15 mm；前壳嵌件与后壳螺钉/孔轴一起移动。</text>']
for j,(label,m,x,z) in enumerate([('修改前 M1.41',before,43,259),('当前主模型 M1.42',after,41,261)]):
 ox=55+j*590;oy=158;scale=17
 sec=m.rotate([90,0,0]).slice(2.15)^(manifold.CrossSection.square([26,30]).translate([31,-275]))
 paths=['M '+' L '.join(f'{ox+(xx-31)*scale:.3f},{oy+(zz+275)*scale:.3f}' for xx,zz in p)+' Z' for p in sec.to_polygons()]
 svg.append(f'<text x="{ox}" y="130" font-size="23">{label}</text><path d="{" ".join(paths)}" fill="#80a3aa" fill-rule="evenodd" stroke="#304753" stroke-width="1"/><circle cx="{ox+(x-31)*scale}" cy="{oy+(275-z)*scale}" r="4" fill="#c24a3d"/><text x="{ox}" y="700" font-size="19">孔轴 X={x} / Z={z} mm</text>')
svg.append('<text x="40" y="748" font-size="18">两侧各内移2 mm、上移2 mm；最小采样孔壁约1.66 mm。没有新增零件。</text></g></svg>')
(HERE/'seam_applied_comparison.svg').write_text(''.join(svg))
print('APPLIED_SEAM_ILLUSTRATION',hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),flush=True)
