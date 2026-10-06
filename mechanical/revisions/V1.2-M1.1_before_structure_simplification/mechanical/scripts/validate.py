"""Actual triangulated-solid checks; PASS never means hardware, control or manufacturing approval."""
import sys,math,itertools,time,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from mathutils.bvhtree import BVHTree
from export import topology
CHECKS=[]

def check(id,status,summary,data=None,method=None):
    CHECKS.append(dict(id=id,status=status,summary=summary,measurement=data,method=method)); print('CHECK',id,status,flush=True)

class Solid:
    def __init__(self,o,base=None,tr=None):
        self.o=o; self.name=o.name.removeprefix(PREFIX); self.group=o.get('group'); self.tree=None
        if base is None:
            o=bpy.data.objects[o['validation_proxy']] if o.get('validation_proxy') else o
            o.data.calc_loop_triangles(); self.v=np.array([tuple(v) for v in vertices_world(o)],dtype=np.float64); self.f=np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.uint64)
            self.m=manifold.Manifold(manifold.Mesh64(self.v,self.f))
        else:
            mat=np.array(tr,dtype=np.float64); self.v=base.v@mat[:3,:3].T+mat[:3,3]; self.f=base.f; self.m=base.m.transform(mat[:3,:])
        self.lo=self.v.min(axis=0); self.hi=self.v.max(axis=0)
        if self.m.status()!=manifold.Error.NoError: raise ValueError(self.name+': '+str(self.m.status()))
    def bvh(self):
        if self.tree is None: self.tree=BVHTree.FromPolygons([Vector(v) for v in self.v],self.f.tolist(),all_triangles=True,epsilon=1e-6)
        return self.tree

def broad(a,b): return bool(np.all(a.hi>=b.lo-1e-5) and np.all(b.hi>=a.lo-1e-5))
def intersect_volume(a,b):
    if not broad(a,b): return 0
    return max(0,(a.m^b.m).volume())
def rigidtr(yaw=0,pitch=0):
    c=Vector((0,0,D['head_z'])); return Matrix.Translation(c)@Matrix.Rotation(math.radians(yaw),4,'Z')@Matrix.Rotation(math.radians(pitch),4,'X')@Matrix.Translation(-c)

