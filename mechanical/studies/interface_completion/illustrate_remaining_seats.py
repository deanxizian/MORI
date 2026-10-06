"""Physical sections of two unadopted remaining seat corrections."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
def readfile(path,ids):
 bpy.ops.wm.open_mainfile(filepath=str(path));load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
 return {n:Solid(bpy.data.objects[PREFIX+n]).m for n in ids}
ids=['Drive_Bridge','Motor_Retainer','Wheel_Axle_R','Wheel_Bearing_R_Inner','Wheel_Bearing_R_Outer','Wheel_Spacer_R_0','Pitch_Yoke','Head_Yaw_Ear_0_Nut']
old=readfile(ROOT/'mori_v1_2.blend',ids);bearing=readfile(HERE/'bearing_lip_candidate.blend',ids);yaw=readfile(HERE/'yaw_nut_open_candidate.blend',ids)
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1280" viewBox="0 0 1280 1280"><rect width="1280" height="1280" fill="#f7f9fa"/><g font-family="PingFang SC,Arial,sans-serif" fill="#263c46"><text x="40" y="45" font-size="28">两处剩余固定座候选</text><text x="40" y="78" font-size="17">尚未应用；不增加打印件或五金数量。下图由实际实体切片生成。</text>']
def section_path(cs,origin,scale,lo,hi):
 cs=cs^(manifold.CrossSection.square((np.array(hi)-lo).tolist()).translate(lo))
 return ' '.join('M '+' L '.join(f'{origin[0]+(x-lo[0])*scale:.2f},{origin[1]+(hi[1]-y)*scale:.2f}' for x,y in p)+' Z' for p in cs.to_polygons())
rot=np.array([[1,0,0],[0,0,1],[0,-1,0]])
for col,(label,solids,lip) in enumerate([('当前挡边 0.75 mm',old,.75),('候选挡边 1.25 mm',bearing,1.25)]):
 ox=45+col*640;oy=165;scale=15;lo=[25,39];hi=[54,67]
 svg.append(f'<text x="{ox}" y="132" font-size="22">{label}</text>')
 for n,color in [('Drive_Bridge','#7a9ba3'),('Motor_Retainer','#aac1c7'),('Wheel_Axle_R','#657580'),('Wheel_Bearing_R_Inner','#d9b46a'),('Wheel_Bearing_R_Outer','#d9b46a'),('Wheel_Spacer_R_0','#aeb8bf')]:
  sec=solids[n].transform(np.c_[rot,[0,0,0]]).slice(0)
  svg.append(f'<path d="{section_path(sec,(ox,oy),scale,lo,hi)}" fill="{color}" stroke="#354852" stroke-width="1" fill-rule="evenodd"/>')
 x0=ox+(34.6-lo[0])*scale;x1=x0+lip*scale;y=oy+(hi[1]-58.2)*scale
 svg.append(f'<rect x="{x0}" y="{y}" width="{x1-x0}" height="{1.3*scale}" fill="none" stroke="#c45244" stroke-width="3"/>')
 svg.append(f'<text x="{ox}" y="615" font-size="17">'+('轴承中心 X=38；短隔套 5 mm' if col==0 else '内侧轴承外移 0.5；短隔套 4.5 mm')+'</text>')
svg.append('<text x="40" y="651" font-size="16">金色为原尺寸轴承。电机、外侧轴承与轮毂不动；金属轴肩同步延长 0.5 mm。</text><line x1="40" y1="681" x2="1240" y2="681" stroke="#cbd6db"/>')
for col,(label,solids) in enumerate([('当前：螺母槽前侧仅约 0.19 mm',old),('候选：开放短槽，去掉薄片',yaw)]):
 ox=60+col*640;oy=772;lo=[-5.5,-13.2];hi=[5.5,-5.5];scale=38
 svg.append(f'<text x="{ox}" y="727" font-size="21">{label}</text><text x="{ox}" y="752" font-size="15">水平切片 Z=198.5 mm，螺母位置保持</text>')
 for n,color in [('Pitch_Yoke','#80a3aa'),('Head_Yaw_Ear_0_Nut','#d9b46a')]:
  svg.append(f'<path d="{section_path(solids[n].slice(198.5),(ox,oy),scale,lo,hi)}" fill="{color}" stroke="#354852" stroke-width="1.2" fill-rule="evenodd"/>')
svg.append('<text x="40" y="1115" font-size="17">螺母仍压在原承压面，顶部保留约 2.6 mm；先放螺母，再装 yaw 舵机。</text><text x="40" y="1150" font-size="17">候选静态检查、螺母装入/止转、轮驱旋转与拆卸检查通过；舵盘资料依然待确认。</text><text x="40" y="1200" font-size="16">这些是名义几何候选，未证明 PA12 强度、紧固力或加工配合。</text></g></svg>')
(HERE/'remaining_seats_comparison.svg').write_text(''.join(svg));print('SEAT_ILLUSTRATIONS',flush=True)
