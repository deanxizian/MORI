"""Rasterize actual planar CAD sections for a pending user decision."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;q=json.loads((H/'pitch_seat_thickness_candidate.json').read_text())
im=Image.new('RGB',(1360,630),'#f2f5f4');d=ImageDraw.Draw(im)
font='/System/Library/Fonts/STHeiti Medium.ttc'
f=lambda n:ImageFont.truetype(font,n)
d.text((40,24),'第2项补充修正 · 上侧俯仰舵机螺母座',font=f(30),fill='#243b42')
d.text((40,68),'相同孔轴、螺母与螺钉；不新增零件。右侧为待确认候选。',font=f(21),fill='#465c62')
z=230.5500030517578;s=37
for i,(key,title) in enumerate([('current','当前：槽上下仍有薄片'),('candidate','候选：上缘加厚，下方开放')]):
 ox=50+i*665;oy=137
 d.rounded_rectangle((ox-10,oy-12,ox+615,oy+370),radius=10,fill='white',outline='#c7d4d4',width=2)
 d.text((ox+12,oy+3),title,font=f(24),fill='#243b42')
 tr=lambda p:(ox+300+p[0]*s,oy+285-(p[1]-z)*s)
 for poly in q['sections'][key]:
  pts=[tr(p) for p in poly];d.polygon(pts,fill='#83a4ac');d.line(pts+[pts[0]],fill='#2d505b',width=2)
 if key=='current':
  for dz,text,ty in [(2.8,'上方约0.5 mm',70),(-2.2,'下方局部约0.2 mm',327)]:
   x,y=tr((0,dz+z));d.line((ox+480,oy+ty+12,x,y),fill='#c94e43',width=3);d.ellipse((x-4,y-4,x+4,y+4),fill='#c94e43');d.text((ox+358,oy+ty),text,font=f(18),fill='#a43129')
 else:
  x,y=tr((0,z+2.7));d.line((ox+480,oy+82,x,y),fill='#27805c',width=3);d.text((ox+344,oy+60),'顶壁1.2 mm',font=f(20),fill='#21684d')
  x,y=tr((0,z-2.9));d.line((ox+485,oy+333,x,y),fill='#27805c',width=3);d.text((ox+324,oy+317),'去掉薄底边',font=f(20),fill='#21684d')
d.text((40,542),'剖面 X=-33.8 mm；蓝灰为打印材料，白色为开口。上缘增加0.7 mm，保留螺钉前侧承压壁。',font=f(20),fill='#465c62')
d.text((40,580),'候选检查：130个头部姿态、螺母侧向装入与止转通过；仅候选，主模型未采用。',font=f(20),fill='#465c62')
im.save(H/'pitch_seat_candidate.png')
print(q['rotation_stops_deg'])