def actual_checks(solids,quick=False):
    contacts={tuple(sorted((v['a'],v['b']))):v['reason'] for v in json.loads((ROOT/'reports/intended_contacts.json').read_text())}
    tol=P['validation']['collision_volume_tolerance_mm3']; failed=[]; touching=[]
    for a,b in itertools.combinations(solids.values(),2):
        v=intersect_volume(a,b)
        if v>tol:
            failed.append(dict(a=a.name,b=b.name,volume_mm3=round(v,4),intended_interface=contacts.get(tuple(sorted((a.name,b.name))))))
        elif broad(a,b) and tuple(sorted((a.name,b.name))) in contacts:
            touching.append(dict(a=a.name,b=b.name,note=contacts[tuple(sorted((a.name,b.name)))]))
    save_json(ROOT/'reports/static_interference.json',{'volume_threshold_mm3':tol,'failed_pairs':failed,'declared_interfaces':touching,'algorithm':'AABB broadphase only, then actual Manifold triangle-solid intersection volume, including containment; intended interfaces do NOT waive volume penetrations'})
    has_proxy=any(a.o.get('validation_proxy') for a in solids.values())
    check('static_rigid_solids','FAIL' if failed else 'BLOCKED' if has_proxy else 'PASS','刚性实体采样 / 原厂两接插件仅完成保守代理检查',{'failures':len(failed),'details':'static_interference.json','vendor_proxy_details':'vendor_lcd_import.json'},'Manifold triangle-solid intersections; LCD111 CAD solids plus two connector bounds. Even zero overlaps is not reported as full exact-hardware PASS.')
    if quick: return
    motion_bad=[]; cable_bad=[]; routes=[Solid(o) for o in bpy.context.scene.objects if o.get('role')=='routing']; yawvals=list(range(-60,61,P['validation']['yaw_step_deg'])); pitchvals=list(range(-20,26,P['validation']['pitch_step_deg']))
    yawparts=[a for a in solids.values() if a.group=='yaw']; pitchparts=[a for a in solids.values() if a.group=='pitch']; fixed=[a for a in solids.values() if a.group not in ['yaw','pitch']]
    extentlo=np.min([a.lo for a in fixed],axis=0); extenthi=np.max([a.hi for a in fixed],axis=0)
    for yaw in yawvals:
        ys=[Solid(a.o,a,rigidtr(yaw,0)) for a in yawparts]
        for pitch in pitchvals:
            ps=[Solid(a.o,a,rigidtr(yaw,pitch)) for a in pitchparts]
            for a,b in itertools.chain(itertools.product(ys,fixed),itertools.product(ps,fixed+ys)):
                v=intersect_volume(a,b)
                if v>tol: motion_bad.append(dict(yaw_deg=yaw,pitch_deg=pitch,a=a.name,b=b.name,volume_mm3=round(v,3)))
            for cable in routes:
                ca=Solid(cable.o,cable,rigidtr(yaw,pitch if cable.group=='pitch' else 0)) if cable.group in ['yaw','pitch'] else cable
                for target in fixed+ys+ps:
                    if ca.group==target.group: continue
                    volume=intersect_volume(ca,target)
                    if volume>.1: cable_bad.append(dict(yaw_deg=yaw,pitch_deg=pitch,route=ca.name,part=target.name,volume_mm3=round(volume,3)))
            for a in ys+ps: extentlo=np.minimum(extentlo,a.lo); extenthi=np.maximum(extenthi,a.hi)
        print('YAW_GRID',yaw,flush=True)
    save_json(ROOT/'reports/head_motion.json',{'yaw_deg':yawvals,'pitch_deg':pitchvals,'poses':len(yawvals)*len(pitchvals),'failures':motion_bad,'bounds_xyz_mm':list(zip(extentlo.tolist(),extenthi.tolist())),'size_xyz_mm':(extenthi-extentlo).tolist(),'algorithm':'Rigid group transforms applied to same closed triangle meshes. All moving groups vs fixed and each other. Internal rigid-group pairs checked in static pass. No inter-sample proof.'})
    check('combined_yaw_pitch','FAIL' if motion_bad else 'BLOCKED' if has_proxy else 'PASS','Yaw/Pitch 联合采样 / 两接插件精确网格待核',{'poses':len(yawvals)*len(pitchvals),'yaw_step_deg':10,'pitch_step_deg':5,'failures':len(motion_bad),'bounds_xyz_mm':list(zip(extentlo.tolist(),extenthi.tolist()))},'Solid-volume intersection with two declared connector proxies; no continuous or complete as-built proof')
    save_json(ROOT/'reports/cable_motion.json',{'poses':len(yawvals)*len(pitchvals),'conservative_tube_radius_mm':1.2,'failures':cable_bad,'limitations':'Fixed/pitch/yaw routing allocations and toroidal service-loop envelopes, not a flexible cable solver. Endpoint terminations within same rigid group reviewed separately.'})
    check('sampled_cable_allocations','FAIL' if cable_bad else 'PASS','联合姿态中的线束预留体与不同运动组实体',{'poses':130,'failure_count':len(cable_bad),'details':'cable_motion.json'},'Actual tube/torus triangle-solid intersections at yaw 10 deg x pitch 5 deg; does not qualify wire strain/bend fatigue')
    check('continuous_motion_proof','NOT_TESTED','有限采样不是连续空间数学证明；弹性、制造公差、舵机回差未建模')
    # Local wheel pockets have overhanging spherical flanks: a global X-plane bound is invalid.
    wheelbad=[]; wheelgaps=[]; targets=[a for n,a in solids.items() if n in ['Body_Upper','Body_Lower','Head_Front','Head_Rear','Head_Lower_Guard']]
    for s,n in [(-1,'L'),(1,'R')]:
        c=Vector((s*D['wheel_x'],0,D['wheel_z']))
        for angle in range(0,361,10):
            tr=Matrix.Translation(c)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-c)
            for name in ['Tire_','Wheel_Hub_','Wheel_Cap_']:
                a=Solid(solids[name+n].o,solids[name+n],tr)
                for b in targets:
                    v=intersect_volume(a,b)
                    if v>tol: wheelbad.append(dict(deg=angle,a=a.name,b=b.name,volume_mm3=v))
                    wheelgaps.append(dict(deg=angle,a=a.name,b=b.name,distance_mm=a.m.min_gap(b.m,10.0)))
    nearest=min(wheelgaps,key=lambda v:v['distance_mm'])
    save_json(ROOT/'reports/wheel_clearance.json',{'method':'Manifold min_gap actual closed triangulated solids, search length 10 mm (larger distances capped); all shell targets, wheel/tire/cap, both sides, 37 poses each','samples':wheelgaps,'minimum':nearest,'continuous_proof':'NOT_TESTED'})
    check('wheel_360_clearance','PASS' if not wheelbad and nearest['distance_mm']>=3 else 'FAIL','两侧轮胎、轮毂及轮盖完整转动与壳体实际间隙',{'poses_each':37,'minimum_solid_gap_mm':nearest['distance_mm'],'minimum_pair':nearest,'target_gap_mm':P['wheel_body_gap_mm'],'failures':wheelbad,'intentional_contacts':'Axle/bearing pairs separate; not part of wheel-shell gap'},'10 degree actual mesh intersection and solid minimum-distance sampling; local wheel pockets invalidate the old global X-plane bound; finite sampling only')

