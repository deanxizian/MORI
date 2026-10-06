"""Add the physical low-current master-switch interface to isolated power P4.
Run once. Existing reverse-protection Q1 is retained: it cannot turn power off.
No P3R1 PCB or firmware is modified.
"""
from pathlib import Path
import pcbnew as k
import json,copy,uuid,re,shutil,inspect,csv
from functional_schematic import Drawing
import readable_schematic as readable
from readable_schematic import block
from logic5v_S3 import draw_branch
from helpers_P4 import paths
from design_P1 import comp,pin
from body_keepouts_P3R1 import create
from layout_P3R1 import pt
name,d,p,r=paths('power');data=json.loads((d/'connectivity.json').read_text());parts={c['ref']:c for c in data['components']}
if 'Q90' in parts:raise SystemExit('Master stage already exists; do not overwrite routing.')
oldsch=(d/(name+'.kicad_sch')).read_text();root=re.search(r'\(uuid ([^)]+)\)',oldsch).group(1)
new=[]
def clone(ref,source,value,nets,at,side='B'):
 c=copy.deepcopy(parts[source]);c.update(ref=ref,value=value,pins={str(n):pin(str(n),v) for n,v in nets.items()},at=list(at),placed_at=list(at),side=side,auto=False,uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,'mori-v12-P1/'+name+'/'+ref)))
 c.pop('layout_revision',None);new.append(c);return c
c=clone('Q90','Q1','AO4407A',{1:'PACK_FUSED',2:'PACK_FUSED',3:'PACK_FUSED',4:'MASTER_GATE',5:'BAT_IN',6:'BAT_IN',7:'BAT_IN',8:'BAT_IN'},(5,11,0));c['note']='Main load switch source=PACK_FUSED, drain=BAT_IN. Q1 remains reverse protection with common drains. Power OFF requires Q90 off; not a safety-rated isolator.'
c=clone('R90','R1','100k',{1:'PACK_FUSED',2:'MASTER_GATE'},(4.5,16,0));c['note']='Gate-source pull-up defaults master OFF with rear harness open.'
c=clone('R91','R1','10k',{1:'MASTER_GATE',2:'MASTER_RETURN'},(10,25,0));c['note']='Gate return current limited; rear switch carries <1.3mA at12.6V, not actuator current.'
c=clone('D90','D1','BZT52H-C10,115',{1:'PACK_FUSED',2:'MASTER_GATE'},(9,22,90));c['note']='Cathode pin1 to source. Gate clamp; low-current zener tolerance must be checked.'
c=clone('J19','J17','REAR MASTER / 1RETURN 2GND',{1:'MASTER_RETURN',2:'GND'},(11,28,0),'F');c['source']='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf';c['note']='JST B2B-PH-K-S(LF)(SN),C131337; PHR-2/SPH-002T-P0.5S; rear J3.1/2. RETURN may sit at pack voltage while OFF.'
parts['J1']['pins']['2']['net']='PACK_FUSED';parts['J1']['value']='PACK AFTER 6.3A FUSE';parts['J1']['note']='Protected finished3S pack through external6.3A fuse. On-board Q90 is controlled by rear SW1. No direct small-switch load current.'
for c in data['components']:
 if c['ref'].startswith('#'):
  for v in c['pins'].values():
   if v['net']=='BAT_IN':v['net']='PACK_FUSED'
