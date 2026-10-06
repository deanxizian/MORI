"""Executed mesh-based checks; no screenshot or bbox-only clearance claims.
BVH triangles + ray parity and sampled interior witnesses. Limitations are explicit.
"""
import sys, math, itertools, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from mathutils.bvhtree import BVHTree
from export import topology, read_stl

CHECKS=[]; START=time.time(); TOL=P['validation']['numeric_tolerance_mm']

def check(id,status,summary,measurement=None,method=None):
    item=dict(id=id,status=status,summary=summary)
    if measurement is not None: item['measurement']=measurement
    if method: item['method']=method
    CHECKS.append(item); print('MORI CHECK',id,status,flush=True)

class Solid:
    def __init__(self,o,transform=None):
        self.name=o.name.removeprefix(PREFIX); self.o=o; self.v=vertices_world(o)
        if transform: self.v=[transform@v for v in self.v]
        o.data.calc_loop_triangles(); self.f=[tuple(t.vertices) for t in o.data.loop_triangles]
        self.tree=BVHTree.FromPolygons(self.v,self.f,all_triangles=True,epsilon=0.00001)
        self.bb=[(min(v[i] for v in self.v),max(v[i] for v in self.v)) for i in range(3)]
        self.solid=manifold.Manifold(manifold.Mesh64(np.array([tuple(v) for v in self.v],dtype=np.float64),np.array(self.f,dtype=np.uint64)))
        if self.solid.status()!=manifold.Error.NoError: raise ValueError(f'Invalid solid {self.name}: {self.solid.status()}')

def boxes_overlap(a,b): return all(a.bb[i][1]>=b.bb[i][0]-1e-4 and b.bb[i][1]>=a.bb[i][0]-1e-4 for i in range(3))

def point_inside(s,p,tolerance=TOL):
    if any(p[i]<s.bb[i][0]-tolerance or p[i]>s.bb[i][1]+tolerance for i in range(3)): return False,0
    near=s.tree.find_nearest(p)
    if not near[0] or near[3]<=tolerance: return False,0
    votes=0
    for direction in [Vector((1,.37139,.17371)).normalized(),Vector((-.2367,1,.4371)).normalized(),Vector((.1271,-.2117,1)).normalized()]:
        origin=p.copy(); hits=0
        for _ in range(64):
            hit=s.tree.ray_cast(origin,direction,2000)
            if hit[0] is None: break
            hits+=1; origin=hit[0]+direction*.001
        votes+=hits%2
    return votes>=2,near[3]

def interference(a,b,detail=False):
    if not boxes_overlap(a,b): return None
    overlaps=a.tree.overlap(b.tree)
    intersection=a.solid^b.solid; volume=intersection.volume()
    if volume>P['validation']['intersection_volume_tolerance_mm3']:
        mm=intersection.to_mesh64(); vv=[Vector(p[:3]) for p in mm.vert_properties]
        depth=max((max(a.tree.find_nearest(p)[3],b.tree.find_nearest(p)[3]) for p in vv),default=0)
        # Exact nominal touching cylinders may differ by sub-0.02 mm polygon sag.
        is_expected=tuple(sorted([a.name,b.name])) in expected_contacts()
        dims=[max(v[i] for v in vv)-min(v[i] for v in vv) for i in range(3)]
        if not (is_expected and (max(dims)<TOL or min(dims)<TOL or volume<P['validation']['intended_cylindrical_contact_volume_tolerance_mm3'] and depth<TOL)):
            return dict(a=a.name,b=b.name,kind='VOLUME_INTERFERENCE',intersection_volume_mm3=volume,sampled_penetration_lower_bound_mm=round(depth,5),intersection_bounds_mm=dims,overlapping_triangle_pairs=len(overlaps))
        return dict(a=a.name,b=b.name,kind='SURFACE_CONTACT_OR_UNRESOLVED',intersection_volume_mm3=volume,tessellation_contact=True,overlapping_triangle_pairs=len(overlaps))
    if overlaps: return dict(a=a.name,b=b.name,kind='SURFACE_CONTACT_OR_UNRESOLVED',overlapping_triangle_pairs=len(overlaps))
    return None

