"""P2 populated-board audit and conditional rectangular power-bay capacity.

Blender -b mechanical/mori_v1_2.blend --python mechanical/scripts/analyze_p2_fit.py
No production PCB or released assembly is modified. Conservative capacities are
design proposals, not final S3 dimensions or physical fit certification.
"""
import sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
from p2_component_envelopes import missing_xt30_envelopes,SOURCE_URL

OUT=ROOT/'studies/pcb_P2_fit'
inventory=json.loads((OUT/'native_inventory.json').read_text())
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()

def cuboid(lo,hi):
    return manifold.Manifold.cube(tuple(np.array(hi)-lo)).translate(lo)
def cube_center(center,size):
    return cuboid((np.array(center)-np.array(size)/2).tolist(),(np.array(center)+np.array(size)/2).tolist())
def bb(m):
    b=m.bounding_box();return np.array(b[:3]),np.array(b[3:])
def overlap(a,b):
    al,ah=bb(a);bl,bh=bb(b)
    return np.all(ah>=bl) and np.all(bh>=al)
def vol(a,b):return max(0,(a^b).volume()) if overlap(a,b) else 0.
def min_gap(a,b,cap=4.):
    al,ah=bb(a);bl,bh=bb(b)
    if np.any(ah+cap<bl) or np.any(bh+cap<al):return cap
    return a.min_gap(b,cap)
fallbacks=[]
def from_solid(s,label):
    v=np.array(s['vertices_mm'],dtype=np.float64);f=np.array(s['triangles'],dtype=np.uint64)
    m=manifold.Manifold(manifold.Mesh64(v,f))
    if m.status()!=manifold.Error.NoError:
        fallbacks.append({'part':label,'reason':str(m.status()),'method':'conservative per-solid AABB; visible CAD retained'})
        m=cuboid(v.min(0).tolist(),v.max(0).tolist())
    return m

source={};cache={}
for kind in ['motion','imu','power']:
    c=json.loads((OUT/f'{kind}_mesh.json').read_text());cache[kind]=c
    source[kind]={x['reference']:manifold.Manifold.batch_boolean([from_solid(s,kind+'/'+x['reference']) for s in x['solids']],manifold.OpType.Add) for x in c['components']}
    for ref,m in source[kind].items():assert m.status()==manifold.Error.NoError,(kind,ref,m.status())
source['power'].update(missing_xt30_envelopes(inventory))

weact=json.loads((ROOT/'sources/v1_2_detail_fit/weact_v11_mesh.json').read_text())
wm=[from_solid(s,'WeAct/'+str(i)) for i,s in enumerate(weact['solids'])]
WM=manifold.Manifold.batch_boolean(wm,manifold.OpType.Add)
assert WM.status()==manifold.Error.NoError
# Rigid mapping from the manufacturer's header centres to native U100 A/B/C/D.
# It also puts the long male pin ends toward the carrier, without changing size.
WEACT_R=np.array([[0,-1,0],[-1,0,0],[0,0,-1]],dtype=float)
assert abs(np.linalg.det(WEACT_R)-1)<1e-9
SIZE={k:[source[k]['PCB'].bounding_box()[3+i]-source[k]['PCB'].bounding_box()[i] for i in range(2)] for k in source}
def placed(kind,center,z,angle=0,core_gap=6):
    w,d=SIZE[kind];r=Matrix.Rotation(math.radians(angle),3,'Z');r=np.array(r)
    tr=np.column_stack([r,np.array([*center,z])-r@np.array([w/2,-d/2,0])])
    result={f'{kind}/{n}':m.transform(tr) for n,m in source[kind].items()}
    if kind=='motion':
        # Source board lower face after inversion: front CAD plane + trial6mm gap.
        core_t=np.array([96.016-w/2,116.078-d/2,1.595+core_gap])
        # robot local Y = -native PCB Y: translation116.078 already includes35/2.
        core_t[1]=116.078
        core_tr=np.column_stack([r@WEACT_R,np.array([*center,z])+r@core_t])
        result['motion/U100']=WM.transform(core_tr)
        # Header sockets have not been selected. Reserve the whole module gap;
        # pin engagement/electrical mating remains BLOCKED.
        socket=cube_center([-8.2,0,1.595+core_gap/2],[41.6,33.22,core_gap])
        result['motion/UNSELECTED_SOCKET_RESERVE']=socket.transform(np.column_stack([r,np.array([*center,z])]))
    if kind=='power':
        for ref in ['C10','C30']:
            bounds=next(x for x in cache[kind]['components'] if x['reference']==ref)['bounds_xyz_mm']
            x=(bounds[0][0]+bounds[0][1])/2;y=(bounds[1][0]+bounds[1][1])/2
            # Generic KiCad model is10mm high, but S3 explicitly retains16mm parts.
            cap=manifold.Manifold.cylinder(16,5,5,64).translate([x,y,1.56])
            result[f'power/{ref}_16MM_REQUIRED']=cap.transform(tr)
    return result