def geometry_checks(solids):
    lo=np.min([a.lo for a in solids.values()],axis=0); hi=np.max([a.hi for a in solids.values()],axis=0)
    body_width=max(solids[n].hi[0] for n in ['Body_Upper','Body_Lower'])-min(solids[n].lo[0] for n in ['Body_Upper','Body_Lower'])
    check('assembled_size','PASS' if hi[2]<=300 and 285<=hi[2]<=295 else 'FAIL','装配真实包围尺寸',{'xyz_mm':(hi-lo).tolist(),'bounds_xyz_mm':list(zip(lo.tolist(),hi.tolist())),'body_front_width_mm':float(body_width),'wheel_pocket_seat_width_mm':2*P['body_side_cut_x_mm'],'head_diameter_mm':P['head_diameter_mm']},'All physical rigid meshes, excluding separate dock, coupons, rendering and keepouts; body width measured from actual upper/lower mesh')
    mother=[]
    for name,center,r in [('Head_Mother',Vector((0,0,D['head_z'])),D['head_radius']),('Body_Mother',Vector((0,0,D['body_z'])),D['body_radius'])]:
        o=bpy.data.objects[PREFIX+name]; errors=[abs((v-center).length-r) for v in vertices_world(o)]
        mother.append({'id':name,'scale':list(o.scale),'radius_mm':r,'max_vertex_radius_error_mm':max(errors)})
    surf=[]
    for name,r,z in [('Body_Upper',D['body_radius'],D['body_z']),('Body_Lower',D['body_radius'],D['body_z']),('Head_Front',D['head_radius'],D['head_z']),('Head_Rear',D['head_radius'],D['head_z'])]:
        a=solids[name]; center=np.array([0,0,z]); rel=a.v-center;sh=P['shape']['variants'][P['shape']['selected']];rel=rel.copy();
        if name.startswith('Body'):
            u=rel[:,2]/r;rel[:,0]/=1+sh['shoulder_bias']*u;rel[:,1]/=(1+sh['shoulder_bias']*u)*sh['depth_scale']
        dist=np.linalg.norm(rel,axis=1); err=np.abs(dist-r); sampled=err<.12; tri=a.f[np.all(sampled[a.f],axis=1)]; tv=a.v[tri]; mid=tv.mean(axis=1)-center;
        if name.startswith('Body'):
            u=mid[:,2]/r;mid[:,0]/=1+sh['shoulder_bias']*u;mid[:,1]/=(1+sh['shoulder_bias']*u)*sh['depth_scale']
        normals=np.cross(tv[:,1]-tv[:,0],tv[:,2]-tv[:,0]); normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-15); radial=mid/np.linalg.norm(mid,axis=1)[:,None]; radial_faces=np.abs(np.einsum('ij,ij->i',normals,radial))>.998; sag=r-np.linalg.norm(mid[radial_faces],axis=1)
        surf.append(dict(id=name,outer_vertices=int(sampled.sum()),max_vertex_sphere_error_mm=float(err[sampled].max()),max_triangle_centroid_sag_mm=float(sag.max())))
    check('declared_mothers_and_sculpted_surface','PASS' if all(v['max_vertex_radius_error_mm']<.001 for v in mother) and max(v['max_triangle_centroid_sag_mm'] for v in surf)<.13 else 'FAIL','原始母球保留；实际外壳按声明卵形公式逆变换检查',{'mothers':mother,'outer_surface_samples':surf},'Original mothers remain true spheres. For B, body XY warping is explicitly inverted before radial comparisons. Local cuts/rims excluded; this is not a claim the sculpted body remains spherical.')
    belly=solids['Body_Lower'].lo[2]; tirez={k:float(a.lo[2]) for k,a in solids.items() if k.startswith('Tire_')}; other=min(float(a.lo[2]) for k,a in solids.items() if not k.startswith('Tire_'))
    check('ground_contacts','PASS' if abs(belly-P['ground_clearance_mm'])<.05 and max(abs(v) for v in tirez.values())<.05 and other>0 else 'FAIL','腹部离地、两轮接地与其他零件不穿地',{'belly_mm':float(belly),'tire_lowest_z_mm':tirez,'other_lowest_z_mm':other})
    tilts=[]; c=Vector((0,0,D['wheel_z']))
    for deg in range(-15,16):
        tr=Matrix.Translation(c)@Matrix.Rotation(math.radians(-deg),4,'X')@Matrix.Translation(-c)
        mins={k:float(Solid(a.o,a,tr).lo[2]) for k,a in solids.items() if not k.startswith('Tire_')}
        n=min(mins,key=mins.get); tilts.append(dict(body_forward_tilt_deg=deg,lowest_part=n,lowest_z_mm=mins[n],belly_z_mm=mins['Body_Lower']))
    check('body_tilt_geometry','PASS' if min(v['lowest_z_mm'] for v in tilts)>0 else 'FAIL','绕轮轴前后倾斜 ±15°，每 1°',tilts,'Positive body forward tilt is -X rotation. Geometric test only, not control safety range')
    data=[]
    for a in solids.values():
        if a.o.get('validation_proxy'):
            a.o.data.calc_loop_triangles();t=topology(vertices_world(a.o),[tuple(p.vertices) for p in a.o.data.loop_triangles]);t['vendor_tessellation_not_closed']=True
        else:t=topology(a.v,a.f)
        components=a.m.decompose(); t['positive_connected_components']=sum(m.volume()>0.01 for m in components); t['closed_cavity_boundary_components']=sum(m.volume()<-0.01 for m in components); data.append(dict(id=a.name,**t))
    bad=[a for a in data if any(a[k] for k in ['nonmanifold_edges','inconsistent_edges','degenerate_triangles']) or a['signed_volume_mm3']<=0]
    save_json(ROOT/'reports/mesh_topology.json',data)
    nonvendor_bad=[a for a in bad if not solids[a['id']].o.get('validation_proxy')]
    check('mesh_topology','FAIL' if nonvendor_bad else 'BLOCKED' if bad else 'PASS','实际网格拓扑 / 两原厂接插件转换网格问题保留',{'bad':bad,'checked':len(data)},'Actual render meshes checked, never replaced by proxy for topology reporting. Purchased CAD defects do not approve printable meshes.')
    disconnected=[v for v in data if solids[v['id']].o.get('category')=='PRINTABLE' and (v['positive_connected_components']>1 or v['closed_cavity_boundary_components']>0)]
    check('printable_connected_solids','FAIL' if disconnected else 'PASS','候选结构件连通且无未声明封闭内孔',{'disconnected':disconnected},'Manifold boundary components with positive volume counted; negative-volume closed cavity boundaries are not mistaken for floating parts')
    check('exact_self_intersection','NOT_TESTED','Manifold 接受网格不等价于独立、可靠的全部自交证明；未运行精确全三角自交算法')
    # Radial shell thickness rays in uncut areas.
    wall=[]
    def surface_error(point,center,r,off,body):
        q=point-center; rr=r-off
        if body:
            sh=P['shape']['variants'][P['shape']['selected']];u=q.z/rr;q.x/=1+sh['shoulder_bias']*u;q.y/=(1+sh['shoulder_bias']*u)*sh['depth_scale']
        return abs(q.length-rr)
    for name,r,z in [('Body_Upper',D['body_radius'],D['body_z']),('Body_Lower',D['body_radius'],D['body_z']),('Head_Front',D['head_radius'],D['head_z']),('Head_Rear',D['head_radius'],D['head_z'])]:
        a=solids[name]; tree=a.bvh(); center=Vector((0,0,z)); samples=[]
        for el in range(-60,76,15):
            for az in range(0,360,15):
                d=Vector((math.cos(math.radians(el))*math.cos(math.radians(az)),math.cos(math.radians(el))*math.sin(math.radians(az)),math.sin(math.radians(el))))
                hit=tree.ray_cast(center+d*(r+3),-d,r+5)
                if hit[0] is None or surface_error(hit[0],center,r,0,name.startswith('Body'))>.16: continue
                second=tree.ray_cast(hit[0]-d*.01,-d,8)
                if second[0] is not None and surface_error(second[0],center,r,P['shell_thickness_mm'],name.startswith('Body'))<.16: samples.append((second[0]-hit[0]).length)
        wall.append(dict(id=name,count=len(samples),min_sample_mm=min(samples,default=None),max_sample_mm=max(samples,default=None)))
    check('nominal_shell_wall_samples','PASS' if all(v['count'] and v['min_sample_mm']>2.2 for v in wall) else 'FAIL','未截切区域壳厚径向射线抽查',wall,'Paired rays, filtering against declared outer/inner profile equations (including B sculpting); radial sample thickness not a global normal minimum wall proof')
    service_wall=[];tree=solids['Body_Lower'].bvh()
    for sign in [-1,1]:
        for y in [-P['shell_service']['seam_mount_abs_y_mm'],P['shell_service']['seam_mount_abs_y_mm']]:
            d=Vector((-sign,0,0));first=tree.ray_cast(Vector((sign*120,y,body_z_mm(-12))),d,150)
            second=tree.ray_cast(first[0]+d*.001,d,10) if first[0] is not None else (None,)
            service_wall.append({'side':sign,'y_mm':y,'z_mm':body_z_mm(-12),'measured_wall_mm':(second[0]-first[0]).length if second[0] is not None else None})
    check('wheel_pocket_service_wall_samples','PASS' if all(s['measured_wall_mm'] is not None and s['measured_wall_mm']>=P['shell_thickness_mm']-.02 for s in service_wall) else 'FAIL','轮窝附近四处下壳工具沉孔的指定截面余厚',service_wall,'Paired ray intersections with the actual lower-shell mesh at configured seam Y, Z=body_center_z-12; verifies four local ligaments only, not all walls or strength')
    check('global_minimum_wall','NOT_TESTED','孔边、布尔窄区和所有支架的全局最小壁厚尚无可靠全覆盖算法；需切片与实体试样')

