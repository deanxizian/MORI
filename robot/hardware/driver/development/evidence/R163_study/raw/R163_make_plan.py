"""Explicit grouped UV/OV resistor reassignment from canonical R159H.

No schematic/net/value changes. This first native trial still requires the OV
trunk and all old logic links to be restored; prohibited from adoption.
"""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
fs={f.GetReference():f for f in c.footprints}
p=copy.deepcopy(json.loads((b/'R162D-plan.json').read_text()))
p.update(revision='R163A',scope=__doc__)
rows=json.loads((b/'R163-divider-assignment.json').read_text())['placements']
for row in rows:
 ref=row['reference'];f=fs[ref];old=list(xy(f.GetPosition()))
 spec={'reference':ref,'from_mm':old,'delta_mm':[round(x-y,6) for x,y in zip(row['position_mm'],old)],'rotation_deg':row['rotation_deg']}
 face=c.board.GetLayerName(f.GetLayer())
 if face!=row['face']:
  spec['side_change']={'from_face':face,'to_face':row['face'],'from_rotation_deg':f.GetOrientationDegrees(),'axis':'LEFT_RIGHT',
                       'reason':'Group the existing divider chain without changing values, pin numbers or nets; exact mirror and guard-face accounting required.'}
 p['translations']=[s for s in p['translations'] if s['reference']!=ref]+[spec]
def net(ref,pad):return next(q.GetNetname() for q in fs[ref].Pads() if q.GetNumber()==str(pad))
miduv=net('R1301',1);mid1=net('R1501',1);mid2=net('R1502',1);uv=net('R1302',1);ov=net('U1501',4);cam=net('R716',2)
delete=set(p['delete_copper'])
ov_keep={'b2374b06-9a90-49c0-b437-a173eff3f557','6941700c-59b2-4d55-a46b-f868f8ad8a3a','d29c1947-4ee9-4231-a599-049e3997a4a2'}
for t in c.segments:
 if t.GetNetname() in {miduv,mid1,mid2,uv} or (t.GetNetname()==ov and uid(t) not in ov_keep):delete.add(uid(t))
delete.update(['14c8ba3a-d3e1-4a98-90bd-fbe3763c6b78','4d1aa9cc-89f2-4384-92b8-e403c66b4b07','fd6ef1bf-978b-4d48-8630-a6df835c32b5'])
p['delete_copper']=sorted(delete)
p['deleted_copper_expected']={id_:{'net':c.by_id[id_].GetNetname(),'layer':c.board.GetLayerName(c.by_id[id_].GetLayer()),'width_mm':c.by_id[id_].GetWidth()/1e6,
 'start_mm':list(xy(c.by_id[id_].GetStart())),'end_mm':list(xy(c.by_id[id_].GetEnd()))} for id_ in sorted(delete)}
# Explicitly repurpose three non-ground holes and retire only fully disconnected
# old transfers. Original GND vias are never eligible.
reassign={
 '7bd5c3f2-f767-42af-b113-c3a4bc91e615':(uv,[65,29.95]),
 'ed145f08-9ec4-48e7-acaf-aabdac5dea88':(miduv,[64.45,31.275]),
 'fe2d0371-b479-48d2-a727-17898dd668f7':(miduv,[67.65,25.15]),
 'b7a4befe-1ae6-40bc-a958-e0a34a8c803c':(cam,[62.75,25.25]),
}
retire={'fcd6ec6b-0145-4092-9c84-0765c014a1fa','f1a3f676-9cff-4b2d-a066-ac57c6f6faf7','676bedc1-b01d-490a-a877-cb96a52f3d90'}
p['move_vias']=[s for s in p['move_vias'] if s['uuid'] not in set(reassign)|retire]
p['reassign_vias']=[{'uuid':id_,'source_expected':via_snapshot(c.board,c.by_id[id_]),'net':n,'position_mm':pos,
 'reason':'Explicit non-ground transfer reassignment for grouped dividers; source bytes and all former functions must be independently checked.'} for id_,(n,pos) in reassign.items()]
for id_ in sorted(retire):
 v=c.by_id[id_];contacts=via_contact_layers(c.board,v,delete)
 assert len(contacts)<=1 and v.GetNetname()!='GND'
 p['remove_obsolete_vias'].append({'uuid':id_,'source_expected':via_snapshot(c.board,v),'remaining_contact_layers':contacts,
 'reason':'All old branches at this non-ground transfer are explicitly replaced by the grouped divider proposal. No restoration or adoption inferred.'})
routes=p['routes'];p['routes']=[r for i,r in enumerate(routes) if i not in {6,9,10,11,12,13,14,15,16,17}]
def route(n,layer,pts,w=.2):p['routes'].append({'net':n,'layer':layer,'width_mm':w,'points_mm':pts})
route(mid1,'B.Cu',[[57.5,30.075],[57.5,31.675]])
route(mid2,'B.Cu',[[57.5,33.325],[57.5,33.8],[59.5,33.8],[59.5,33.575]])
route(ov,'B.Cu',[[59.5,31.925],[59.5,31.5],[60.425,30.575]])
route(miduv,'B.Cu',[[63.325,33.5],[63.7,33.5],[64.45,32.75],[64.45,31.275]])
route(miduv,'In3.Cu',[[64.45,31.275],[64.1,31.4],[63.4,31.4],[63.4,28.35],[66.65,28.35],[66.65,27.15],[67.65,26.15],[67.65,25.15]])
route(miduv,'F.Cu',[[67.65,25.15],[67.65,26.5],[67.95,26.8],[68.4,26.8],[68.9,27.3],[68.9,27.675]])
route(uv,'F.Cu',[[68.9,29.325],[68.3,29.175],[66.6,29.175],[66.35,29.025],[65.05,29.025],[65,29.95]])
route(uv,'F.Cu',[[65.65,28.275],[65.65,29.025]])
route(uv,'B.Cu',[[63.4,26.525],[63.4,26.95],[64.0625,26.95]])
route(uv,'B.Cu',[[62.9,31.975],[63.6,31.975],[64.2,31.375],[64.2,30.6]])
route(uv,'F.Cu',[[64.2,30.6],[65,30.6],[65,29.95]])
for s in p['vias']:
 if s['net']==mid2 and s['position_mm']==[64.2,30.6]:s['net']=uv
route(cam,'B.Cu',[[61.575,25.25],[62.75,25.25]],.5)
route(cam,'In2.Cu',[[62.75,25.25],[62.75,26.75],[62.2,27.3],[60,27.3]],.5)
route('GND','B.Cu',[[60.425,28.925],[61.2,28.925],[61.45,29.175],[61.45,29.5]],.3)
route('GND','B.Cu',[[62.9,30.325],[62.9,29.5],[62.35,28.95],[62,28.95]],.3)
p['unfinished_connections']=['OV divider to U1501','HEAD_UV_N original output','HEAD_UV_ENABLE original bias','all canonical remaining nets']
out=b/'R163A-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'plan':str(out),'translations':len(p['translations']),'routes':len(p['routes']),'deleted':len(delete),'reassign':len(reassign)}))
