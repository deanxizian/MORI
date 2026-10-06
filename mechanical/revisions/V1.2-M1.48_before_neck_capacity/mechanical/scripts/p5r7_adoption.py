"""M1.45 component-up WeAct and received P5R7 interface stack.

The config owns dimensions. Source PCB models are loaded by native_electronics;
this phase changes only the core/header/socket assembly, never printed parts.
"""
from common import *
from native_electronics import aggregate,board_transform
from purchased_geometry import remove_generated,finish_reference
import hashlib

Q=P.get('p5r7_adoption',{})

def supplied_sources():
    for key in ['handoff','addendum']:
        path=PROJECT/Q[key]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==Q[key+'_sha256'],str(path)
    return json.loads((PROJECT/Q['handoff']).read_text())

def carrier_pads():
    inv=json.loads((PROJECT/P['native_electronics']['inventory']).read_text())
    module=next(x for x in inv['boards']['motion']['footprints'] if x['reference']=='U100')
    r,t=board_transform('motion')
    return {p['number']:(r@np.array([p['xy_mm'][0],-p['xy_mm'][1],0])+t)[:2] for p in module['pads']}

def known_source_pair(a,b,volume):
    """Classify only the measured source-model discrepancy as BLOCKED.

    Never suppress the contact or call it a passing fit. Larger/new collisions
    fail and source pin-number/size/hash checks independently constrain this.
    """
    if not Q.get('enabled'):return False
    q=Q['known_source_discrepancy']
    return set([a,b])==set(q['pair']) and abs(volume-q['candidate_overlap_mm3'])<=q['comparison_tolerance_mm3']

def add_reference(name,m,label,mpn,source):
    remove_generated(name);d=m.to_mesh64()
    o=mesh(name,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist())
    finish_reference(o,label,'CATALOGUE_ENVELOPE_WITH_ASSUMED_CONTACTS',['P5R7_HANDOFF'],'body','pcb')
    move_collection(o,'PLACEHOLDER');o['category']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['source_mpn']=mpn;o['source_file']=Q['handoff'];o['source_sha256']=Q['handoff_sha256']
    o['model_fidelity']='Vendor catalogue body dimensions; contacts/tolerances are trial allocations'
    o['selection_status']='ENGINEERING_CANDIDATE_NOT_PURCHASE_RELEASE';o['interface_status']='BLOCKED: full physical mating unqualified'
    o['unknown_dimensions']='Actual female contacts, insertion engagement, plating/tolerances and matched core E pin variant'
    o['p5r7_source']=source;o['source_scale_factor']=1.;o['export_candidate']=False
    o.data.materials.clear();o.data.materials.append(material('p5r7_unqualified',(.64,.29,.055)))
    return o

