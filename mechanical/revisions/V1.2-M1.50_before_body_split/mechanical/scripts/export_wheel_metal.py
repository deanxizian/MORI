"""Analytic STEP design references for the CUSTOM wheel metalwork (OCP 7.8).
Not a purchased-part model, machining release or replacement geometry source.
"""
from pathlib import Path
import shutil
import json,math,hashlib
from OCP.gp import gp_Pnt,gp_Dir,gp_Ax2
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse,BRepAlgoAPI_Cut,BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs,STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

ROOT=Path(__file__).resolve().parents[1];P=json.loads((ROOT.parent/'config/geometry.json').read_text());w=P['wheel_interface']
OUT=ROOT/'metal_design';OUT.mkdir(exist_ok=True)
def cyl(r,z0,z1,x=0,y=0):return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z0),gp_Dir(0,0,1)),r,z1-z0).Shape()
def fuse(a,b):return BRepAlgoAPI_Fuse(a,b).Shape()
def cut(a,b):return BRepAlgoAPI_Cut(a,b).Shape()
def metrics(shape):
 g=GProp_GProps();BRepGProp.VolumeProperties_s(shape,g)
 bb=Bnd_Box();BRepBndLib.AddOptimal_s(shape,bb,False,False);v=bb.Get()
 return {'volume_mm3':g.Mass(),'bounds_mm':list(v),'size_mm':[v[i+3]-v[i] for i in range(3)],'valid_BRep':BRepCheck_Analyzer(shape).IsValid()}
origin=w['output_face_abs_x_mm'];fl=w['flange_thickness_mm'];sh=w['shoulder_end_abs_x_mm']-origin;key=w['hub_key_start_abs_x_mm']-origin;end=w['shaft_end_abs_x_mm']-origin
shaft=fuse(cyl(w['flange_od_mm']/2,0,fl),cyl(w['shoulder_diameter_mm']/2,fl-.1,sh))
shaft=fuse(shaft,cyl(w['shaft_journal_diameter_model_mm']/2,sh-.1,key))
k=cyl(w['shaft_journal_diameter_model_mm']/2,key-.1,end)
af=w['shaft_key_across_flats_mm'];k=BRepAlgoAPI_Common(k,BRepPrimAPI_MakeBox(gp_Pnt(-af/2,-4,key-.2),af,8,end-key+.4).Shape()).Shape();shaft=fuse(shaft,k)
shaft=cut(shaft,cyl(w['factory_screw_recess_diameter_mm']/2,-.05,w['factory_screw_recess_depth_mm']))
shaft=cut(shaft,cyl(1.525,end-9.5,end+.1))
for angle in w['output_hole_angles_deg']:
 x=w['output_hole_pcd_mm']/2*math.cos(math.radians(angle));y=w['output_hole_pcd_mm']/2*math.sin(math.radians(angle))
 shaft=cut(shaft,cyl(w['flange_hole_clearance_mm']/2,-.1,fl+.1,x,y));shaft=cut(shaft,cyl(w['shoulder_tool_relief_diameter_mm']/2,fl,sh+.1,x,y))
shapes=[('Wheel_Axle_Common_DESIGN_REFERENCE',shaft,2)]
spacer_lengths=[b-a for a,b in w['spacer_spans_abs_x_mm']]
if 5 not in spacer_lengths:
 old=OUT/'Wheel_Spacer_5mm_DESIGN_REFERENCE.step'
 if old.exists():
  history=OUT/'history/V1.2-M1.42';history.mkdir(parents=True,exist_ok=True)
  if not (history/old.name).exists():shutil.copy2(old,history/old.name)
  old.unlink()