def camera_checks(solids):
    c=P['camera']; origin=Vector(c['pupil_from_head_mm'])+Vector((0,0,D['head_z'])); blockers=[a for a in solids.values() if a.name not in ['Camera_Lens','Camera_Window','Face_Protector','Camera_PCB']]
    hits=[]; window_miss=[]; window=solids['Camera_Window'].bvh()
    for ix in range(11):
        for iz in range(9):
            h=(ix/10*2-1)*math.radians(c['assumed_hfov_deg']/2); v=(iz/8*2-1)*math.radians(c['assumed_vfov_deg']/2)
            direction=Vector((math.tan(h),1,math.tan(v))).normalized()
            if window.ray_cast(origin,direction,12)[0] is None: window_miss.append([ix,iz])
            for a in blockers:
                h0=a.bvh().ray_cast(origin,direction,150)
                if h0[0] is not None: hits.append(dict(ray=[ix,iz],blocker=a.name,distance_mm=h0[3]))
    check('camera_nominal_fov','PASS' if not hits and not window_miss else 'FAIL','相机独立开口、假设视场与脸框遮挡',{'hfov_deg':c['assumed_hfov_deg'],'vfov_deg':c['assumed_vfov_deg'],'rays':99,'occlusions':hits,'window_misses':window_miss},'11 x 9 pinhole rays through actual transparent window and opaque triangulated blockers; all head optical components share pitch transform. Window refraction not simulated')
    fixed=[a for a in blockers if a.group not in ['pitch','yaw']]; external_hits=[]
    for yy in range(-60,61,10):
        for pp in range(-20,26,5):
            tr=rigidtr(yy,pp); pos=tr@origin; rot=tr.to_3x3()
            for ix in range(11):
                for iz in range(9):
                    h=(ix/10*2-1)*math.radians(c['assumed_hfov_deg']/2); v=(iz/8*2-1)*math.radians(c['assumed_vfov_deg']/2); ray=rot@Vector((math.tan(h),1,math.tan(v))).normalized()
                    for target in fixed:
                        hit=target.bvh().ray_cast(pos,ray,150)
                        if hit[0] is not None: external_hits.append({'yaw':yy,'pitch':pp,'part':target.name})
    check('camera_fov_body_motion','PASS' if not external_hits else 'FAIL','相机联合姿态视场与固定机身遮挡',{'poses':130,'rays_per_pose':99,'blockages':external_hits},'Ray casts to fixed body meshes; rigid camera/window/front frame relationship also checked in nominal rays')
    check('camera_calibration_reflections','NOT_TESTED','真实镜头视场、透明窗折射、保护片反光和实际外参待选型与标定；无实测舵机反馈时头角为估计')
    check('head_opening_exposure','NOT_TESTED','下护罩按屏幕扫掠让位；极端俯仰开口是否可接受需查看角度渲染并做实体遮光试验，不宣称完全封闭')