def expected_contacts():
    pairs={}
    def add(a,b,why): pairs[tuple(sorted([a,b]))]=why
    for s in ['L','R']:
        add('Wheel_Hub_'+s,'Wheel_Cap_'+s,'Hub/cap mating planar face, with separately pending retention')
        for tag in ['Inner','Outer']: add('Independent_Axle_'+s,'Wheel_Bearing_'+s+'_'+tag,'Axle/bearing bore boundary; fit unselected')
        add('Independent_Axle_'+s,'Pulley_'+s+'_Axle','Axle/pulley bore boundary; torque clamp pending')
        add('Motor_'+s+'_PLACEHOLDER','Encoder_'+s+'_PLACEHOLDER','Motor assembly end plane')
        add('Motor_'+s+'_PLACEHOLDER','Motor_Output_'+s,'Motor output end plane')
        add('Motor_Output_'+s,'Pulley_'+s+'_Motor','Motor pulley bore boundary')
        add('Belt_'+s+'_ENVELOPE','Pulley_'+s+'_Motor','Belt/pulley tangent pitch envelope; teeth not represented')
        add('Belt_'+s+'_ENVELOPE','Pulley_'+s+'_Axle','Belt/pulley tangent pitch envelope; teeth not represented')
        add('Load_Frame','Motor_Mount_'+s,'Motor bracket / deck underside seat')
    for name in ['Controller_Mount','Driver_Mount','Imu_Mount','Servo_Mount']:
        add('Load_Frame',name,'Support plate / rigid frame seat')
    for name in ['Controller','Driver','Imu']: add(name+'_Mount',name+'_PLACEHOLDER','PCB envelope / standoff top plane, pattern pending')
    add('Load_Frame','Body_Upper_Shell','Four internal chassis boss seats at z=114; shell threads provisional')
    add('Load_Frame','Head_Bearing_Carrier','Four support post top planes')
    add('Head_Bearing_Carrier','Head_Bearing_Outer_Race','Bearing axial support ledge; retention pending')
    add('Head_Turntable','Head_Bearing_Inner_Race','Spindle / bearing inner bore contact')
    add('Head_Turntable','Head_Front_Shell','Two front head boss seats')
    add('Head_Turntable','Head_Rear_Shell','Two rear head boss seats')
    add('Head_Turntable','Head_Gear_Pitch','Driven gear / spindle bore contact; torque interface pending')
    add('Head_Turntable','Yaw_Stop_Flag','Stop flag top / rotor underside; attachment pending')
    add('Servo_Output','Head_Servo_PLACEHOLDER','Actuator output end plane')
    add('Servo_Output','Servo_Gear_Pitch','Servo gear bore contact')
    add('Servo_Gear_Pitch','Head_Gear_Pitch','Tangent pitch circles only; not meshing gear teeth')
    add('Display_Mount_Frame','Display_PCB_PLACEHOLDER','PCB rear perimeter seat')
    add('Display_Mount_Frame','Head_Front_Shell','Four optical frame boss seat planes')
    for j in range(10):
        for race in ['Inner','Outer']: add('Head_Bearing_Ball_%02d'%j,'Head_Bearing_'+race+'_Race','Schematic rolling contact')
    for i in range(4):
        add('Battery_Hanger_%d'%i,'Load_Frame','Hanger top / deck underside')
        add('Battery_Hanger_%d'%i,'Battery_Tray','Hanger bottom / slotted tray tab plane')
    for s in [-1,1]: add('Yaw_Stop_Fixed_'+str(s),'Head_Bearing_Carrier','Fixed stop base / carrier top plane; attachment pending')
    for family in ['Body','Frame']:
        for i in range(4):
            add(f'{family}_Screw_{i}',f'{family}_Insert_{i}','Nominal screw shank / smooth thread-envelope bore; real thread and insert fit unselected')
            add(f'{family}_Screw_{i}','Body_Lower_Shell' if family=='Body' else 'Load_Frame','Screw head / bearing seat plane')
    return pairs

def sphere_metrics(o,center,radius):
    vs=vertices_world(o); errors=[]; verts=[]
    for v in vs:
        er=abs((v-center).length-radius)
        if er<.12: verts.append(er)
    o.data.calc_loop_triangles()
    for f in o.data.loop_triangles:
        vv=[vs[k] for k in f.vertices]
        if all(abs((v-center).length-radius)<.12 for v in vv):
            # Exclude flat caps/rims if their normals are not radial.
            mid=sum(vv,Vector())/3; n=(vv[1]-vv[0]).cross(vv[2]-vv[0]).normalized()
            if abs(n.dot((mid-center).normalized()))>.996: errors.append(radius-(mid-center).length)
    return dict(outer_vertices_sampled=len(verts),outer_triangles_sampled=len(errors),
                max_vertex_radial_error_mm=max(verts,default=0),max_triangle_centroid_sag_mm=max(errors,default=0))

