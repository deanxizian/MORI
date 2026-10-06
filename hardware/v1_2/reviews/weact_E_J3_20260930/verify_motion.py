"""Native verification and review exports; not a fabrication release."""
from update_native_P5R7 import *
import xml.etree.ElementTree as ET
import all_trace_review_P5R2 as atlas
import audit_body_P5 as body
from body_keepouts_P3R1 import rectangle

OUT=HERE/'reports/motion';PRE=HERE/'previews/motion';PRE.mkdir(parents=True,exist_ok=True)
def audit_paths(kind,rev='P5R7'):
    name,d,p=paths(kind,rev);return name,d,p,OUT
name,d,p=paths('motion');oldname,oldd,oldp=paths('motion','P5R6')
commands=json.loads((OUT/'released/commands.json').read_text())
for key,value in commands['inputs'].items():assert sha(ROOT/key)==value
drc=json.loads((OUT/'released/drc.json').read_text());erc=json.loads((OUT/'released/erc.json').read_text())
assert not any(drc[q]for q in ['violations','unconnected_items','schematic_parity','ignored_checks'])
assert not erc['ignored_checks'] and not any(s['violations']for s in erc['sheets'])
a=k.LoadBoard(str(oldp));b=k.LoadBoard(str(p))
fps=lambda bb:{f.GetReference():f for f in bb.GetFootprints()}
aa,bb=fps(a),fps(b)
pose=lambda f:(xy(f.GetPosition()),f.GetOrientationDegrees(),f.IsFlipped())
assert all(pose(aa[r])==pose(bb[r])for r in aa if r not in ['R19','R9'])
assert pose(bb['R19'])==((32,16.575),0,True)
assert pose(bb['R9'])[0]==(45,17) and pose(bb['R9'])[1:]==pose(aa['R9'])[1:]
edge=lambda board:sorted((int(g.GetShape()),xy(g.GetStart()),xy(g.GetEnd()))for g in board.GetDrawings()if g.GetLayer()==k.Edge_Cuts)
assert edge(a)==edge(b)
changed=[]
for ref in aa:
    old={q.GetNumber():q for q in aa[ref].Pads()};new={q.GetNumber():q for q in bb[ref].Pads()}
    assert old.keys()==new.keys()
    for pin,x in old.items():
        y=new[pin]
        assert (x.GetNetname(),xy(x.GetSize()),xy(x.GetDrillSize()),int(x.GetShape()))==(y.GetNetname(),xy(y.GetSize()),xy(y.GetDrillSize()),int(y.GetShape()))
        delta=tuple(round(v-u,6)for u,v in zip(xy(x.GetPosition()),xy(y.GetPosition())))
        if delta!=(0,0):
            if ref in ['R19','R9']:continue
            assert ref=='U100' and pin.startswith('E') and delta==(2.54,0)
            changed.append({'pin':pin,'net':y.GetNetname(),'old_mm':xy(x.GetPosition()),'new_mm':xy(y.GetPosition())})
assert len(changed)==8
lib=k.FootprintLoad(str(d/'footprints/MORI_Custom.pretty'),'WeAct_F4_64Pin_V11_ECorrected_P5R7')
loaded={q.GetNumber():xy(q.GetPosition())for q in lib.Pads()}
for q in bb['U100'].Pads():
    want=loaded[q.GetNumber()];actual=xy(q.GetPosition())
    assert all(abs((actual[i]-[6,.89][i])-want[i])<.000002 for i in range(2))

atlas.paths=audit_paths;atlas.source=lambda kind:paths(kind,'P5R6')
before=atlas.extract('motion','before');after=atlas.extract('motion','after')
body.paths=audit_paths;body.audit('motion')
review=json.loads((OUT/'body_review_final.json').read_text())
assert not any(x['classification']=='FAIL_FOREIGN_NET'for x in review['body_crossing_inventory'])
oldflags={(x['type'],x['net'],tuple(x['uuids']))for x in before['candidates']}
flags=[x for x in after['candidates']if(x['type'],x['net'],tuple(x['uuids']))not in oldflags]
dump(OUT/'new_style_candidates.json',flags)

socket=rectangle([33.66,17.76,38.74,28.42]);socket_hits=[]
for t in b.GetTracks():
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='/NRST':continue
    if socket.Collide(t.GetEffectiveShape(t.GetLayer()),0):
        socket_hits.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'position':xy(t.GetPosition())})