exclude={'MCU_Motion','Body_IMU','Power_Module'}
targets={}
for o in [o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('role') in ['part','routing']]:
    n=o.name.removeprefix(PREFIX)
    if n in exclude:continue
    s=Solid(o)
    if s.hi[2]<105 or s.lo[2]>153:continue
    targets[n]=s.m

def clashes(items,environment,threshold=.01):
    found=[]
    for n,a in items.items():
        for k,b in environment.items():
            v=vol(a,b)
            if v>threshold:found.append({'part':n,'obstacle':k,'intersection_mm3':round(v,3)})
    return found

baseline={'motion':{'center':[0,-37],'z':118,'angle':0},
          'imu':{'center':[-32,39],'z':118,'angle':90},
          'power':{'center':[0,6],'z':117,'angle':0}}
old_parts={n:m for k,p in baseline.items() for n,m in placed(k,**p).items()}
old_clashes=clashes(old_parts,targets)

# Capacity studies may replace ONLY the removable power carrier and local
# board seats on the common deck. The yaw bridge, battery, speaker and outer
# shell remain. No fixed bearing/servo relocation is hidden in this proposal.
fixed={n:m for n,m in targets.items() if n!='Power_Board_Carrier' and not n.startswith('Power_Carrier_')}
seat_cut=cube_center([0,-37.75,117.5],[74.2,35.7,5])
imu_cut=cube_center([-32,39,117.5],[19.8,24.2,5])
fixed['Load_Frame']=fixed['Load_Frame']-seat_cut-imu_cut
support_changes=['Replace removable83x52x2 power carrier by short PCB supports on deck; final holes await S3',
                 'Relocate MCU and rigid IMU seats, preserving a continuous4mm load deck',
                 'Rear MCU mounting plate/bolt access must be redrawn at native P2 holes; not yet manufactured']

# Move only the lower end of the existing body-fixed head trunk3mm left and
#3mm forward. Radius stays1.2mm; upper points/service loop stay unchanged.
# This is a routing reservation, not a specified real harness/bend radius.
new_trunk_points=[[-45,28,137],[-42+10*7/22,25-15*7/22,144],[-32,10,159],[-P['head_joint'].get('yaw_cable_clip_abs_x_mm',18),0,153]]
def beam_solid(a,b,r=1.2):
    a=Vector(a);b=Vector(b);tr=(b-a).to_track_quat('Z','Y').to_matrix()
    return manifold.Manifold.cylinder((b-a).length,r,r,32).transform(np.column_stack([np.array(tr),np.array(a)]))
trunk=manifold.Manifold.batch_boolean([beam_solid(a,b) for a,b in zip(new_trunk_points,new_trunk_points[1:])],manifold.OpType.Add)
trunk_clashes=clashes({'Head_Trunk_PROPOSED':trunk},{n:m for n,m in fixed.items() if n not in ['Head_Trunk','Yaw_Service_Loop']})
assert not trunk_clashes,trunk_clashes
fixed['Head_Trunk']=trunk
support_changes.append('Move body head-trunk lower endpoint from[-42,25,137] to[-45,28,137]mm; rejoin old route atZ144; keep upper route/service loop')

# Find the closest candidate movements with original-size native boards.
motion_trials=[]
for y in [-39,-40,-41,-42,-43,-44]:
    for z in [121,122,123,124,125]:
        items=placed('motion',[0,y],z)
        bad=clashes(items,fixed)
        nearest=min((min_gap(a,b,2.) for a in items.values() for b in fixed.values()),default=2)
        motion_trials.append({'center':[0,y],'z':z,'angle':0,'min_gap_mm':round(nearest,3),'collisions':bad})
        if not bad and nearest>=1:break