def static_checks(solids,contacts):
    report=[]; expected=[]; unresolved=[]; failures=[]
    for a,b in itertools.combinations(solids.values(),2):
        hit=interference(a,b)
        if not hit: continue
        key=tuple(sorted([a.name,b.name])); reason=contacts.get(key)
        if reason: hit['intended_contact']=reason
        report.append(hit)
        if hit['kind']=='VOLUME_INTERFERENCE': failures.append(hit)
        elif reason: expected.append(hit)
        else: unresolved.append(hit)
    save_json(ROOT/'reports/interference_pairs.json',dict(volume_interferences=failures,unresolved_surfaces=unresolved,expected_contacts=expected,method='Actual closed triangle solids: Manifold intersection volume + BVH surface contacts. 0.001 mm3 numerical volume threshold; documented intended contacts may have a thin <0.02 mm planar overlap or <0.5 mm3 polygon sag overlap.'))
    check('static_interference_screen','FAIL' if failures else ('NOT_CHECKED' if unresolved else 'PASS'),
          '内部/外部所有实体两两碰撞筛查；未列出的数值接触不自动豁免',dict(volume_count=len(failures),unresolved_count=len(unresolved),expected_count=len(expected),details='interference_pairs.json'),
          '实际闭合三角实体求交体积（含完全包含）+ BVH 表面接触。0.001 mm³ 数值体积阈值；预期接触仅容许报告所列极薄数值层或 <0.5 mm³ 网格弦差接触。')
    motor_fails=[q for q in failures if any(w in q['a']+' '+q['b'] for w in ['Motor_','Encoder_'])]
    check('motor_envelope_installation','FAIL' if motor_fails else 'PASS','名义电机/编码器包络与外壳及支架筛查',dict(conflicts=motor_fails,can_mm=[P['drive']['motor_can_diameter_mm'],P['drive']['motor_can_length_mm']],encoder_length_mm=P['drive']['motor_encoder_length_mm']),
          '已执行三角形碰撞检查；只证明当前包络，绝不表示供应商器件已适配。')
    check('continuous_global_interference_proof','NOT_CHECKED','已做离散姿态的三角实体布尔体积求交；尚未完成所有内部零件在步长之间的连续构型空间证明',method='Manifold 3.5.3 实体交集；保留毫米三角近似与数值阈值。')
    return failures

