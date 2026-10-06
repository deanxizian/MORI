"""Extract actual nominal fastener shapes and screen straight tool cylinders."""
import sys,json,math,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid
ROOT=PROJECT
load_collections();assembled();bpy.context.view_layer.update()
classify=json.loads((ROOT/'mechanical/reports/manufacturing_classification.json').read_text())
ids=set(n for k,v in classify['categories'].items() if k not in ['auxiliary_print'] for n in v)
solids={n:Solid(bpy.data.objects[PREFIX+n]) for n in ids if bpy.data.objects.get(PREFIX+n)}
contacts=json.loads((ROOT/'mechanical/reports/intended_contacts.json').read_text());out=[]
for name in classify['categories']['fasteners']:
 if 'Screw' not in name:continue
 s=solids[name];tri=s.v[s.f];cr=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cr,axis=1)/2;ns=cr/np.maximum(2*ar[:,None],1e-12);groups={}
 for n,a in zip(ns,ar):
  if n[np.argmax(abs(n))]<0:n=-n
  k=tuple(np.round(n,4));groups[k]=groups.get(k,0)+a
 axis=np.array(max(groups,key=groups.get));axis/=np.linalg.norm(axis);center=s.v.mean(0)
 axial=(s.v-center)@axis;rad=np.linalg.norm((s.v-center)-axial[:,None]*axis,axis=1);headrad=rad.max();sel=axial[rad>headrad*.96];headheight=float(sel.max()-sel.min());sign=1 if sel.mean()>(axial.max()+axial.min())/2 else -1
 outward=axis*sign;ht=float(axial.max() if sign>0 else axial.min());face=center+ht*axis;length=float(axial.max()-axial.min()-headheight)
 screwsize=3 if headrad>2.2 else 2;toolrad=1.5;orient=np.column_stack((np.cross(outward,[1,0,0] if abs(outward[0])<.9 else [0,1,0]),[0,0,0],outward));orient[:,0]/=np.linalg.norm(orient[:,0]);orient[:,1]=np.cross(outward,orient[:,0])
 tool=manifold.Manifold.cylinder(30,toolrad,toolrad,48).transform(np.c_[orient,face+outward*.02]);handle=manifold.Manifold.cylinder(25,8,8,48).transform(np.c_[orient,face+outward*30])
 hits=[];handlehits=[]
 for n,t in solids.items():
  if n==name:continue
  for shape,rows in [(tool,hits),(handle,handlehits)]:
   bb=np.array(shape.bounding_box())
   if np.any(bb[3:]<t.lo) or np.any(t.hi<bb[:3]):continue
   vol=max(0,(shape^t.m).volume())
   if vol>.02:rows.append({'part':n,'volume_mm3':round(vol,3)})
 interfaces=[c for c in contacts if name in [c['a'],c['b']]]
 out.append({'id':name,'label':s.o.get('label_zh'),'extracted_axis_outward':outward.tolist(),'tool_start_mm':face.tolist(),'nominal_shank_length_mm':length,'nominal_head_diameter_mm':float(2*headrad),'nominal_head_height_mm':headheight,'tool_assumption':'Straight3mm shaft x30mm plus16mm handle x25mm; not a particular purchased tool','shaft_blockers_in_complete_assembly':hits,'handle_blockers_in_complete_assembly':handlehits,'documented_interfaces':interfaces,'reference_candidate':'GB823 M2 small pan head3.5x1.4max; thread/length fit still to review' if screwsize==2 and not name.startswith('Wheel_Output') else 'Keep specific source/self-tapping or socket specification; do not substitute by head appearance','status':'PASS' if not hits and not handlehits else 'BLOCKED','meaning':'Blockers may be normal assembly prerequisites; this is not proof of impossible assembly. Real driver tip, grip and tool deflection untested.'})
(HERE/'fastener_current.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('FASTENER_ACCESS_REVIEW_COMPLETE',len(out),flush=True)
