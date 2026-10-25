"""Add documented package reconstructions to native exported board references.

OCP Python. No hardware project is written. The original STEP/meshes are retained.
Every reconstruction records its evidence and unmodeled details; none is measured.
"""
from pathlib import Path
import json,math,hashlib
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.gp import gp_Pnt
from convert_populated_pcbs import tessellate,bounds

P=Path(__file__).resolve().parents[2];OUT=P/'mechanical/sources/populated_P5'
inv=json.loads((OUT/'inventory.json').read_text())
def box(c,d):return BRepPrimAPI_MakeBox(gp_Pnt(*[c[i]-d[i]/2 for i in range(3)]),*d).Shape()
def cyl(c,r,h):return BRepPrimAPI_MakeCylinder(__import__('OCP.gp',fromlist=['gp_Ax2']).gp_Ax2(gp_Pnt(c[0],c[1],c[2]-h/2),__import__('OCP.gp',fromlist=['gp_Dir']).gp_Dir(0,0,1)),r,h).Shape()
def data(shape,mat='dark'):
    d=tessellate(shape);d['material']=mat;return d
def transform(s,r,t):
    s=dict(s);v=np.asarray(s['vertices_mm'])@r.T+t;s['vertices_mm']=v.tolist();s['cad_bounds_xyz_mm']=[[float(v[:,i].min()),float(v[:,i].max())] for i in range(3)];return s