def access_checks(solids):
    tol=.01; bad=[]; names=['Battery','Battery_Tray']; removed=['Body_Lower','Body_Upper']+[n for n in solids if n.startswith('Battery_Hanger') or n.startswith('Shell_Screw') or n.startswith('Shell_Insert')]
    for distance in range(0,121,3):
        tr=Matrix.Translation((0,distance,0))
        for n in names:
            a=Solid(solids[n].o,solids[n],tr)
            for k,b in solids.items():
                if k in names+removed: continue
                v=intersect_volume(a,b)
                if v>tol: bad.append(dict(forward_mm=distance,a=n,b=k,volume_mm3=round(v,3)))
    save_json(ROOT/'reports/battery_access.json',dict(failures=bad,travel_mm=120,step_mm=3,removed=removed,prerequisites='DISARM and external support; remove wheel caps/wheels and withdraw axles before removing both body shells. Disconnect pack and release four hangers; pull tray forward +Y. Shell/axle disassembly tool sequence still needs hardware review.'))
    check('battery_extraction','PASS' if not bad else 'FAIL','拆除上下壳、吊杆并断开电池后沿+Y取出',{'failure_count':len(bad),'details':'battery_access.json'},'41 actual solid-mesh translations; connectors/flexible leads not a certified unplugging path')
    toolbad=[]
    for i,(x,y) in enumerate(P['shell_service']['frame_mount_xy_mm']):
        obj=cyl('temporary_tool',(x,y,body_z_mm(-11)),2.5,50); a=Solid(obj)
        for k,b in solids.items():
            if k in ['Body_Lower','Load_Frame','Frame_Screw_'+str(i)]+[n for n in solids if n.startswith('Shell_')]: continue
            v=intersect_volume(a,b)
            if v>tol: toolbad.append(dict(index=i,b=k,volume_mm3=v))
        bpy.data.objects.remove(obj,do_unlink=True)
    check('frame_screwdriver_path','PASS' if not toolbad else 'FAIL','下壳移除后的四处框架螺丝刀杆路径',{'radius_mm':2.5,'length_mm':50,'failures':toolbad},'Actual tool cylinder / triangle-solid volumes; full hand and tool handle not included')
    check('all_fasteners_assembly','NOT_TESTED','其余紧固件长度、嵌件热压头、工具手柄与完整逐件装配路径尚待阶段 B；当前候选孔仅供试打')
    check('real_hardware_fit','BLOCKED','只验证阶段 A 包络；保留共享契约中硬件候选的适配失败。最新型号与包络见 contracts/mechanical_interfaces.json；真实轮驱、屏幕、相机、舵机和完整连接器仍需阶段 B 回写，不能靠外观调整宣称已适配')
    # Visible routing reservations tested explicitly without treating cable endpoints as rigid collisions.
    routing=[o for o in bpy.context.scene.objects if o.get('role')=='routing']; conflicts=[]
    for o in routing:
        a=Solid(o)
        for k,b in solids.items():
            v=intersect_volume(a,b)
            if v>.1: conflicts.append(dict(route=a.name,part=k,volume_mm3=round(v,2)))
    save_json(ROOT/'reports/routing_review.json',{'static_overlaps':conflicts,'meaning':'Endpoints and clip pass-through require cable-specific interpretation; no blanket clearance PASS','dynamic':'NOT_TESTED: actual cable stiffness, flex shape, bend radius and connector strain across all poses'})
    check('cable_service_loops','NOT_TESTED','已建服务环、线束路径和约束点；实际柔性扫掠与连接器受力未验证',{'static_review':'routing_review.json','review_pairs':len(conflicts)})
    check('hard_stop_contact_angles','NOT_TESTED','有限角度限位件已布置；准确触点角度、强度与舵机失控冲击需专门验证，不能用软件限角代替')
    check('power_interface_operations','NOT_TESTED','已布置 USB-C、按钮、电源开关与插头/手指包络；实物插拔、开关急停可达性、线缆拉力待阶段 B')