def apply_p5r7_adoption():
    if not Q.get('enabled'):return
    hand=supplied_sources();w=Q['weact'];cache=json.loads((PROJECT/w['source_mesh']).read_text())
    assert cache['source_sha256']==w['source_sha256'] and len(cache['solids'])==w['source_header_solid_count']
    raw=json.loads((PROJECT/P['native_electronics']['boards']['motion']['mesh']).read_text());br,bt=board_transform('motion',raw)
    pcb=next(c for c in raw['components'] if c['reference']=='PCB')
    carrier_top=max((np.array(s['vertices_mm'])@br.T+bt)[:,2].max() for s in pcb['solids'])
    thickness=-float(cache['solids'][0]['cad_bounds_xyz_mm'][2][0]);bottom=float(carrier_top+w['board_face_gap_mm'])
    r=np.array(w['rotation'],float);t=np.array([*w['translation_xy_mm'],bottom+thickness])
    components=[];moves=[]
    for i,s in enumerate(cache['solids']):
        if i==w['removed_bent_E_solid']:continue
        v=np.array(s['vertices_mm']);f=s['triangles']
        if i in w['flipped_header_solids']:
            cy=(v[:,1].min()+v[:,1].max())/2;hr=np.diag([1.,-1.,-1.]);ht=np.array([0,2*cy,-thickness]);v=v@hr.T+ht
            moves.append(dict(source_solid=i,rotation=hr.tolist(),translation_mm=ht.tolist()))
        components.append(dict(reference='VENDOR_'+str(i),value='WeAct original solid '+str(i),evidence='VENDOR_CAD_RIGID_HEADER_REORIENTATION' if i in w['flipped_header_solids'] else 'VENDOR_CAD',solids=[dict(vertices_mm=v.tolist(),triangles=f,material='pcb' if i==0 else 'dark')]))
    corecache=dict(source_file=cache['source_file'],source_sha256=cache['source_sha256'],source_revision='WeAct V1.1 / P5R7 component-up assembly',components=components)
    o,m,refs,falls=aggregate('MCU_Motion',corecache,r,t,'WeAct V1.1 元件面朝上／排针朝下')
    remove_generated('WeAct_Collision_Proxy')
    o['data_status']='ASSUMED';o['source_sha256']=cache['source_sha256'];o['placement_limit']='P5R7 requested geometry; 11.04mm nominal face gap, not measured engagement; E pin/hole qualification BLOCKED'
    o['source_header_moves']=json.dumps(moves);o['interface_status']='BLOCKED: E source STEP pin/hole inconsistency retained'
    o['documented_mass_g']=12;o['mass_status']='BUDGET_ASSUMPTION_NOT_MEASURED'
    pads=carrier_pads();epts=np.array([v for k,v in pads.items() if k.startswith('E')]);ec=epts.mean(0)
    male=next(s for s in Q['sockets'] if s.get('use'));maleheight=male['body_xyz_mm'][2]
    em=manifold.Manifold.cube(male['body_xyz_mm'],True).translate([*ec,bottom-maleheight/2])
    length=male['mating_pin_length_mm']+maleheight+male['solder_tail_mm']
    for x,y in epts:
        em+=manifold.Manifold.cube([Q['E_pin_square_mm'],Q['E_pin_square_mm'],length],True).translate([x,y,bottom+(male['solder_tail_mm']-male['mating_pin_length_mm']-maleheight)/2])
    add_reference('E_Straight_Header',em,'E口直排针候选／针孔配合待核',male['mpn'],'Unmodified catalogue square0.64mm pins; source STEP collision retained')
    socketrows=[]
    for label,letters,sku in [('AC',['A','C'],'61303021821'),('BD',['B','D'],'61303021821'),('E',['E'],'61300821821')]:
        s=next(x for x in Q['sockets'] if x['mpn']==sku);xy=np.array([v for k,v in pads.items() if k[0] in letters]);center=xy.mean(0);size=s['body_xyz_mm']
        z=float(carrier_top+size[2]/2);sm=manifold.Manifold.cube(size,True).translate([*center,z])
        for x,y in xy:
            depth=Q['trial_socket_contact_depth_mm'];sm-=manifold.Manifold.cube([*Q['trial_socket_hole_xy_mm'],depth],True).translate([x,y,carrier_top+size[2]-depth/2+.01])
            sm+=manifold.Manifold.cube([*Q['trial_socket_tail_xy_mm'],s['solder_tail_mm']],True).translate([x,y,carrier_top-s['solder_tail_mm']/2])
        add_reference('Socket_'+label,sm,'WeAct '+label+' 排母候选',sku,'Catalogue housing; internal contact relief assumed, not exact spring CAD')
        socketrows.append(dict(id='Socket_'+label,mpn=sku,body_xyz_mm=size,center_mm=[*center,z],tails_mm=s['solder_tail_mm']))
    vendor=json.loads((ROOT/'reports/vendor_weact_import.json').read_text());vendor.update(source_scale_factor=1,source_solid_count=224,retained_solid_count=223,retired_bent_E_source_solid=32,solid_count=224,component_side='UP',rotation=r.tolist(),translation_mm=t.tolist(),header_moves=moves,carrier_stack='P5R7 nominal11.04mm housing stack; E pin/hole and full contact engagement BLOCKED',collision_method='Exact source triangles with separate closed per-solid validation union; original E discrepancy retained',imported_bounds_xyz_mm=bounds(o));save_json(ROOT/'reports/vendor_weact_import.json',vendor)
    result=dict(revision=P['revision'],adoption_status='PASS',full_mated_fit='BLOCKED',handoff_sha256=Q['handoff_sha256'],addendum_sha256=Q['addendum_sha256'],core=dict(rotation=r.tolist(),translation_mm=t.tolist(),carrier_top_mm=float(carrier_top),core_bottom_mm=bottom,board_face_gap_mm=w['board_face_gap_mm'],vendor_substrate_thickness_mm=thickness,header_moves=moves),sockets=socketrows,fallbacks=falls,pads_world_xy_mm={k:v.tolist() for k,v in pads.items()},changed_existing_ids=Q['changed_existing_ids'],new_ids=Q['new_ids'],printed_parts_changed=False,limits=Q['limits'])
    save_json(ROOT/'reports/p5r7_adoption_build.json',result)
    npath=ROOT/'reports/native_electronics_geometry.json';native=json.loads(npath.read_text());native['unresolved']['WeAct_socket']='Three catalogue socket candidates installed; 11.04mm stack and E straight pin/hole interface remain BLOCKED';native['weact_P5R7']=result;save_json(npath,native)
    print('P5R7_ADOPTED',len(components),'source solids; three sockets and E header',flush=True)
