"""Read-only release evidence for the scoped rear-board prototype."""
from pathlib import Path
import csv,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
import wx,pcbnew as k
APP=wx.App(False)
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];H=ROOT/'hardware/v1_2'
sys.path.insert(0,str(H/'tools'))
from layout_P5 import xy,rect
import all_trace_review_P5R2 as atlas
import audit_body_P5 as body
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
LIB=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')
OUT=HERE/'reports/rear';PRE=HERE/'previews/rear';PRE.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def paths(kind,rev='P5R7'):
    n=f'MORI_{kind}_{rev}';d=H/'kicad'/n
    return n,d,d/(n+'.kicad_pcb'),OUT
logs=[]
def run(args):
    cp=subprocess.run(args,capture_output=True,text=True)
    logs.append({'argv':args,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
    dump(OUT/'export_commands.json',logs)
    assert cp.returncode==0,(args,cp.stderr)
    return cp
name,d,p,_=paths('rear');oldname,oldd,oldp,_=paths('rear','P5R6')
for key,want in json.loads((OUT/'released/commands.json').read_text())['inputs'].items():assert sha(ROOT/key)==want
drc=json.loads((OUT/'released/drc.json').read_text());erc=json.loads((OUT/'released/erc.json').read_text())
assert not any(drc[key] for key in ['violations','unconnected_items','schematic_parity','ignored_checks'])
assert not erc['ignored_checks'] and not any(s['violations'] for s in erc['sheets'])
atlas.paths=paths;atlas.source=lambda kind:paths(kind,'P5R6')[:3]
before=atlas.extract('rear','before');after=atlas.extract('rear','after')
body.paths=paths
original_rect=body.rect
body.rect=lambda f:[6.5,19.5,16.4,24] if f.GetReference()=='J3' else original_rect(f)
body.audit('rear')
br=json.loads((OUT/'body_review_final.json').read_text())
br['method']+=' J3 uses documented 9.9x4.5mm plastic housing; the separate Fab pin-1 L mark is excluded.'
br['J3_manual_review']='Each of MASTER_RETURN, LOOP_3V3 and CLR_N approaches its own pad normal to the nearer housing edge (native -Y), without folding back or passing another component body; 1.7mm edge-to-pad-centre versus 2.8mm toward the far edge. Remaining body length after own pad copper is excluded is listed, not hidden.'
dump(OUT/'body_review_final.json',br)
assert not any(r['classification']=='FAIL_FOREIGN_NET' for r in br['body_crossing_inventory'])
a=k.LoadBoard(str(oldp));b=k.LoadBoard(str(p))
fp=lambda bb:{f.GetReference():f for f in bb.GetFootprints()}
aa,bb=fp(a),fp(b)
padmap=lambda bb:sorted((f.GetReference(),q.GetNumber(),q.GetNetname(),xy(q.GetSize()),xy(q.GetDrillSize()))for f in bb.GetFootprints()for q in f.Pads())
edges=lambda bb:sorted((int(g.GetShape()),xy(g.GetStart()),xy(g.GetEnd()))for g in bb.GetDrawings()if g.GetLayer()==k.Edge_Cuts)
pose=lambda f:(xy(f.GetPosition()),f.GetOrientationDegrees(),f.IsFlipped())
changed={r:{'before':pose(aa[r]),'after':pose(bb[r])}for r in aa if pose(aa[r])!=pose(bb[r])}
assert set(changed)=={'J3'} and padmap(a)==padmap(b) and edges(a)==edges(b)
assert sha(oldd/(oldname+'.kicad_dru'))==sha(d/(name+'.kicad_dru'))
olditems={t.m_Uuid.AsString():t for t in a.GetTracks()};newitems={t.m_Uuid.AsString():t for t in b.GetTracks()}
removed=[{'uuid':u,'net':t.GetNetname(),'via':isinstance(t,k.PCB_VIA),'xy':xy(t.GetPosition())} for u,t in olditems.items() if u not in newitems]
added=[{'uuid':u,'net':t.GetNetname(),'via':isinstance(t,k.PCB_VIA),'width_mm':k.ToMM(t.GetWidth(k.F_Cu)if isinstance(t,k.PCB_VIA)else t.GetWidth())} for u,t in newitems.items() if u not in olditems]
assert {r['net']for r in removed}<={'/MASTER_RETURN','/LOOP_3V3','/CLR_N','/GND'}
assert {r['net']for r in added}=={'/MASTER_RETURN','/LOOP_3V3','/CLR_N'}
for u in olditems.keys() & newitems.keys():
    x,y=olditems[u],newitems[u]
    assert (xy(x.GetStart()),xy(x.GetEnd()),x.GetLayer(),x.GetNetname())==(xy(y.GetStart()),xy(y.GetEnd()),y.GetLayer(),y.GetNetname())
oldflags={(x['type'],x['net'],tuple(x['uuids']))for x in before['candidates']}
newflags=[x for x in after['candidates']if(x['type'],x['net'],tuple(x['uuids']))not in oldflags]
assert not newflags
for phase,sch in [('before',oldd/(oldname+'.kicad_sch')),('after',d/(name+'.kicad_sch'))]:
    run([CLI,'sch','export','netlist','--format','kicadxml','-o',str(OUT/(phase+'_netlist.xml')),str(sch)])
def topology(path):
    return sorted((n.attrib['name'],sorted((x.attrib['ref'],x.attrib['pin'])for x in n.findall('node')))for n in ET.parse(path).getroot().findall('nets/net'))
assert topology(OUT/'before_netlist.xml')==topology(OUT/'after_netlist.xml')
models=[]
for f in b.GetFootprints():
    for model in f.Models():
        q=Path(str(model.m_Filename).replace('${KICAD10_3DMODEL_DIR}',str(LIB)).replace('${KIPRJMOD}',str(d)))
        models.append({'reference':f.GetReference(),'path':str(q),'exists':q.exists(),'sha256':sha(q)if q.exists()else None,'source_type':'Library CAD, not a measured product'})
assert all(m['exists'] for m in models if m['reference']=='J3')
step=PRE/(name+'_BOARD_AND_J3_REFERENCE.step')
run([CLI,'pcb','export','step','--force','--no-dnp','--component-filter','J3','--user-origin','0x0mm','--define-var',f'KICAD10_3DMODEL_DIR={LIB}','-o',str(step),str(p)])
dump(OUT/'model_sources.json',{'models':models,'step_sha256':sha(step),'pcb_sha256':sha(p),
    'export_scope':'Board and changed J3 ONLY. Reuse unchanged received source models for the other parts; no complete populated STEP claim.',
    'missing_library_model_references':[m['reference']for m in models if not m['exists']],
    'no_assigned_model_references':[f.GetReference()for f in b.GetFootprints()if not f.Models() and not f.GetReference().startswith('H')]})
for phase,source in [('before',oldp),('after',p)]:
    temp=OUT/(phase+'_REVIEW_ONLY.kicad_pcb');board=k.LoadBoard(str(source))
    for zone in list(board.Zones()):
        if not zone.GetIsRuleArea():board.Delete(zone)
    k.SaveBoard(str(temp),board)
    for label,layers in [('front','F.Cu,F.Fab,B.Fab,F.Silkscreen,Edge.Cuts'),('back','B.Cu,F.Fab,B.Fab,B.Silkscreen,Edge.Cuts')]:
        svg=PRE/(phase+'_'+label+'.svg');png=svg.with_suffix('.png')
        run([CLI,'pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--layers',layers,'-o',str(svg),str(temp)])
        js='require('+json.dumps(atlas.SHARP)+')(process.argv[1],{density:500}).resize({width:1800}).flatten({background:"#10151c"}).png().toFile(process.argv[2]);'
        run([atlas.NODE,'-e',js,str(svg),str(png)])
    temp.unlink()
for net in ['/MASTER_RETURN','/LOOP_3V3','/CLR_N']:
    (OUT/(net[1:]+'.svg')).write_text(atlas.picture(after,net))
changed_inputs=[]
for row in json.loads((HERE/'source_manifest_initial.json').read_text()):
    q=ROOT/row['path'];actual=sha(q)if q.exists()else None
    if actual!=row['sha256']:changed_inputs.append({'path':row['path'],'initial_sha256':row['sha256'],'current_sha256':actual})
assert not any(x['path'].startswith('hardware/') or x['path']=='contracts/components.json' for x in changed_inputs)
verification={'status':'PASS','scope':'Rear P5R7 J3 native/interface prototype review only','tool':drc['kicad_version'],
    'pcb_sha256':sha(p),'schematic_sha256':sha(d/(name+'.kicad_sch')),'ERC':0,'DRC':0,'unconnected':0,'parity':0,
    'ignored_checks':[],'native_pad_functions_sizes_drills_preserved':True,'schematic_topology_preserved':True,
    'outline_holes_other_component_poses_preserved':True,'native_outline_mm':[24,25],'nominal_stack_mm':k.ToMM(b.GetDesignSettings().GetBoardThickness()),
    'changed_placements':changed,'removed_copper':removed,'added_copper':added,'new_smoothness_flags':newflags,
    'foreign_body_route_candidates':0,'J3_own_pin_projection_rows':[r for r in br['body_crossing_inventory']if r['reference']=='J3'],
    'GND_stitch_change':'Two redundant GND stitches covered by the moved housing were removed. Numbered J3.2 remains plated-through GND; saved pours/refill and native connectivity pass. No power, CC, TVS or capacitor-return trace was modified.',
    'unrelated_external_source_changes':changed_inputs,'physical_test_status':'NOT_TESTED','mechanical_integration_status':'BLOCKED',
    'manufacturing_release':False,'preview_note':'Native SVGs omit pours in disposable review copies; back drawings shown in the same top-view coordinates, not mirrored assembly views.'}
dump(OUT/'verification.json',verification)
print('VERIFIED',sha(p),'models',len(models),'step',sha(step),flush=True)