def volume_moments(s):
    tris=s.v[s.f]; a,b,c=tris[:,0],tris[:,1],tris[:,2]; vol=np.einsum('ij,ij->i',a,np.cross(b,c))/6; V=float(vol.sum()); sums=a+b+c; first=np.sum(vol[:,None]*sums/4,axis=0)
    Q=np.zeros((3,3))
    for j in range(3):
        for k in range(3): Q[j,k]=np.sum(vol*(a[:,j]*a[:,k]+b[:,j]*b[:,k]+c[:,j]*c[:,k]+sums[:,j]*sums[:,k])/20)
    return V,first/V,Q

def mass_checks(solids):
    entries=[]
    for n,a in solids.items():
        V,com,Q=volume_moments(a); cat=a.o.get('category'); mat=a.o.data.materials[0].name.removeprefix(PREFIX) if a.o.data.materials else ''
        if cat=='PRINTABLE': mass=V*.00124*(.98 if n in ['Head_Front','Head_Rear','Body_Upper','Body_Lower','Head_Lower_Guard'] else .65); assumption='PLA 1.24 g/cm3; shell effective fill 98%, bracket 65% incl perimeters'
        elif n.startswith('Drive_Motor'): mass=19.5; assumption='S288 vendor19.5g for full motor; separate output references mass accounted below'
        elif n=='Battery': mass=190; assumption='190g ASSUMED finished3S2200-2600mAh pack; no capacity/runtime claim'
        elif n in ['Yaw_Servo','Pitch_Servo']: mass=13.2; assumption='SCS0009 vendor13.2+/-1g; actual revision pending'
        elif n=='Display_Module': mass=9; assumption='9g assumed screen plus touch layer'
        elif n=='Display_PCB': mass=14; assumption='14g ASSUMED complete vendor-CAD LCD module; vendor mass/physical weighing missing'
        elif n=='CAM_Mainboard': mass=18; assumption='18g assumed CAM board including integrated audio/microphones, not measured'
        elif n.startswith('S288_Output') or n.endswith('Output'): mass=.1; assumption='Visual subcomponent; main servo mass includes output,0.1g bookkeeping reserve'
        elif n=='Camera_PCB': mass=5; assumption='5 g camera assumption'
        elif n.startswith('MCU_'): mass=18; assumption='18g assumed STM32 carrier'
        elif n=='Speaker': mass=20; assumption='20g assumed4ohm3W speaker'
        elif n.startswith('Tire_'): mass=V*.00115*.7; assumption='Rubber 1.15 g/cm3, effective 70% solid'
        else:
            density=.0045 if mat=='metal' else .00185 if mat=='pcb' else .0012
            mass=V*density; assumption='Uniform effective '+str(density*1000)+' g/cm3 for '+mat+' reference envelope'
        rho=mass/V; I=(np.eye(3)*np.trace(Q)-Q)*rho
        entries.append(dict(id=n,group=a.group,mass_g=mass,com_mm=com.tolist(),raw_inertia_g_mm2=I.tolist(),assumption=assumption))
    totals={}
    for label,groups in [('whole_robot',None),('head_pitch',['pitch']),('head_yaw_total',['pitch','yaw'])]:
        selected=[v for v in entries if groups is None or v['group'] in groups]; mass=sum(v['mass_g'] for v in selected); com=sum(np.array(v['com_mm'])*v['mass_g'] for v in selected)/mass
        I=sum(np.array(v['raw_inertia_g_mm2']) for v in selected); Icom=I-mass*(np.dot(com,com)*np.eye(3)-np.outer(com,com)); pivot=np.array([0,0,D['head_z']]); dp=com-pivot; Ip=Icom+mass*(np.dot(dp,dp)*np.eye(3)-np.outer(dp,dp))
        totals[label]={'mass_g_rounded':round(mass/5)*5,'center_mm_rounded':np.round(com,1).tolist(),'inertia_at_COM_kg_m2':(Icom*1e-9).round(7).tolist(),'inertia_at_head_joint_kg_m2':(Ip*1e-9).round(7).tolist(),'estimated_mass_uncertainty_percent':35}
    # COM over the entire sampled head workspace, relative to body in a cradle.
    xy=[]
    for yaw in range(-60,61,10):
        for pitch in range(-20,26,5):
            total=np.zeros(3); mass=0
            for v in entries:
                p=Vector(v['com_mm']); p=rigidtr(yaw,pitch if v['group']=='pitch' else 0)@p if v['group'] in ['pitch','yaw'] else p
                total+=np.array(p)*v['mass_g']; mass+=v['mass_g']
            xy.append((total/mass)[:2].tolist())
    dockmargin=min(min(32-abs(p[0]),30-abs(p[1])) for p in xy)
    save_json(ROOT/'reports/mass_budget.json',{'status':'ASSUMED','pitch_gravity_torque_peak_Nm_estimate':round(totals['head_pitch']['mass_g_rounded']/1000*9.81*float(np.linalg.norm(np.array(totals['head_pitch']['center_mm_rounded'])[1:]-np.array([0,D['head_z']])))/1000,3),'density_and_component_mass_assumptions':entries,'totals':totals,'uncertainty':'At least +/-35%; uniform density approximation; screws/connector internals/cable actual masses incomplete. Not measured. Mass placement must be revisited in control model.','dock':{'contact_polygon_xy_mm':P['dock']['contact_xy_mm'],'head_grid_COM_xy_mm':xy,'min_nominal_margin_mm':dockmargin}})
    check('mass_inertia_estimates','PASS','已输出有假设的质量与惯量估算（不是载荷验收）',totals,'Signed tetrahedron volume, first and second moments. Uniform effective material densities and separate unselected hardware mass assumptions')
    check('head_torque_and_balance','NOT_TESTED','舵机扭矩、头部加速载荷、支架强度、轴承寿命与实机自平衡尚未验证')
    check('dock_nominal_COM_projection','PASS' if dockmargin>0 else 'FAIL','托架四点名义支撑多边形内的重心投影',{'margin_mm':round(dockmargin,1),'robot_lift_mm':8,'drive_required':'DISARMED / DOCKED_MAINTENANCE; no plugged-in driving'},'Assumed masses and rigid contacts; 130 head poses. Actual compliance, friction, cable pull and tipping require physical tests')
    docksolids=[Solid(o) for o in parts() if o.get('group')=='dock']; lift=Matrix.Translation((0,0,8)); bad=[]; contacts=[]
    for a0 in solids.values():
        a=Solid(a0.o,a0,lift)
        for b in docksolids:
            vol=intersect_volume(a,b)
            if vol>.05: bad.append(dict(robot=a.name,dock=b.name,volume_mm3=vol))
            if a.name=='Body_Lower' and b.name.startswith('Dock_Pad'):
                contacts.append(dict(pad=b.name,nearest_sample_mm=min(a.bvh().find_nearest(Vector(v))[3] for v in b.v)))
    check('dock_mesh_contacts','PASS' if not bad and all(v['nearest_sample_mm']<.2 for v in contacts) else 'FAIL','实际托架网格接触、轮胎离地与实体干涉',{'failed_pairs':bad,'body_pad_contacts':contacts,'tire_floor_gap_mm':8},'Translated assembled robot +8 mm, same meshes; solid intersections and nearest vertex-to-triangle witnesses')
    check('dock_physical_stability','NOT_TESTED','软垫变形、地面摩擦、插线拉力及真实重心必须实测；托架稳定不代表机器人断电可自立')
    check('budget_and_runtime','BLOCKED','1000 元总预算和 60 分钟混合工况续航未验证；未提供完整报价与实测平均功耗')