assert not socket_hits,socket_hits
olditems={t.m_Uuid.AsString():t for t in a.GetTracks()};newitems={t.m_Uuid.AsString():t for t in b.GetTracks()}
removed=[{'uuid':u,'net':t.GetNetname(),'via':isinstance(t,k.PCB_VIA)}for u,t in olditems.items()if u not in newitems]
added=[{'uuid':u,'net':t.GetNetname(),'via':isinstance(t,k.PCB_VIA)}for u,t in newitems.items()if u not in olditems]
scope={'/NRST','/IMU_CS','/IMU_MOSI','/IMU_SCK','/ARM_FEEDBACK','/ARM_Q','/CLR_N','/USER_KEY_N','/CHG_N','/BAT_ADC_IN','/WHEEL_ADC_IN','/CURRENT_ADC_IN','/S288_BUS','/FAULT_N','/HEAD_BUS','/CAM_RX_BUF','/CAM_RX','/CAM_TX','/+3V3','/GND'}
assert {x['net']for x in removed+added}<=scope
assert not any(not isinstance(t,k.PCB_VIA) and t.GetLayer()not in [k.F_Cu,k.B_Cu]for t in b.GetTracks())
for u in olditems.keys()&newitems.keys():
    x,y=olditems[u],newitems[u]
    assert (xy(x.GetStart()),xy(x.GetEnd()),x.GetLayer(),x.GetNetname())==(xy(y.GetStart()),xy(y.GetEnd()),y.GetLayer(),y.GetNetname())
logs=[]
def run(args):
    cp=subprocess.run(args,capture_output=True,text=True)
    logs.append({'argv':args,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
    dump(OUT/'export_commands.json',logs);assert cp.returncode==0,(args,cp.stderr)
for phase,sch in [('before',oldd/(oldname+'.kicad_sch')),('after',d/(name+'.kicad_sch'))]:
    run([CLI,'sch','export','netlist','--format','kicadxml','-o',str(OUT/(phase+'_netlist.xml')),str(sch)])
def topology(path):return sorted((n.attrib['name'],sorted((x.attrib['ref'],x.attrib['pin'])for x in n.findall('node')))for n in ET.parse(path).getroot().findall('nets/net'))
assert topology(OUT/'before_netlist.xml')==topology(OUT/'after_netlist.xml')
stepfile=PRE/(name+'_BARE_BOARD.step')
run([CLI,'pcb','export','step','--force','--board-only','--user-origin','0x0mm','-o',str(stepfile),str(p)])
for phase,source in [('before',oldp),('after',p)]:
    temp=OUT/(phase+'_REVIEW_ONLY.kicad_pcb');board=k.LoadBoard(str(source))
    for zone in list(board.Zones()):
        if not zone.GetIsRuleArea():board.Delete(zone)
    k.SaveBoard(str(temp),board)
    for side,layers in [('front','F.Cu,F.Fab,B.Fab,F.Silkscreen,Edge.Cuts'),('back','B.Cu,F.Fab,B.Fab,B.Silkscreen,Edge.Cuts')]:
        svg=PRE/(phase+'_'+side+'.svg')
        run([CLI,'pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--layers',layers,'-o',str(svg),str(temp)])
        js='require('+json.dumps(atlas.SHARP)+')(process.argv[1],{density:500}).resize({width:2400}).flatten({background:"#10151c"}).png().toFile(process.argv[2]);'
        run([atlas.NODE,'-e',js,str(svg),str(svg.with_suffix('.png'))])
    temp.unlink()
for net in sorted(scope-{'/GND'}):(OUT/(net[1:]+'.svg')).write_text(atlas.picture(after,net))
result={'status':'PASS'if not flags else'FAIL','scope':'Motion P5R7 native and E socket routing checks only',
 'tool':drc['kicad_version'],'pcb_sha256':sha(p),'schematic_sha256':sha(d/(name+'.kicad_sch')),
 'ERC':0,'DRC':0,'unconnected':0,'parity':0,'ignored_checks':[],'inner_signal_tracks':0,
 'outline_holes_poses_except_R19_R9_unchanged':True,'A_D_positions_and_all_numbered_functions_unchanged':True,
 'changed_placement':{r:{'before':pose(aa[r]),'after':pose(bb[r])}for r in ['R19','R9']},
 'E_pad_change':changed,'native_library_pad_match':True,'schematic_topology_preserved':True,
 'removed_copper':removed,'added_copper':added,'new_style_candidates':flags,'E_foreign_tracks_and_vias':socket_hits,
 'bare_STEP':str(stepfile.relative_to(ROOT)),'bare_STEP_sha256':sha(stepfile),'populated_STEP':None,
 'mechanical_stack':'BLOCKED_PENDING_INTEGRATION','physical_tests':'NOT_TESTED','manufacturing_release':False,
 'preview_note':'Copper pours omitted only in disposable native preview copies. Both sides use unmirrored native top coordinates.'}
dump(OUT/'verification.json',result)
print('Native and topology checks PASS; new style candidates',len(flags),flush=True)