imu_trials=[]
for c in [[-32,39],[-47,35],[-48,34],[-49,33],[-49,34],[-50,33],[47,35],[48,34],[49,33]]:
    for z in [119.5,121,123,125]:
        items=placed('imu',c,z,90);bad=clashes(items,fixed)
        nearest=min((min_gap(a,b,2.) for a in items.values() for b in fixed.values()),default=2)
        imu_trials.append({'center':c,'z':z,'angle':90,'min_gap_mm':round(nearest,3),'collisions':bad})
        if not bad and nearest>=1:break

save_json(OUT/'preliminary_fit.json',{'baseline_placements':baseline,'baseline_collisions':old_clashes,
          'motion_trials':motion_trials,'imu_trials':imu_trials,'fallbacks':fallbacks,'support_changes':support_changes})
print('PRELIMINARY',len(old_clashes),'baseline collisions',flush=True)
valid_m=[p for p in motion_trials if not p['collisions'] and p['min_gap_mm']>=1]
valid_i=[p for p in imu_trials if not p['collisions'] and p['min_gap_mm']>=1]
print('MOTION_OPTIONS',[(x['center'],x['z'],x['min_gap_mm']) for x in valid_m],flush=True)
print('IMU_OPTIONS',[(x['center'],x['z'],x['min_gap_mm']) for x in valid_i],flush=True)
if not valid_m or not valid_i:raise RuntimeError('No approved study placement; inspect preliminary_fit.json')

# Axes-fixed rectangle study: width measured left/right, depth front/back.
# Whole board gets16mm above nominal front plane and3mm underside allowance;
# 1mm geometric separation is required, but is NOT a cable bend allowance.
power_z=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2+4.5
samples=[];best=None
for mp in valid_m:
    for ip in valid_i:
        mi=placed('motion',**{k:mp[k] for k in ['center','z','angle']})
        ii=placed('imu',**{k:ip[k] for k in ['center','z','angle']})
        if clashes(ii,mi):continue
        env=dict(fixed,**mi,**ii)
        for center_y in range(1,11):
            width=2*(P['belly_relayout']['yaw_bridge_half_width_mm']-P['belly_relayout']['yaw_bridge_leg_thickness_mm'])-2
            bestdepth=0;blocking=None
            # Width82 = bridge inner84 minus1mm per side. Also test this with
            # actual meshes; it is not justified by its AABB alone.
            for depth in range(44,65):
                a=cuboid([-width/2,center_y-depth/2,power_z-3],[width/2,center_y+depth/2,power_z+1.6+16])
                near=[];ok=True
                for n,b in env.items():
                    v=vol(a,b);g=min_gap(a,b,1.01)
                    if v>.01 or g<.999:
                        blocking={'part':n,'gap_mm':round(g,3),'intersection_mm3':round(v,3)};ok=False;break
                    near.append((g,n))
                if not ok:break
                bestdepth=depth
            rec={'width_mm':width,'depth_mm':bestdepth,'center_y_mm':center_y,'pcb_dielectric_bottom_z_mm':power_z,
                 'motion':{k:mp[k] for k in ['center','z','angle']},'imu':{k:ip[k] for k in ['center','z','angle']},'next_depth_blocker':blocking}
            samples.append(rec)
            score=(width*bestdepth,-abs(mp['center'][1]+37)-abs(ip['center'][0]+32),-abs(center_y-6))
            if best is None or score>best[0]:best=(score,rec)
        print('CAPACITY_GRID',mp['center'],ip['center'],'best',best[1]['depth_mm'],flush=True)

chosen=best[1]
assert chosen['depth_mm']>0,'No capacity found'
chosen_boards={}
for kind in ['motion','imu']:
    chosen_boards.update(placed(kind,**chosen[kind]))