def v12_checks(solids):
    display=[]; z=D['head_z']+P['display']['z_from_head_mm']; radius=P['display']['active_diameter_mm']/2
    for x in np.linspace(-radius,radius,17):
        for zz in np.linspace(-radius,radius,17):
            if x*x+zz*zz>radius*radius:continue
            origin=Vector((x,49.86,z+zz))
            for name,a in solids.items():
                if name in ['Display_Module','Face_Protector']:continue
                hit=a.bvh().ray_cast(origin,Vector((0,1,0)),40)
                if hit[0] is not None:display.append({'x_mm':float(x),'z_from_display_mm':float(zz),'blocker':name})
    check('display_active_aperture','FAIL' if display else 'PASS','真实45.68mm发光区到观察侧的遮挡检查',{'active_diameter_mm':45.68,'sample_grid':17,'blocked_rays':display},'Orthographic +Y rays from display front; circular active-region samples against every opaque triangle mesh. Clear protector excluded; reflections not simulated.')
    # Catch components that are entirely outside shells; triangle intersection alone misses that case.
    outside=[]; center=np.array([0,0,D['head_z']])
    for n in ['CAM_Mainboard','Camera_PCB','Display_PCB','Pitch_Servo','Pitch_Horn','Pitch_Output']:
        a=solids[n];maximum=float(np.linalg.norm(a.v-center,axis=1).max())
        if maximum>D['head_radius']+.01:outside.append({'part':n,'maximum_radius_mm':maximum})
    check('head_allocations_inside_outer_envelope','FAIL' if outside else 'PASS','头内主板/屏板/相机/舵机位于声明头外形内',{'outside':outside,'head_radius_mm':D['head_radius']},'All vertices of allocated rigid hardware against convex spherical head mother; separate shell/body and joint collisions tested with triangle solids. Not a claim actual hardware matches allocations.')
    axes=[]
    for n in ['L','R']:
        a=solids['Tire_'+n];axes.append({'wheel':n,'center_y_mm':float((a.lo[1]+a.hi[1])/2),'center_z_mm':float((a.lo[2]+a.hi[2])/2),'radius_mm':float((a.hi[2]-a.lo[2])/2)})
    check('wheel_coaxial_geometry','PASS' if all(abs(a['center_y_mm'])<.001 and abs(a['center_z_mm']-a['radius_mm'])<.001 for a in axes) else 'FAIL','双轮同轴且轮轴高度等于实际轮胎半径',axes)
    # USB body approach and smaller male nose are separate, not an unrealistically thin whole plug.
    plug=box('USB_Tool_Approach',(14,-100,body_z_mm(8)),(16,34,10));bad=[];a=Solid(plug)
    for n,b in solids.items():
        v=intersect_volume(a,b)
        if v>.01:bad.append({'part':n,'volume_mm3':v})
    bpy.data.objects.remove(plug,do_unlink=True)
    nose=box('USB_Tool_Nose',(14,-80,body_z_mm(8)),(8.4,6,2.6));a=Solid(nose)
    for n,b in solids.items():
        if n=='USB_Receptacle':continue
        v=intersect_volume(a,b)
        if v>.01:bad.append({'part':n,'volume_mm3':v})
    bpy.data.objects.remove(nose,do_unlink=True)
    check('usb_plug_approach_allocation','PASS' if not bad else 'FAIL','USB插头外壳与前端插拔预留',{'body_mm':[16,34,10],'nose_mm':[8.4,6,2.6],'overlaps':bad},'Rigid assumed plug boxes against actual solids at deepest insertion. Sweeping away along -Y is clear outside the body; vendor plug and retention strain remain unverified.')
    lcd=solids['Display_PCB'];hits=[]
    for name in ['Head_Front','Head_Rear','Display_Frame','Camera_Mount','Camera_PCB','Pitch_Yoke','Pitch_Cradle']:
        vol=intersect_volume(lcd,solids[name])
        if vol>.01:hits.append({'part':name,'intersection_mm3':round(vol,3)})
    info=json.loads((ROOT/'reports/vendor_lcd_import.json').read_text())
    review={'status':'FAIL' if hits else 'BLOCKED','component_id':'display','geometry':'Original113-solid CAD displayed;111 exact tessellated solids plus two connector bounding proxies checked', 'bounds_xyz_mm':bounds(lcd.o),'intersections':hits,'source_sha256':info['source_sha256'],'supersedes':'V1.2-M1 full55x55 rectangle conditional conflict; actual product outline is circular','limits':'No exact all-connector fit claim. PDF9.1ref vs CAD9.35, post centers, purchased revision, mating plugs/FFC and tool access still require confirmation.'}
    save_json(ROOT/'reports/display_outline_review.json',review)
    check('display_full_vendor_outline',review['status'],'原厂LCD外形已回写 / 两接插件精确实体待核',review,'111 original CAD subsolids and two conservative connector proxies against actual structure; zero overlap does not certify the full exact hardware.')
    check('actual_board_antennas_microphones','BLOCKED','CAM37×37板框、32.6孔中心距已核；实际装件厚度、孔径、USB/麦克风/天线坐标与FPC仍缺尺寸')
    from purchased_geometry import audit_purchased_geometry
    audit=audit_purchased_geometry()
    check('purchased_dimension_provenance',audit['integrity_status'],'采购件尺寸来源、原厂CAD比例与未知项标签',audit['integrity_checks'],'Source-file hashes; rigid1:1 CAD transform; original vs imported bounds; no unsupported MEASURED or complete real-fit flags.')
    check('all_purchased_parts_dimensioned','BLOCKED','尚未选定/缺少完整尺寸的采购件保持橙色占位，不能宣称全部按实物建模',{'missing':'purchased_geometry_audit.json','unselected':audit['unselected_component_ids']})



def main():
    quick='--quick' in sys.argv; start=time.time(); bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly']; load_collections()
    for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']: COLS[name].hide_viewport=False
    assembled(); solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
    actual_checks(solids,quick)
    if not quick: geometry_checks(solids); camera_checks(solids); access_checks(solids); mass_checks(solids); v12_checks(solids)
    save_json(ROOT/'reports'/('quick_validation.json' if quick else 'validation.json'),{'status_vocabulary':['PASS','FAIL','NOT_TESTED','BLOCKED','NOT_APPLICABLE'],'elapsed_s':round(time.time()-start,1),'checks':CHECKS,'counts':{s:sum(v['status']==s for v in CHECKS) for s in ['PASS','FAIL','NOT_TESTED','BLOCKED']},'limits':'Geometry evidence only. No manufacturing, cost, electrical, balance or product safety approval.'})
    print('VALIDATION_COMPLETE',flush=True)
if __name__=='__main__': main()