for length in spacer_lengths:shapes.append((f'Wheel_Spacer_{length:g}mm_DESIGN_REFERENCE',cut(cyl(4,0,length),cyl(3.05,-.1,length+.1)),2))
Interface_Static.SetCVal_s('write.step.unit','MM')
rows=[]
for name,shape,quantity in shapes:
 m=metrics(shape);assert m['valid_BRep'],name
 file=OUT/(name+'.step');writer=STEPControl_Writer();writer.Transfer(shape,STEPControl_AsIs);assert writer.Write(str(file))==IFSelect_RetDone
 reader=STEPControl_Reader();assert reader.ReadFile(str(file))==IFSelect_RetDone;reader.TransferRoots();reimport=metrics(reader.OneShape());assert max(abs(a-b) for a,b in zip(reimport['size_mm'],m['size_mm']))<.001
 m['STEP_reimport_size_mm']=reimport['size_mm'];m['STEP_reimport_valid_BRep']=reimport['valid_BRep']
 rows.append({'id':name,'quantity':quantity,'file':str(file.relative_to(ROOT)),**m,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
assert abs(rows[0]['size_mm'][2]-end)<.001
data={'revision':P['revision'],'units':'mm','frame':'part-local +Z from S288 flange mating face toward wheel; localX -> assemblyY, localY -> assemblyZ; common design used twice, opposite assembly X directions','source_geometry_sha256':hashlib.sha256((ROOT.parent/'config/geometry.json').read_bytes()).hexdigest(),'parts':rows,'manufacturing_release':False,'limitations':['Custom metal design, not supplier stock or purchase authorization','M3 thread represented by3.05mm major-clearance cylinder ONLY: machining callout is M3x0.5 tapped, NOT a3.05 drilled hole','Journal fits/coaxiality, actual output screw profile, factory central head and bearing inner-ring shoulder need measured samples before machining release','Analytic BRep regenerated from shared configuration; Blender mesh is separately generated and checked']}
(ROOT/'reports/wheel_metal_export.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print('WHEEL_METAL_STEP_EXPORTED',[(r['id'],r['size_mm']) for r in rows])
# A dimensioned vector drawing from the SAME shared parameters (not a render).
# Thread and tolerance callouts govern manufacturing review; STEP is reference.
scale=16;ox=105;cy=230
X=lambda mm:ox+mm*scale
Y=lambda mm:cy-mm*scale
points=[(0,-7),(0,7),(fl,7),(fl,4),(sh,4),(sh,2.99),(key,2.99),(key,2.4),(end,2.4),(end,-2.4),(key,-2.4),(key,-2.99),(sh,-2.99),(sh,-4),(fl,-4),(fl,-7)]
outline=' '.join(f'{X(x):.2f},{Y(y):.2f}' for x,y in points)
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="900" viewBox="0 0 1400 900"><defs><marker id="a" orient="auto-start-reverse" markerWidth="6" markerHeight="6" refX="3" refY="3"><path d="M0,0L6,3L0,6" fill="none" stroke="#173b50"/></marker></defs><rect width="1400" height="900" fill="white"/><g font-family="Arial,sans-serif" fill="#173b50"><text x="60" y="54" font-size="28">MORI '+P['revision']+' / CUSTOM WHEEL SHAFT / 2 IDENTICAL PIECES</text><text x="60" y="87" font-size="18">DESIGN REFERENCE - mm - NO MACHINING RELEASE - matching STEP has analytic surfaces</text><polygon points="'+outline+'" fill="#d6e5eb" stroke="#173b50" stroke-width="2"/><path d="M65,230H900" stroke="#537384" stroke-dasharray="12 6"/>']
def dim(a,b,y,label):
 svg.append(f'<path d="M{X(a)},{y-8}V{y+8} M{X(b)},{y-8}V{y+8} M{X(a)},{y}H{X(b)}" stroke="#173b50" fill="none" marker-start="url(#a)" marker-end="url(#a)"/><text x="{(X(a)+X(b))/2}" y="{y-11}" text-anchor="middle" font-size="17">{label}</text>')
stack=2*w['bearing_width_mm']+spacer_lengths[0]
dim(0,end,400,f'{end:g} total');dim(0,fl,360,f'{fl:g}');dim(sh,sh+stack,340,f'{stack:g} bearing stack');dim(key,end,340,'12.2 double-D')
svg.append('<text x="370" y="152" font-size="18">JOURNAL MODEL DIA 5.98 / NOMINAL 6mm CLASS</text><text x="657" y="181" font-size="17">AF 4.8</text>')
fcx=1120;fcy=235;fs=13
svg.append(f'<circle cx="{fcx}" cy="{fcy}" r="{7*fs}" fill="#d6e5eb" stroke="#173b50" stroke-width="2"/><circle cx="{fcx}" cy="{fcy}" r="{5.25*fs}" fill="none" stroke="#537384" stroke-dasharray="5 4"/><circle cx="{fcx}" cy="{fcy}" r="{3*fs}" fill="white" stroke="#173b50"/>')
for a in w['output_hole_angles_deg']:
 x=fcx+5.25*fs*math.cos(math.radians(a));y=fcy+5.25*fs*math.sin(math.radians(a));svg.append(f'<circle cx="{x}" cy="{y}" r="{1.1*fs}" fill="white" stroke="#173b50"/>')
svg.append('<text x="980" y="364" font-size="17">REAR FLANGE FACE / DIA 14</text><text x="980" y="391" font-size="17">6 x DIA 2.2 ON PCD 10.5</text>')
notes=[
'1. One-piece steel flange + shoulder + shaft. Material candidate: C45 / 1045; no purchased material certification.',
'2. Six open DIA 4.2 shoulder scallops allow screw-head insertion and tool access; see STEP for true 3D profile.',
'3. Rear centre relief DIA 6 x 2 deep clears factory screw. Confirm real S288 central head before machining.',
'4. Axial end: M3 x 0.5 blind tapped hole, usable thread at least 9mm; drill depth / tip allowance to be detailed.',
'   CAD uses a DIA 3.05 thread-major CLEARANCE representation: DO NOT machine it as a plain DIA 3.05 hole.',
'5. Journal fits, runout and perpendicularity must be specified against purchased 686ZZ bearings before release.',
'   CAD journal DIA 5.98 is the trial geometry, not a universal tolerance. Inspect 0.15mm housing end clearances.',
f'6. Spacers: metal tube OD8 / ID6.1, L{spacer_lengths[0]:g} and L{spacer_lengths[1]:g}, quantity2 each. Square ends; match stack without bearing preload.',
'7. PA12 double-D coupon first. Check both rotation directions, end-screw locking, creep, alignment and load.',
'8. This drawing omits chamfers/thread helices. Factory plastic flange pull-out, fatigue and impact remain untested.'
]
for i,t in enumerate(notes):svg.append(f'<text x="60" y="{474+i*33}" font-size="17">{t}</text>')
svg.append('</g></svg>');(OUT/'wheel_shaft_drawing.svg').write_text('\n'.join(svg))
