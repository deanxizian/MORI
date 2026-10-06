"""Source, rigid-fit and service evidence for populated electronics; not metrology."""
from common import *
from native_electronics import E,source_mesh,board_transform
import hashlib

def validate_native_electronics(solids,Solid,iv,check):
    if not E.get('enabled'):return
    geometry=json.loads((ROOT/'reports/native_electronics_geometry.json').read_text());rows=[]
    inv=json.loads((PROJECT/E['inventory']).read_text())
    for kind,s in E['boards'].items():
        c=source_mesh(s['mesh']);r,t=board_transform(kind,c);a=solids[s['object']];refs=json.loads(a.o['component_reference_index']);by={x['reference']:x for x in refs};errors=[]
        actual=np.asarray([tuple(v) for v in vertices_world(a.o)])
        for comp in c['components']:
            if comp['reference'] not in by:continue
            v=np.concatenate([np.asarray(z['vertices_mm'])@r.T+t for z in comp['solids']]);span=by[comp['reference']]['vertices'];errors.append(float(np.max(np.abs(v-actual[slice(*span)]))))
        pcb=next(z for z in c['components'] if z['reference']=='PCB');bb=pcb['bounds_xyz_mm'];native=inv['boards'][kind]
        rows.append({'board':kind,'native_file':native['source'],'sha256_matches':hashlib.sha256((PROJECT/native['source']).read_bytes()).hexdigest()==native['source_sha256'],
          'finished_pcb_xyz_mm':[b-a for a,b in bb],'components_including_PCB':len(c['components']),'max_import_vertex_error_mm':max(errors),'source_scale_factor':a.o['source_scale_factor'],
          'evidence_counts':{ev:sum(z.get('evidence')==ev for z in c['components']) for ev in sorted(set(z.get('evidence','') for z in c['components']))},'fallbacks':geometry['boards'][kind]['fallbacks']})
    check('native_populated_sources', 'PASS' if all(r['sha256_matches'] and r['max_import_vertex_error_mm']<.001 and r['source_scale_factor']==1 and not r['fallbacks'] for r in rows) else 'FAIL',
      '四块原生PCB按已交接版本导入；板框/孔/装件坐标与来源哈希检查',rows,'Actual imported vertices vs complete source cache, not just AABBs. PCB finished thickness reconstructed from nominal stackup; source STEP substrate height retained in audit. Native placement is not selected-SKU physical metrology.')
    names=[s['object'] for s in E['boards'].values()]+list(E['modules'])+['Power_Switch','USB_Receptacle'];hits=[]
    for i,n in enumerate(names):
        for other,b in solids.items():
            if other==n or other in names[:i]:continue
            v=iv(solids[n],b)
            if v>.02:hits.append({'board':n,'obstacle':other,'volume_mm3':v})
    check('native_populated_rigid_fit','PASS' if not hits else 'FAIL','已建模电路板与总装实体的静态交集检查',{'hits':hits,'includes':names,'volume_threshold_mm3':.02},'Closed source meshes and dimensioned reconstructions, AABB broadphase then Manifold volume including containment. Missing CAM parts, tolerances, mating plugs, heat and flexible cables excluded explicitly.')
    mounts=[]
    for name,s in E['modules'].items():
        mod=geometry['modules'][name];battery=solids['Battery'];gap=solids[name].m.min_gap(battery.m,30);fails=[]
        targets=['Load_Frame',name]+[x for x in E['modules'] if x!=name]+['Body_IMU']
        for site in mod['mount_sites']:
            if not site['fastened']:continue
            x,y=site['world_xy_mm'];n=name+'_Screw_'+str(site['index']);bolt=solids[n]
            tool=cyl('buck_tool_probe',(x,y,float(bolt.lo[2])-15.2),2.1,30);toolsolid=Solid(tool)
            for part in targets:
                v=iv(toolsolid,solids[part])
                if v>.01:fails.append({'site':site['index'],'obstacle':part,'volume_mm3':v,'kind':'driver'})
            bpy.data.objects.remove(tool,do_unlink=True)
            for step in range(21):
                moved=Solid(bolt.o,bolt,Matrix.Translation((0,0,-step)))
                for part in targets:
                    v=iv(moved,solids[part])
                    if v>.01:fails.append({'site':site['index'],'obstacle':part,'volume_mm3':v,'travel_mm':step,'kind':'screw'})
        mounts.append({'module':name,'battery_gap_mm':gap,'mount_sites':mod['mount_sites'],'failures':fails})
    check('buck_underside_mount_access','PASS' if all(not row['failures'] and row['battery_gap_mm']>=3 for row in mounts) else 'FAIL','两块降压板一体短座、底面螺钉工具路径与电池间距',mounts,'Battery/tray and shells removed; shaft diameter4.2x30mm, screw extraction20mm/1mm samples. Heat, hand room and live wiring not tested.')
    rear=geometry['rear_mount'];check('rear_native_switch_reach','BLOCKED','后接口板真实尺寸已适配；原生开关拨柄仍缩在壳内，需要电路布局或拨杆方案调整',rear,'No native component repositioning. USB mouth vs SW stem depth from received geometry; switch stem direction needs sample confirmation.')
    check('populated_mated_thermal_fit','BLOCKED','裸装件检查不包含全部对插线束、CAM完整装件、排母选型和独立充电板',geometry['unresolved'],'Pololu family CAD is an engineering reference; selected voltage/thermal/current behavior not certified. Mated JST/XT30 and USB leads require real SKU and bend/strain-relief review.')
    save_json(ROOT/'reports/native_electronics_validation.json',{'revision':P['revision'],'sources':rows,'rigid_hits':hits,'buck_mounts':mounts,'unknown':geometry['unresolved'],'geometric_status':'PASS' if not hits and all(not x['failures'] and x['battery_gap_mm']>=3 for x in mounts) else 'FAIL','as_built':'NOT_TESTED','manufacture_release':False})
