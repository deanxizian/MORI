"""Read-only per-reference review, using circular Fab bodies where present."""
from pathlib import Path
import pcbnew as k
import json, csv, math, hashlib
from collections import Counter
from audit_body_routes_P4 import rect, clip
H=Path(__file__).resolve().parents[1]; O=H/'layout_P4/body_route_review'
xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
pt=lambda p:k.VECTOR2I(k.FromMM(p[0]),k.FromMM(p[1]))
rows=[]; summary={}; source_rules={}
for kind in ['motion','imu','power','rear']:
 name=f'MORI_{kind}_P4';d=H/'kicad'/name;p=d/(name+'.kicad_pcb');b=k.LoadBoard(str(p))
 data=json.loads((O/(name+'.json')).read_text())
 assert data['pcb_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
 fps={f.GetReference():f for f in b.GetFootprints()};tracks={t.m_Uuid.AsString():t for t in b.GetTracks()}
 for q in data['candidates']:
  row=dict(q);f=fps[q['reference']];t=tracks[q['track_uuid']]
  if not q['same_side']:
   reason='铜在器件对面层，但仍位于器件投影下；不能因换层自动放行，须检查可否通过摆位、旋转或改变路线避开。'
   disposition='OPPOSITE_LAYER_REQUIRES_ROUTING_REVIEW'
  elif q['category']=='MEZZANINE':
   reason='U100 是架空的 WeAct 插接模块；载板内部电路处于模块投影内。需结构复核实际底部高度和排母，不能推广为贴片器件穿体豁免。'
   disposition='RAISED_MODULE_ASSEMBLY_REVIEW_REQUIRED'
  elif q['category']=='CONNECTOR':
   assert q['component_has_this_net'],q
   reason='本接插件自身网络，但网络归属不足以证明从最近边界向外引出；必须检查完整路径，短逃线与壳下长距离折返分别裁定。'
   disposition='CONNECTOR_ESCAPE_REQUIRES_PATH_REVIEW'
  else:
   circles=[s for s in f.GraphicalItems() if isinstance(s,k.PCB_SHAPE) and s.GetLayer() in [k.F_Fab,k.B_Fab] and s.GetShape()==k.S_CIRCLE]
   true_hits=0;covered=0
   a,z=q['start_mm'],q['end_mm'];lo,hi=clip(a,z,q['body_rect_mm']);ln=math.dist(a,z);n=max(1,math.ceil(ln*(hi-lo)/.01))
   ps=[p.GetEffectiveShape(f.GetLayer()) for p in f.Pads()]
   if circles:
    c=max(circles,key=lambda s:s.GetRadius());center=xy(c.GetCenter());radius=k.ToMM(c.GetRadius())
    for i in range(n):
     u=lo+(hi-lo)*(i+.5)/n;v=(a[0]+u*(z[0]-a[0]),a[1]+u*(z[1]-a[1]))
     if math.dist(v,center)<radius and not any(s.Collide(pt(v),0) for s in ps):true_hits+=1
    covered=true_hits*ln*(hi-lo)/n
    row['actual_round_body_core_mm']=round(covered,4)
   if circles and covered<.02:
    reason='保守矩形筛查命中圆柱电解的矩形角部；按实际 Fab 圆形复核，线段不进入圆柱实体投影。'
    disposition='RECTANGLE_CORNER_FALSE_POSITIVE'
   elif kind=='imu' and q['reference']=='U1' and q['core_length_estimate_mm']<=.1 and q['component_has_this_net']:
    reason='ICM-42688-P LGA 引脚本身位于封装边缘内部；该线从焊盘向最近封装边界直出，焊盘外壳内长度约0.096mm，属于必要封装逃线。'
    disposition='NAMED_LGA_PAD_ESCAPE'
   elif kind=='power' and q['reference']=='C10' and q['net']=='/W_VM' and q['track_uuid']=='eddf1534-d706-4ea0-bafa-613f2e275416':
    reason='C10 正引脚位于圆柱内部；从(48,20)向左直出到(45.5,20)，焊盘外约1.5mm。保留短、宽的轮母线电容支路，未折回穿越圆柱。'
    disposition='NAMED_RADIAL_CAP_PIN_ESCAPE'
   else:
    reason='未完成逐路径确认，不能自动放行。'
    disposition='UNREVIEWED_SAME_SIDE_BODY_ROUTE'
  row.update(disposition=disposition,reason=reason);rows.append(row)
 summary[kind]=dict(pcb_sha256=data['pcb_sha256'],reviewed_candidates=len(data['candidates']),dispositions=dict(Counter(q['disposition'] for q in rows if q['board']==name)))
 pro=json.loads((d/(name+'.kicad_pro')).read_text())
 source_rules[kind]=dict(drc_exclusions=pro['board']['design_settings'].get('drc_exclusions',[]),inner_layer_signal_tracks=sum(t.GetLayer() not in [k.F_Cu,k.B_Cu] for t in b.GetTracks() if t.Type()!=k.PCB_VIA_T),R13='PASS',R14='FAIL: exact0.499999mm setback not imposed at every bend; no all47-rules PASS claim')
 assert not source_rules[kind]['drc_exclusions'] and source_rules[kind]['inner_layer_signal_tracks']==0

# Rear shell seat review: top parts and every exposed via/PTH tail matter.
b=k.LoadBoard(str(H/'kicad/MORI_rear_P4/MORI_rear_P4.kicad_pcb'))
seats=[[0,0,6.5,14],[17.5,0,24,14]];hits=[]
def overlaps(a,z):return a[0]<z[2] and a[2]>z[0] and a[1]<z[3] and a[3]>z[1]
for f in b.GetFootprints():
 if f.GetReference().startswith('H'):continue
 if not f.IsFlipped() and rect(f) and any(overlaps(rect(f),s) for s in seats):hits.append(['F_body',f.GetReference()])
 for p in f.Pads():
  if not p.IsOnLayer(k.F_Mask):continue
  bb=p.GetBoundingBox();r=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
  if any(overlaps(r,s) for s in seats):hits.append(['exposed_pad',f.GetReference(),p.GetNumber()])
for v in b.GetTracks():
 if v.Type()!=k.PCB_VIA_T:continue
 x,y=xy(v.GetPosition());rr=k.ToMM(v.GetWidth(k.F_Cu))/2
 if any(overlaps([x-rr,y-rr,x+rr,y+rr],s) for s in seats):hits.append(['via',x,y])
review=dict(status='FAIL',scope='Candidate classification only; does not validate shortest topology, route smoothness, component orientation or complete outward pin escape.',summary=summary,source_rules=source_rules,rear_seats=dict(status='FAIL' if hits else 'PASS',checked_seats_xy_mm=seats,hits=hits,limits='Native 2D only; supports/screws/solder/plug/switch linkage and body-shell assembly NOT_TESTED'),acceptance='P4 user routing requirements FAILED. The previous classification was insufficient. Opposite-layer and connector-own-net candidates are not automatically approved.',physical_tests='NOT_TESTED')
(O/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
with (O/'reviewed_routes.csv').open('w',newline='',encoding='utf-8-sig') as f:
 keys=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
print(json.dumps(review,ensure_ascii=False,indent=2))