parts['J17']['source']='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf'
data['components']+=new;(d/'connectivity.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
# Recompose the functional schematic while retaining native symbol UUIDs.
x=Drawing(name)
for ref in ['J1','J17','J19']:
 if ref in x.original_properties:x.original_properties[ref]['Datasheet']=next(c for c in data['components'] if c['ref']==ref).get('source','')
src=inspect.getsource(readable.power).replace("b.place('J1',12,25,orient='r');",'').replace("b.join(('J1',2),('Q1',5));", "b.mark('Q1',5);")
src=src.replace('External pack, fuse and master switch precede J1.','Q90 master stage precedes BAT_IN.').replace('MORI / POWER CONDITIONER / S2','MORI / POWER CONDITIONER / P4')
ns=dict(readable.__dict__);exec(src,ns);ns['power'](x)
draw_branch(x,60,'M5','+5V_MOTION','J17',6,5,'11  Motion 5 V / independent fused buck')
draw_branch(x,70,'C5','+5V_CAM','J18',7,166,'12  Interaction 5 V / independent fused buck')
x.paper=(841,1220)
b=block(x,'13  Physical master power / low-current rear switch',5,391,318,77,'OFF opens Q90 and the separate motion latch loop. No automatic ARM. Existing Q1 retains reverse-polarity protection.')
b.place('J1',16,29,orient='r');b.place('Q90',80,30,kind='pmos');b.join(('J1',2),('Q90',1));b.mark('Q90',5)
b.place('R90',50,42,orient='v');b.join(('Q90',1),('R90',1),via=[(50,30)])
b.place('D90',107,42,kind='zener',orient='v');b.join(('R90',1),('D90',1),via=[(50,20),(107,20)])
b.place('R91',145,52);b.join(('Q90',4),('R91',1),via=[(80,52)]);b.join(('R90',2),('R91',1),via=[(50,52)]);b.join(('D90',2),('R91',1),via=[(107,52)])
b.place('J19',203,53);b.join(('R91',2),('J19',1));b.mark('J19',2)
x.text('Q90 SO-8: peak loss / inrush SOA / OFF leakage / thermal: NOT_TESTED.',227,417,1.1)
x.text('Rear switch only sinks gate current. Do not connect a motor here.',227,425,1.1)
x.text('SW1 second pole connects motion J8: LOOP_3V3 to CLR_N.',227,433,1.1)
summary=x.finish();sch=d/(name+'.kicad_sch');s=sch.read_text().replace('(rev "S2 drawing layout")','(rev "P4 physical master")').replace('PROTOTYPE / UNVALIDATED - electrical design unchanged','PROTOTYPE / NOT_TESTED - new master stage and PH connectors').replace('2026-09-22','2026-09-23');sch.write_text(s)
(r/'master_schematic_layout.json').write_text(json.dumps(summary,indent=2)+'\n')
b=k.LoadBoard(str(p));nets={str(n):v for n,v in b.GetNetsByName().items()}
for n in ['PACK_FUSED','MASTER_GATE','MASTER_RETURN']:
 nn='/'+n
 if nn not in nets:nets[nn]=k.NETINFO_ITEM(b,nn);b.Add(nets[nn])
for f in b.GetFootprints():
 if f.GetReference()=='J1':
  f.SetValue(parts['J1']['value'])
  for pad in f.Pads():
   if pad.GetNumber()=='2':pad.SetNet(nets['/PACK_FUSED'])
 if f.GetReference()=='J17':f.SetField('Datasheet',parts['J17']['source'])
# Old BAT_IN copper bypassed the new switch and must be completely removed.
for t in list(b.GetTracks()):
 if t.GetNetname()=='/BAT_IN':b.Delete(t)
for c in new:
 lib,fn=c['footprint'].split(':');f=k.FootprintLoad(str(d/'footprints'/(lib+'.pretty')),fn);f.SetReference(c['ref']);f.SetValue(c['value']);f.SetPath(k.KIID_PATH('/'+root+'/'+c['uuid']));f.SetField('Datasheet',c.get('source',''));b.Add(f)
 if c['side']=='B':f.Flip(f.GetPosition(),False)
 f.SetOrientationDegrees(c['at'][2]);f.SetPosition(pt(*c['at'][:2]));f.Reference().SetVisible(False);f.Value().SetVisible(False)
 for pad in f.Pads():
  if pad.GetNumber() in c['pins']:pad.SetNet(nets['/'+c['pins'][pad.GetNumber()]['net']])
log=create(b)
rule=d/(name+'.kicad_dru');s=rule.read_text();s=s.replace("A.intersectsArea('NETBODY_J1') && A.NetName != '/BAT_IN'","A.intersectsArea('NETBODY_J1') && A.NetName != '/PACK_FUSED'")
for c in new:
 allowed=sorted({'/'+v['net'] for v in c['pins'].values() if v['net']});cond="A.intersectsArea('NETBODY_"+c['ref']+"')"+''.join(" && A.NetName != '"+n+"'" for n in allowed)
 s+='\n(rule '+json.dumps('P4 '+c['ref']+' unrelated nets outside body')+'\n (condition '+json.dumps(cond)+')\n (constraint disallow track via))\n'
rule.write_text(s);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
with (d/'assembly_bom.csv').open('w',newline='') as f:
 fields=['ref','value','footprint','source','note'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({a:c.get(a,'') for a in fields} for c in data['components'] if c['footprint'])
(r/'body_keepouts.json').write_text(json.dumps(log,indent=2)+'\n');print('P4 physical master added; route and native checks still required')