def bb(ss):return [[min(s['cad_bounds_xyz_mm'][i][0] for s in ss),max(s['cad_bounds_xyz_mm'][i][1] for s in ss)] for i in range(3)]
audit={}
for kind,board in inv['boards'].items():
    cache=json.loads((OUT/f'{kind}_mesh.json').read_text());fps={f['reference']:f for f in board['footprints']}
    pcb=next(c for c in cache['components'] if c['reference']=='PCB');subheight=pcb['bounds_xyz_mm'][2][1]
    skin=(board['thickness_mm']-subheight)/2
    # KiCad exports the substrate with outer copper/mask absent. Reconstruct the
    # nominal finished board between substrate_bottom-skin and substrate_top+skin,
    # retaining every original XY edge and through hole, without moving packages.
    for s in pcb['solids']:
        for v in s['vertices_mm']:v[2]=v[2]*board['thickness_mm']/subheight-skin
        s['cad_bounds_xyz_mm'][2]=[-skin,subheight+skin]
        s['material']='pcb'
    pcb['bounds_xyz_mm']=bb(pcb['solids']);pcb['evidence']='NATIVE_EDGE_CUTS_AND_DRILLS_FINISHED_THICKNESS'
    pcb['substrate_to_finished_board']={'substrate_mm':subheight,'finished_mm':board['thickness_mm'],'outer_copper_and_mask_each_mm':skin,'component_positions_unmodified':True}
    front=subheight+skin;back=-skin
    for c in cache['components']:
        if c['reference']=='PCB':continue
        f=fps[c['reference']];c['value']=f['value'];c['evidence']='NATIVE_PLACEMENT_KICAD_LIBRARY_NOT_SELECTED_SKU_METROLOGY'
        for s in c['solids']:s['material']='ivory' if c['reference'].startswith('J') else 'dark'
    rebuild=list(board['missing_models'])
    if kind=='power':rebuild+=['C10','C30']
    added=[]
    for ref in rebuild:
        if ref=='U100':continue # Imported original WeAct CAD by a separate rigid transform.
        f=fps[ref];fp=f['footprint'];ss=[];evidence='';limit='No solder fillets or physical tolerance verification.'
        if 'XT30UPB-M' in fp:
            # AMASS2026 official catalogue p10; conservative solid housing. All
            # drilled pin coordinates are the actual native footprint pads.
            ss=[data(box((2.5,0,5.35),(10.2,5.6,10.7)),'yellow')]
            for x in [0,5]:ss.append(data(cyl((x,0,-1.5),.8,3),'metal'))
            evidence='AMASS2026 catalogue p10:10.2x5.6x10.7;3mm weld legs'
            limit='Conservative housing envelope; keyway, contacts and mating plug are not exact CAD. Native selected pin pitch5mm; lead dia1.6 is drawing reference.'
        elif ref.startswith('F'):
            ss=[data(box((0,0,1.345),(6.1,2.69,2.69)),'ivory')]
            evidence='Littelfuse451/453 datasheet p4:6.10+/-0.20 x2.69+/-0.25 x2.69+/-0.25mm'
        elif ref.startswith('L'):
            ss=[data(box((0,0,2.4),(6.7,6.6,4.8)))]
            for x in [-2.75,2.75]:ss.append(data(box((x,0,.15),(1.8,3,.3)),'metal'))
            evidence='Bourns SRP7050TA drawing:body6.7+/-0.3 x6.6+/-0.3 x4.8+/-0.2;terminal overall7.3+/-0.3'
            limit='Corner rounding/terminal folds are simplified. Maximum envelope7.6x6.9x5.0 remains a clearance requirement.'
        elif ref in ['U60','U70']:
            ss=[data(box((0,0,.6),(1.6,2.9,1.0)))]
            # Native DDC footprint has columns along X, three leads along Y.
            for x in [-1.05,1.05]:
                for y in [-.95,0,.95]:ss.append(data(box((x,y,.15),(.7,.3,.3)),'metal'))
            evidence='TI DDC0006A maximum2.9x2.8x1.1mm;0.95mm lead pitch'
            limit='Dimensioned package envelope, simplified lead folds, not original manufacturer CAD.'
        elif ref in ['C10','C30']:
            ss=[data(cyl((2.5,0,8),5,16),'dark')]
            for x in [0,5]:ss.append(data(cyl((x,0,-1),.3,2),'metal'))
            evidence='Panasonic EEUFR1C102 nominal diameter10,length16,pitch5;generic KiCad10mm tall can replaced'
            limit='Nominal can dimensions exact to datasheet. Trimmed lead length2mm is an assembly allowance; original leads must be trimmed. Sleeve/tolerances need measured sample.'
        elif ref=='SW1':
            ss=[data(box((0,0,1.75),(9.1,3.5,3.5)),'metal'),data(box((0,3.25,2.55),(1.5,3,1.5)),'dark')]
            for x in [-2.5,0,2.5]:
                for y in [-2.8,2.8]:ss.append(data(box((x,y,.15),(.6,1.0,.3)),'metal'))
            for x in [-3.4,3.4]:ss.append(data(cyl((x,0,-.25),.35,.5),'dark'))
            evidence='SOFNG MS-202V-G3 drawing:body9.1x3.5x3.5,stem3,travel2;6pads/2pegs from native footprint'
            limit='Stem centered neutral for fit view; real two positions+/-1mm. Stem toward native-Y edge inferred from footprint/drawing and requires sample orientation verification.'
        elif ref=='USB1':
            # Local +Y points toward opening for this bottom-side footprint;
            # body centre agrees with native footprint datum/pad registration.
            case=box((0,0,1.58),(8.94,7.35,3.16))
            case=BRepAlgoAPI_Cut(case,box((0,1.7,1.58),(8.34,5,2.56))).Shape()
            ss=[data(case,'metal'),data(box((0,1.0,1.58),(6.7,4,.7)),'dark')]
            evidence='HRO TYPE-C-31-M-12 manufacturer drawing:8.94x7.35x3.16,opening8.34x2.56'
            limit='Fillets, spring contacts and shell tabs simplified. Tongue0.7 from drawing; native fixing drill/pad pattern retained in PCB. Loose plug unmodeled.'
        else:raise RuntimeError((kind,ref,'No factual reconstruction rule'))
        angle=math.radians(f['rotation_deg']);rz=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1.]])
        # Native front local +Y becomes STEP +Y. Bottom flips X and Z around Y;
        # centroid symmetric parts are unaffected, while USB opening is +Y.
        rr=rz@(np.diag([-1.,1.,-1.]) if f['side']=='B' else np.eye(3))
        t=np.array([f['xy_mm'][0],-f['xy_mm'][1],front if f['side']=='F' else back])
        transformed=[transform(s,rr,t) for s in ss]
        entry={'reference':ref,'value':f['value'],'solids':transformed,'bounds_xyz_mm':bb(transformed),'evidence':'VENDOR_DIMENSIONED_RECONSTRUCTION','dimension_basis':evidence,'limitations':limit}
        cache['components']=[c for c in cache['components'] if c['reference']!=ref]+[entry];added.append({'ref':ref,'evidence':evidence,'limits':limit})
    cache.update(source_native_file=board['source'],source_native_sha256=board['source_sha256'],
      nominal_board_thickness_mm=board['thickness_mm'],native_substrate_origin_to_finished_bottom_mm=skin,
      source_revision=board['name'],unresolved_models=['U100 separate original manufacturer CAD'] if kind=='motion' else [],
      all_native_positions_preserved=True,library_limit='Generic library bodies retain native footprint placement; not every selected MPN matches all undocumented bevels/heights. No as-built claim.',supplements=added)
    path=OUT/f'{kind}_complete_mesh.json';path.write_text(json.dumps(cache,separators=(',',':')))
    audit[kind]={'component_count':len(cache['components']),'source_hash':board['source_sha256'],'output_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'reconstructions':added,'PCB':pcb['bounds_xyz_mm'],'unresolved_models':cache['unresolved_models']}
    print('COMPLETED_CACHE',kind,len(cache['components']),flush=True)
(OUT/'supplement_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