def motion_checks(solids,contacts):
    yawstep=P['validation']['yaw_step_deg']; lim=P['head_yaw_limit_deg']
    moving=[s for s in solids.values() if s.o.get('group')=='head']; fixed=[s for s in solids.values() if s.o.get('group') not in ['head','wheel_L','wheel_R']]
    # Mechanical stop pads and external shells are included; only documented contact boundaries are classified separately.
    yaw_bad=[]; yaw_surface=[]; samples=list(range(-int(lim),int(lim)+1,yawstep))
    for deg in samples:
        rot=Matrix.Rotation(math.radians(deg),4,'Z')
        for old in moving:
            a=Solid(old.o,rot)
            for b in fixed:
                if not boxes_overlap(a,b): continue
                key=tuple(sorted([a.name,b.name])); hit=interference(a,b)
                if hit and hit['kind']=='VOLUME_INTERFERENCE': yaw_bad.append(dict(angle_deg=deg,**hit))
                elif hit and key not in contacts: yaw_surface.append(dict(angle_deg=deg,**hit))
    check('head_yaw_sweep','FAIL' if yaw_bad else ('NOT_CHECKED' if yaw_surface else 'PASS'),'头部 ±60° 运动包络检查',dict(range_deg=[-lim,lim],step_deg=yawstep,poses=len(samples),volume_conflicts=yaw_bad,unresolved_contacts=yaw_surface),
          '每个角度转换同一套真实三角网格，BVH+内点筛查；包括转盘、外壳、线束预留和固定限位块。步间仍需连续核验。')
    # Rotationally symmetric envelope additionally certifies shell exclusion for all angles.
    check('continuous_external_yaw_envelope','PASS' if P['head_body_motion_gap_mm']>0 and P['body_top_opening_diameter_mm']/2>P['head_joint']['rotor_plate_radius_mm'] else 'FAIL',
          '外部头壳/身体及转盘穿孔的连续角度包络',dict(head_cut_z_mm=D['head_bottom_z'],body_top_z_mm=D['body_top_z'],axial_gap_mm=P['head_body_motion_gap_mm'],rotor_radial_hole_gap_mm=P['body_top_opening_diameter_mm']/2-P['head_joint']['rotor_plate_radius_mm']),
          'Z 截平分离与旋转不变的圆柱孔径界限；只覆盖这些外部接口，不代替全部内部连续运动证明。')
    wstep=P['validation']['wheel_step_deg']; bad=[]; checked=0
    shell=[solids[n] for n in ['Body_Upper_Shell','Body_Lower_Shell','Head_Front_Shell','Head_Rear_Shell']]
    for s,name in [(-1,'L'),(1,'R')]:
        pivot=Vector((s*D['wheel_x'],0,D['wheel_z']))
        for deg in range(0,361,wstep):
            tr=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(deg),4,'X')@Matrix.Translation(-pivot)
            for key in ['Tire_','Wheel_Hub_','Wheel_Cap_']:
                a=Solid(solids[key+name].o,tr)
                for b in shell:
                    hit=interference(a,b)
                    if hit: bad.append(dict(angle_deg=deg,**hit))
            checked+=1
    check('wheel_360_sweep','FAIL' if bad else 'PASS','左右车轮各完整旋转一周',dict(step_deg=wstep,poses_per_side=361//wstep+1,total_side_poses=checked,conflicts=bad),
          '真实轮胎/轮毂/盖三角网格，0…360°（含端点），与静止外壳的 BVH/内点检查。')
    tilt=[]; pivot=Vector((0,0,D['wheel_z']))
    for angle in range(-P['validation']['tilt_limit_deg'],P['validation']['tilt_limit_deg']+1,P['validation']['tilt_step_deg']):
        tr=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-pivot)
        non_tires=[]
        for s in solids.values():
            if s.name.startswith('Tire_'): continue
            zz=min((tr@v).z for v in s.v); non_tires.append((zz,s.name))
        belly=min((tr@v).z for v in solids['Body_Lower_Shell'].v)
        m=min(non_tires); tilt.append(dict(angle_deg=angle,belly_lowest_z_mm=belly,non_tire_lowest_z_mm=m[0],lowest_part=m[1]))
    min_z=min(v['non_tire_lowest_z_mm'] for v in tilt)
    check('body_pitch_plus_minus_15','PASS' if min_z>0 else 'FAIL','绕轮轴前后倾斜 ±15° 的接地风险',dict(samples=tilt,min_non_tire_z_mm=min_z,min_belly_z_mm=min(v['belly_lowest_z_mm'] for v in tilt)),
          'X 轴=(0,0,47.5)；每 1° 变换全部实体网格顶点。仅几何包络；不代表安全运动角或自平衡验证。')

def access_checks(solids):
    st=P['structure']; f=P['fasteners_assumed']
    # Actual cylindrical screwdriver envelopes, tools removed immediately after inspection.
    failures=[]
    for j,(x,y) in enumerate(st['deck_mount_xy_mm']):
        tool=cyl('TEMP_tool',(x,y,110-f['screwdriver_access_length_mm']/2),f['screwdriver_radius_mm'],f['screwdriver_access_length_mm'])
        ts=Solid(tool)
        for b in solids.values():
            if b.name in ['Body_Lower_Shell','Load_Frame',f'Frame_Screw_{j}']: continue
            hit=interference(ts,b)
            if hit and hit['kind']=='VOLUME_INTERFERENCE': failures.append(dict(screw=j,**hit))
        bpy.data.objects.remove(tool,do_unlink=True)
    check('chassis_screwdriver_access','FAIL' if failures else 'PASS','卸下身体下壳后，四个承重框架螺钉的工具操作空间',dict(tool_radius_mm=f['screwdriver_radius_mm'],tool_length_mm=f['screwdriver_access_length_mm'],conflicts=failures),
          '实际圆柱工具包络 vs 三角实体；移除下壳的服务状态。未模拟手掌/完整手柄。')
    check('all_other_screw_and_insert_tools','NOT_CHECKED','头部需分离承重组件并打开后壳；其余嵌件热压头、完整螺丝刀手柄和装配力尚未统一验证',
          dict(assumed_clearance_mm=f['body_screw_clearance_diameter_mm'],assumed_insert_pilot_mm=f['body_insert_pilot_diameter_mm']),
          '已建真实孔和退刀/沉孔；供应商螺钉长度、嵌件外径/深度未选型，不能证明全部工具可达。')
    # Battery tray, battery and strap extracted together downward after removing the lower shell and loosening hanger nuts.
    names=['Battery_PLACEHOLDER','Battery_Tray','Battery_Strap']; other=[s for k,s in solids.items() if k not in names+['Body_Lower_Shell']]
    bad=[]
    for distance in range(0,91,3):
        tr=Matrix.Translation((0,0,-distance))
        for name in names:
            a=Solid(solids[name].o,tr)
            for b in other:
                hit=interference(a,b)
                if hit and hit['kind']=='VOLUME_INTERFERENCE': bad.append(dict(down_mm=distance,**hit))
    check('battery_removal_path','FAIL' if bad else 'PASS','电池、托架、绑带模块向下取出',dict(travel_mm=90,step_mm=3,removed_parts=['Body_Lower_Shell'],prerequisites='Disconnect battery, loosen four hanger fixings',conflicts=bad),
          '每 3 mm 对真实网格做 BVH/内点检查；检查拆出轨迹，不要求穿过顶部小孔。')
    check('complete_assembly_sequence','NOT_CHECKED','已设计可拆壳和分模块装配顺序；未完成全零件、螺钉、线束的连续装配路径证明',
          dict(sequence_document='reports/assembly_and_printing.md'),method='Battery path and four chassis tool paths executed; remaining sequences conditional on selected hardware.')

