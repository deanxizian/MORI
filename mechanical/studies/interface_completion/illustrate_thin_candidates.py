"""Exact sections and local wall probes; never modifies the main assembly."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from export import topology
bpy.ops.wm.open_mainfile(filepath=str(HERE/'thin_mount_candidates.blend'))
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
current={n:Solid(bpy.data.objects[PREFIX+n]) for n in ['Display_Frame','Pitch_Yoke','Head_Pitch_Ear_0_Nut']}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'mori_v1_2.blend'))
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
old={n:Solid(bpy.data.objects[PREFIX+n]).m for n in ['Display_Frame','Pitch_Yoke']}
checks=[]
for n in ['Display_Frame','Pitch_Yoke']:
 s=current[n];checks.append({'id':n,'topology':topology(s.v,s.f),'positive_components':sum(x.volume()>.001 for x in s.m.decompose())})
base=old['Display_Frame'];p=np.array([-2.1,27.5375067,259.8]);h=base.ray_cast((p+[0,0,.0001]).tolist(),(p+[0,0,20]).tolist())[0]
q=np.array(h.position);normal=np.array(h.normal);start=q-normal*.0001
camray=current['Display_Frame'].m.ray_cast(start.tolist(),(start-normal*100).tolist())[0]
pitchray=current['Pitch_Yoke'].m.ray_cast([-40,0,228.2501],[-40,0,260])[0]
probes={'camera_floor_normal_ray_mm':camray.distance*100+.0001,'pitch_bearing_upper_wall_mm':pitchray.distance*(260-228.2501)+.0001,'checks':checks,'limits':'Local probes at identified old thin spots; not a global minimum-wall or strength certification.'}
(HERE/'thin_candidate_wall_checks.json').write_text(json.dumps(probes,indent=2))
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="960" viewBox="0 0 1280 960"><rect width="1280" height="960" fill="#f7f8fa"/><g font-family="PingFang SC,Arial,sans-serif" fill="#263c46">']
spec=[('Display_Frame',0,27.54,(-9,252,9,270),'1 · 相机座：填平废弃孔腔'),('Pitch_Yoke',1,-40,(-9,222,9,237),'2 · 俯仰螺母座：消除轴承孔上方薄壁')]
section_records=[]
for row,(name,mode,coord,bb,title) in enumerate(spec):
 for col,(label,m) in enumerate([('当前主模型 M1.42',old[name]),('修复候选 · 尚未应用',current[name].m)]):
  x0,z0,x1,z1=bb;ox=45+col*640;oy=70+row*450;scale=min(490/(x1-x0),330/(z1-z0));paths=[]
  if mode==0:poly=[[(x,-z) for x,z in poly] for poly in m.rotate([90,0,0]).slice(coord).to_polygons()]
  else:poly=[[(-y,z) for y,z in poly] for poly in m.rotate([0,90,90]).slice(-coord).to_polygons()]
  # Both coordinate mappings above reflect one axis. Reverse every contour
  # to preserve outer/hole winding before the positive-fill intersection.
  sec=manifold.CrossSection([list(reversed(p)) for p in poly])^manifold.CrossSection.square([x1-x0,z1-z0]).translate([x0,z0])
  assert sec.area()>1,(name,label,'Empty section')
  section_records.append({'part':name,'label':label,'section_area_mm2':sec.area()})
  for p in sec.to_polygons():paths.append('M '+' L '.join(f'{ox+(x-x0)*scale:.3f},{oy+(z1-z)*scale:.3f}' for x,z in p)+' Z')
  svg.append(f'<text x="{ox}" y="{oy-34}" font-size="21">{title}</text><text x="{ox}" y="{oy-12}" font-size="16">{label}</text><path d="{" ".join(paths)}" fill="#73969f" stroke="#294553" stroke-width="1" fill-rule="evenodd"/>')
  ylo,yhi,zlo,zhi=(-6.31,6.31,257.35,260.25) if row==0 else (-2.8,2.8,228.15,233)
  svg.append(f'<rect x="{ox+(ylo-x0)*scale}" y="{oy+(z1-zhi)*scale}" width="{(yhi-ylo)*scale}" height="{(zhi-zlo)*scale}" fill="none" stroke="#c74f40" stroke-width="2" stroke-dasharray="6 4"/>')
  caption=('Y=27.54 mm 剖面；镜头、外轮廓和光学平面不动。' if row==0 else '原螺母处 X=-40 mm 剖面；舵机和轴承孔不动。')
  svg.append(f'<text x="{ox}" y="{oy+365}" font-size="16">{caption}</text>')
svg.append('<text x="45" y="930" font-size="17">第2项候选：螺母移至 X=-33.8 mm 的现有耳座，配 M2×8 和短侧入口；不增加零件。</text>')
svg.append('</g></svg>');(HERE/'thin_mount_comparison.svg').write_text(''.join(svg))
(HERE/'thin_illustration_checks.json').write_text(json.dumps({'status':'PASS','nonempty_sections':section_records,'geometry_modified':False},ensure_ascii=False,indent=2))
print('THIN_WALL_PROBES',probes,flush=True)