chosen_environment=dict(fixed,**chosen_boards)
candidate_sizes=[]
for size in [[80,55],[80,60],[82,chosen['depth_mm']]]:
    a=cuboid([-size[0]/2,chosen['center_y_mm']-size[1]/2,power_z-3],
             [size[0]/2,chosen['center_y_mm']+size[1]/2,power_z+17.6])
    distances=sorted([{'part':n,'gap_mm':round(min_gap(a,m,5),3),'intersection_mm3':round(vol(a,m),3)} for n,m in chosen_environment.items()],key=lambda x:x['gap_mm'])
    candidate_sizes.append({'xy_mm':size,'center_xy_mm':[0,chosen['center_y_mm']],
                            'bounds_xyz_mm':[[float(l),float(h)] for l,h in zip(*bb(a))],
                            'closest_obstacles':distances[:8],
                            'status':'PASS_GEOMETRY_ONLY' if all(x['gap_mm']>=.999 and x['intersection_mm3']<=.01 for x in distances) else 'FAIL'})
fitted_p2=placed('power',[0,chosen['center_y_mm']],power_z)
p2_fit_clashes=clashes(fitted_p2,chosen_environment)
module_to_carrier=clashes({'motion/U100':chosen_boards['motion/U100']},
                          {n:m for n,m in chosen_boards.items() if n.startswith('motion/') and n not in ['motion/U100','motion/UNSELECTED_SOCKET_RESERVE']})
result={'revision':'P2_FIT_STUDY_1','source_mechanical_revision':P['revision'],
        'units':'mm','status':'CONDITIONAL_GEOMETRIC_CAPACITY_NOT_S3_RELEASE',
        'scope':'Actual P2 native files plus current routing tubes; power is historical, S3 outline is not inferred',
    'maximum_sampled_rectangle':chosen,'capacity_samples':samples,
    'candidate_limits':candidate_sizes,'placed_historical_P2_power_collisions':p2_fit_clashes,
    'WeAct_against_native_carrier_components':module_to_carrier,
    'head_trunk_proposal':{'points_mm':new_trunk_points,'radius_mm':1.2,'static_collisions':trunk_clashes,'status':'CONSERVATIVE_ROUTING_NOT_REAL_HARNESS'},
        'required_local_support_changes':support_changes,
        'method':{'mesh_kernel':'manifold3d Mesh64 union/intersection and min_gap',
                  'power_width_mm':82,'depth_grid_mm':[44,64,1],'power_center_y_grid_mm':[1,10,1],
                  'pcb_dielectric_bottom_z_mm':power_z,'above_board_component_reserve_mm':16,
                  'below_board_reserve_mm':3,'minimum_geometric_gap_mm':1,
                  'finite_grid_not_global_optimum':True},
        'native_sources_sha256':{k:v['source_sha256'] for k,v in inventory['boards'].items()},
        'geometry_fallbacks':fallbacks,
        'vendor_dimension_envelopes':{'references':list(missing_xt30_envelopes(inventory)),
             'part':'AMASS XT30UPB-M30','body_xyz_mm':[10.2,5.6,10.7],'weld_leg_mm':3,
             'source_url':SOURCE_URL,'catalogue_page':10,'scope':'Conservative body/pin solids, no mating plug;8 missing KiCad models repaired in study only'},
        'not_tested':['Mating plug SKUs, actual bend radii and harness access', 'Thermal copper, high-current clearances, S3 circuit routing',
                      'Fasteners/support strength and physical manufacture', 'Full motion sweep after future mount redesign'],
        'weact_mapping':{'rotation':WEACT_R.tolist(),'scale':1,'source_origin_translation_to_carrier_center_xy_mm':[61.016,116.078],
                         'core_lower_face_above_front_plane_mm':6,'header_status':'ASSUMED6mm stack; male-pin seating and female socket SKU remain BLOCKED'},
        'baseline_fit':{'collisions':old_clashes,'placements':baseline}}
save_json(OUT/'fit_results.json',result)
proposal_meshes={}
for n in ['Load_Frame','Head_Trunk']:
    mm=fixed[n].to_mesh64()
    proposal_meshes[n]={'vertices_mm':mm.vert_properties[:,:3].tolist(),'triangles':mm.tri_verts.tolist()}
save_json(OUT/'proposed_support_meshes.json',proposal_meshes)
print('P2_FIT_ANALYSIS_COMPLETE',json.dumps(chosen),flush=True)