def thickness_samples(o):
    s=Solid(o); ds=[]; o.data.calc_loop_triangles()
    for t in list(o.data.loop_triangles)[::max(1,len(o.data.loop_triangles)//350)]:
        a,b,c=[s.v[i] for i in t.vertices]; n=(b-a).cross(c-a)
        if n.length<.05: continue
        n.normalize(); center=(a+b+c)/3; hit=s.tree.ray_cast(center-n*.005,-n,200)
        if hit[0] is not None and hit[3]>.05: ds.append(hit[3]+.005)
    return dict(sample_count=len(ds),min_normal_ray_span_mm=min(ds,default=None),median_normal_ray_span_mm=sorted(ds)[len(ds)//2] if ds else None,
                limitation='Normal-ray local spans can include bosses or graze corners; NOT a global minimum-wall proof.')

def shell_radial_thickness(solids):
    result=[]; nominal=P['shell_thickness_mm']
    for name in ['Head_Front_Shell','Head_Rear_Shell','Body_Upper_Shell','Body_Lower_Shell']:
        r=D['head_radius'] if name.startswith('Head') else D['body_radius']
        center=Vector((0,0,D['head_z'] if name.startswith('Head') else D['body_z']))
        vals=[]; tree=solids[name].tree
        for polar in range(15,166,10):
            for az in range(5,360,10):
                th=math.radians(polar); ph=math.radians(az)
                d=Vector((math.sin(th)*math.cos(ph),math.sin(th)*math.sin(ph),math.cos(th)))
                outer=tree.ray_cast(center+d*(r+1),-d,2*r+4)
                if outer[0] is None or abs((outer[0]-center).length-r)>.12: continue
                inner=tree.ray_cast(outer[0]-d*.005,-d,2*r+4)
                if inner[0] is None or abs((inner[0]-center).length-(r-nominal))>.12: continue
                vals.append((outer[0]-inner[0]).length)
        result.append(dict(part=name,samples=len(vals),min_mm=min(vals,default=None),max_mm=max(vals,default=None)))
    ok=all(x['samples']>30 and x['min_mm']>=nominal-.12 and x['max_mm']<=nominal+.12 for x in result)
    check('radial_shell_wall_thickness','PASS' if ok else 'FAIL','未截切、非螺柱区域球壳的真实径向壁厚',dict(nominal_mm=nominal,parts=result),
          '每 10° 球面方向径向射线，依次求外/内表面交点；筛除孔、切面、螺柱；容差 ±0.12 mm，另有完整最薄壁未验证项。')

def exported_self_screen(vertices,faces):
    tree=BVHTree.FromPolygons(vertices,faces,all_triangles=True,epsilon=0)
    pairs=[]
    for a,b in tree.overlap(tree):
        if a>=b or set(faces[a]).intersection(faces[b]): continue
        pairs.append((a,b))
    return dict(nonadjacent_triangle_overlap_pairs=len(pairs),first_pairs=pairs[:20],
                method='BVH self-overlap on re-read STL triangles; same/shared-vertex neighbours excluded; epsilon=0. This is a numerical risk screen, not an exact-arithmetic certificate.')

def main():
    bpy.context.window.scene=bpy.data.scenes['MORI_Assembly']; load_collections(); assembled()
    COLS['DATUMS'].hide_viewport=False; bpy.context.view_layer.update()
    objects=parts(); solids={o.name.removeprefix(PREFIX):Solid(o) for o in objects}
    contacts=expected_contacts(); save_json(ROOT/'reports/expected_contacts.json',[dict(a=a,b=b,reason=r) for (a,b),r in contacts.items()])
    disk_hash=__import__('hashlib').sha256((ROOT/'params.json').read_bytes()).hexdigest()
    check('environment','PASS' if disk_hash==bpy.context.scene.get('params_sha256') else 'FAIL','实际运行 Blender 检查，并核对参数文件与已保存模型摘要',dict(blender=bpy.app.version_string,python=sys.version,params_sha256=bpy.context.scene.get('params_sha256'),current_params_sha256=disk_hash,unit_scale=bpy.context.scene.unit_settings.scale_length,front='-Y'))
    check('reference_image_comparison','NOT_CHECKED','仅收到文字附件，没有参考图片；未进行图片对照')
    mother=[]
    for name,r,center in [('Head_Mother_Sphere',D['head_radius'],Vector((0,0,D['head_z']))),('Body_Mother_Sphere',D['body_radius'],Vector((0,0,D['body_z'])))]:
        o=bpy.data.objects[PREFIX+name]; vv=vertices_world(o); e=max(abs((v-center).length-r) for v in vv)
        mother.append(dict(name=name,diameter_mm=2*r,scale=list(o.scale),max_vertex_radius_error_mm=e))
    check('true_spherical_mothers','PASS' if max(x['max_vertex_radius_error_mm'] for x in mother)<.001 else 'FAIL','头/身原始母球等半径、无非等比缩放',mother,'逐顶点到母球球心的欧氏距离；保留隐藏构造球。')
    sm=[]
    for key,r,center in [('Head_Front_Shell',D['head_radius'],Vector((0,0,D['head_z']))),('Head_Rear_Shell',D['head_radius'],Vector((0,0,D['head_z']))),('Body_Upper_Shell',D['body_radius'],Vector((0,0,D['body_z']))),('Body_Lower_Shell',D['body_radius'],Vector((0,0,D['body_z'])))]:
        sm.append(dict(part=key,**sphere_metrics(solids[key].o,center,r)))
    check('retained_spherical_surfaces','PASS' if max(m['max_triangle_centroid_sag_mm'] for m in sm)<.12 else 'FAIL','未截切外球面的一致性与网格弦差',sm,'筛选半径偏差 <0.12 mm 且法线与径向一致的外表面三角形；检查顶点及面重心，排除切面/孔。')
    bb=[[min(s.bb[i][0] for s in solids.values()),max(s.bb[i][1] for s in solids.values())] for i in range(3)]
    dim=[v[1]-v[0] for v in bb]
    check('measured_dimensions','PASS','装配姿态从实际网格计算尺寸',dict(overall_xyz_mm=dim,bounds_xyz_mm=bb,body_cut_width_mm=max(solids['Body_Upper_Shell'].bb[0][1],solids['Body_Lower_Shell'].bb[0][1])-min(solids['Body_Upper_Shell'].bb[0][0],solids['Body_Lower_Shell'].bb[0][0]),head_mother_diameter_mm=2*D['head_radius'],body_mother_diameter_mm=2*D['body_radius'],tire_diameter_mm=solids['Tire_L'].bb[2][1]-solids['Tire_L'].bb[2][0],track_center_to_center_mm=D['track'],wheel_axle_z_mm=D['wheel_z'],body_center_z_mm=D['body_z'],axle_drop_mm=D['axle_drop'],belly_ground_mm=solids['Body_Lower_Shell'].bb[2][0]),'网格全顶点极值；轮距=两个实际旋转中心间距，非图纸估读。')
    check('body_front_proportion','PASS' if 2*P['body_side_cut_x_mm']>P['head_diameter_mm'] else 'FAIL','侧截后的身体宽度仍大于头部母球直径',dict(cut_width_mm=2*P['body_side_cut_x_mm'],head_mm=P['head_diameter_mm'],ratio=2*P['body_side_cut_x_mm']/P['head_diameter_mm']))
    ground=[s.name for s in solids.values() if abs(s.bb[2][0])<.02]
    underground=[dict(part=s.name,min_z=s.bb[2][0]) for s in solids.values() if s.bb[2][0]<-.02]
    check('two_tire_ground_contacts','PASS' if sorted(ground)==['Tire_L','Tire_R'] and not underground else 'FAIL','只有两个轮胎接地，其余零件不穿地',dict(contacts=ground,underground=underground), '全部实际三角网格顶点最低值；平面 Z=0 的闭合实体接触。')
    gap_results=[]
    for s,name in [(-1,'L'),(1,'R')]:
        for key,z in [('Tire_',D['wheel_z']+36.5),('Wheel_Hub_',D['wheel_z']+25),('Wheel_Cap_',D['wheel_z']+25)]:
            p=Vector((s*P['body_side_cut_x_mm'],0,z)); near=solids[key+name].tree.find_nearest(p)
            bound=(min(v.x for v in solids[key+name].v)-P['body_side_cut_x_mm']) if s==1 else (-P['body_side_cut_x_mm']-max(v.x for v in solids[key+name].v))
            gap_results.append(dict(part=key+name,measured_surface_distance_mm=near[3],separating_plane_lower_bound_mm=bound,witness_shell_mm=list(p),witness_part_mm=list(near[0])))
    check('actual_wheel_shell_gap','PASS' if min(x['measured_surface_distance_mm'] for x in gap_results)>=3-TOL and all(abs(x['measured_surface_distance_mm']-x['separating_plane_lower_bound_mm'])<.02 for x in gap_results) else 'FAIL',
          '轮胎、轮毂及轮毂盖到静止外壳的真实最小间隙',gap_results,
          '三角 BVH 最近点上界 + 侧面分离半空间下界相等，构成最小距离证据；不是单独用包围盒判碰。对轴对称转动保留同一 X 分离界。')
    hp=Vector((0,32,D['body_top_z'])); hn=solids['Head_Rear_Shell'].tree.find_nearest(hp)
    check('head_body_static_gap','PASS' if hn[3]>=P['head_body_motion_gap_mm']-.02 else 'FAIL','头壳下缘与身体顶部间隙',dict(surface_gap_mm=hn[3],body_witness_mm=list(hp),head_witness_mm=list(hn[0])), '真实三角最近点 + Z 截平面分离下界。')
    acts=sorted(o['actuator_id'] for o in objects if 'actuator_id' in o)
    check('exactly_three_actuators','PASS' if acts==['drive_L','drive_R','head_yaw'] else 'FAIL','全机三个执行器',acts)
    static_checks(solids,contacts); motion_checks(solids,contacts); access_checks(solids)
    samples={}
    for o in objects:
        if o.get('export_candidate'): samples[o.name.removeprefix(PREFIX)]=thickness_samples(o)
    save_json(ROOT/'reports/wall_samples.json',samples)
    check('all_part_wall_thickness_sampling','NOT_CHECKED','已执行法线射线筛查，尚不足以确认每个零件的全局最薄壁合格',dict(parts=len(samples),report='wall_samples.json',nominal_shell_mm=P['shell_thickness_mm']),
          '每件最多约350个面，沿内法线射线量距；孔边/锐角近掠射值不能直接判作实体最小壁厚。')
    shell_radial_thickness(solids)
    check('global_min_wall_and_self_intersection','NOT_CHECKED','未完成全部局部最薄壁证明及稳健全三角自交认证；导出前的闭合/法线/退化检查不能替代此项',method='Shell nominal 2.4 mm; optical bezel and trial recesses have separately documented thin regions. Require slicer inspection.')
    manifest=ROOT/'reports/export_manifest.json'
    if manifest.exists():
        ex=json.loads(manifest.read_text()); bad=[p['id'] for p in ex['parts'] if p['status']!='PASS']
        # Re-read delivered bytes here, independently of in-memory mesh checks.
        reread=[]; self_screens=[]; exported_walls={}
        for item in ex['parts']:
            v,fa,no=read_stl(ROOT/item['file']); reread.append(dict(id=item['id'],**topology(v,fa,no)))
            self_screens.append(dict(id=item['id'],**exported_self_screen(v,fa)))
            temp=mesh('TEMP_STL_'+item['id'],v,fa)
            exported_walls[item['id']]=thickness_samples(temp)
            bpy.data.objects.remove(temp,do_unlink=True)
        check('stl_actual_export_geometry','FAIL' if bad else 'PASS','重新读取实际导出 STL，检查闭合、非流形边、法线、退化面与尺寸',dict(candidate_count=ex['candidate_count'],delivered_count=ex['exported_count'],quarantined=bad,details='export_manifest.json',reread=reread),
              '二进制 STL 回读，坐标焊接至 1e-5 mm，边关联计数、绕序、正体积、法向、退化三角，尺寸误差 <0.01 mm。输出数字单位 mm，无 1000 倍缩放。')
        save_json(ROOT/'reports/stl_surface_risk.json',dict(self_intersection_screen=self_screens,wall_samples=exported_walls))
        risk=sum(x['nonadjacent_triangle_overlap_pairs'] for x in self_screens)
        check('stl_self_intersection_risk_screen','PASS' if risk==0 else 'NOT_CHECKED','实际 STL 的非邻接三角自交风险筛查，并在回读实体上再次抽样壁厚',
              dict(candidate_count=len(self_screens),nonadjacent_overlap_pairs=risk,report='stl_surface_risk.json'),
              '实际导出字节回读；BVH 自交筛查排除共顶点邻面。出现候选相交需再定位；采样厚度仍不等于全局最小壁厚证明。')
    else: check('stl_actual_export_geometry','NOT_CHECKED','尚未运行 export.py；请导出后重新运行本检查')
    check('snap_fit','NOT_CHECKED','本轮采用螺钉/嵌件候选接口，没有设计或宣称已验证卡扣；已提供配合孔、嵌件孔和间隙小样')
    check('cable_dynamic_bend_pinch','NOT_CHECKED','4 mm 线束、14 mm 穿轴孔、服务环与导向通道已建模；真实线缆动态弯曲、夹线和疲劳未验证',dict(required_bend_radius_mm=P['head_joint']['wire_bend_radius_requirement_mm'],head_limit_deg=P['head_yaw_limit_deg']))
    check('hardware_interfaces_and_power','NOT_CHECKED','电机/轴承/屏幕/电池/PCB/接插件均待选型；2S 只是布局概念，USB-C 不代表任意电池可直接充电')
    check('mass_com_actuator_load_balance','NOT_CHECKED','没有真实质量、重心、力矩、轴强度、控制器与实物数据；不承诺断电自立、稳定行驶或摔倒自起')
    check('slicing_and_test_print','NOT_CHECKED','未运行切片器/未实际试打；0.3 mm 单边间隙仅为本轮起点，须按材料与打印机校正')
    render_path=ROOT/'reports/render_run.json'
    if render_path.exists():
        rr=json.loads(render_path.read_text()); records=rr.get('records',[])
        expected={'front','side','rear','top','bottom','45_assembled','exploded','internal','engineering','engineering_gap_detail'}
        ok=expected.issubset(set(rr['views'])) and len({r['geometry_digest'] for r in records})==1 and rr.get('params_sha256')==bpy.context.scene.get('params_sha256')
        check('same_geometry_all_views','PASS' if ok else 'NOT_CHECKED','渲染来源与同一几何一致性',dict(views=rr['views'],records=len(records),report='render_run.json'),
              '各视图使用同一场景的相同部件网格摘要，仅变更相机、可见性和装配/爆炸帧；参数摘要与当前模型匹配。')
    idem=ROOT/'reports/rebuild_check.json'
    if idem.exists():
        ii=json.loads(idem.read_text()); check('repeatable_owned_only_rebuild',ii['status'],'同一 Blender 进程重建两次，验证对象不堆积且保留无关对象',ii)
    summary={s:sum(c['status']==s for c in CHECKS) for s in ['PASS','FAIL','NOT_CHECKED']}
    result=dict(project='MORI',blender=bpy.app.version_string,elapsed_seconds=time.time()-START,summary=summary,checks=CHECKS)
    save_json(ROOT/'reports/validation.json',result)
    lines=['# MORI 实际检查记录','',f'Blender {bpy.app.version_string}；前方 -Y；单位 mm；装配帧 1。',
           '',f'PASS {summary["PASS"]} / FAIL {summary["FAIL"]} / NOT_CHECKED {summary["NOT_CHECKED"]}。',
           '', '**这是装配与结构预研，不是生产放行、自平衡或强度合格证。**','']
    for c in CHECKS:
        lines += [f'## {c["status"]} — {c["id"]}',c['summary'],'']
        if c.get('method'): lines += ['方法与范围：'+c['method'],'']
        if c.get('measurement') is not None:
            js=json.dumps(c['measurement'],ensure_ascii=False,indent=2)
            if len(js)>7500: js=js[:7500]+'\n… 完整记录见 validation.json。'
            lines += ['```json',js,'```','']
    (ROOT/'reports/validation.md').write_text('\n'.join(lines))
    print('MORI VALIDATION SUMMARY',summary,flush=True)

if __name__=='__main__': main()
