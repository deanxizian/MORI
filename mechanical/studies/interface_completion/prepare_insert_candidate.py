"""Isolated insert candidate, preserving the released assembly and native PCBs."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from layout_cleanup import mm_mesh
from structural_simplification import hardware
from purchased_geometry import remove_generated
from monocoque_structure import obj,source_build
from render import camera
load_collections()
for c in bpy.data.collections:
    if c.get('mori_owner')==OWNER:c.hide_viewport=False
assembled();source_build().materials();bpy.context.view_layer.update()
audit=json.loads((HERE/'baseline_audit.json').read_text());rows=[]
fasteners={r['id']:r for r in json.loads((HERE/'fastener_current.json').read_text())}
probes={r['id']:r for r in json.loads((HERE/'seat_probes.json').read_text())}
baseline={o.name.removeprefix(PREFIX):Solid(o).m for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}

def axial_solid(r,h,mid,axis):
    tr=Matrix.Translation(Vector(mid))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
    return manifold.Manifold.cylinder(h,r,r,96,center=True).transform(np.array(tr)[:3,:])

def fastener_axis(name):
    s=Solid(obj(name));tri=s.v[s.f];cr=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cr,axis=1)/2;ns=cr/np.maximum(2*ar[:,None],1e-12);groups={}
    for n,a in zip(ns,ar):
        if n[np.argmax(abs(n))]<0:n=-n
        k=tuple(np.round(n,4));groups[k]=groups.get(k,0)+a
    axis=np.array(max(groups,key=groups.get));axis/=np.linalg.norm(axis);mid=s.v.mean(0)
    d=(s.v-mid)@axis;r=np.linalg.norm(s.v-mid-d[:,None]*axis,axis=1)
    sign=1 if d[r>r.max()*.96].mean()>(d.min()+d.max())/2 else -1
    return axis*sign

def replace_solid(o,m):
    old=(o.get('category'),o.get('label_zh'),o.get('group'));temp=mm_mesh('candidate_mesh',m.simplify(.0005))
    o.data=temp.data.copy();o.matrix_world=Matrix.Identity(4);SOLIDS.pop(o.name,None);bpy.data.objects.remove(temp,do_unlink=True)
    o['interface_candidate']='NOT_ADOPTED; insert catalogue + local mounting review'

for a in audit['inserts']:
    name=a['id'];host=obj(a['screen']['host']);screw=name.replace('Insert','Screw');axis=fastener_axis(screw)
    oldmid=np.array(a['center_mm']);length=4.0 if name.startswith(('Frame_','Shell_')) else 3.0
    od=4.6 if length==4.0 and name.startswith(('Frame_','Shell_')) else 3.6
    pilot=4.05 if od==4.6 else 3.25
    entry_distance=float(np.median([v[0] for v in probes[name]['host_ends'] if v[0] is not None]));entry=oldmid+axis*entry_distance;mid=entry-axis*(length/2+.2)
    hm=Solid(host).m;oldhm=hm
    if name.startswith('Head_Seam'):
        # Paired seam relocation is a separate user-review proposal.
        # Keep the old released scene untouched; candidate fills old local bore
        # only inside the spherical front/rear shell and seam sleeve.
        sign=1 if oldmid[0]>0 else -1
        b=source_build();ho=b.sphere('candidate_exact_mother',(0,0,D['head_z']),D['head_radius']);mother=Solid(ho).m;bpy.data.objects.remove(ho,do_unlink=True)
        hi=b.sphere('candidate_exact_inner',(0,0,D['head_z']),D['head_radius']-P['shell_thickness_mm']);inner=Solid(hi).m;bpy.data.objects.remove(hi,do_unlink=True)
        shell=mother-inner
        for hn,ycen,dep in [('Head_Front',3,5.4),('Head_Rear',-8,15.4)]:
            part=obj(hn);pm=Solid(part).m
            oldlug=axial_solid(4.2,dep,[sign*43,ycen,D['head_z']+37],[0,1,0])^mother
            oldbore=axial_solid(2.5,60,[sign*43,-10,D['head_z']+37],[0,1,0])
            half=manifold.Manifold.cube([200,100,200],True).translate([0,50.3 if hn=='Head_Front' else -50.3,D['head_z']])
            # Restore original shell around old counterbore and remove only old boss interior.
            pm=(pm+(oldbore^shell^half))-(oldlug^inner)
            newlug=axial_solid(4.2,dep,[sign*41,ycen,D['head_z']+39],[0,1,0])^mother
            pm=pm+newlug
            if hn=='Head_Rear':
                pm=pm-axial_solid(1.15,30,[sign*41,-10,D['head_z']+39],[0,1,0])
                pm=pm-axial_solid(2.4,45,[sign*41,-35,D['head_z']+39],[0,1,0])
            else:
                q=P['readiness_completion']['head_shell'];xx,yy=head_shell_mount_xy_mm(sign);seat=D['head_z']+q['head_seat_z_from_head_mm']
                pm=pm-axial_solid(q['clearance_radius_mm'],60,[xx,yy,D['head_z']+47],[0,0,1])
                pm=pm-axial_solid(q['counterbore_radius_mm'],50,[xx,yy,seat+25],[0,0,1])
            replace_solid(part,pm)
        obj(screw).location.x-=sign*2;obj(screw).location.z+=2;SOLIDS.pop(obj(screw).name,None)
        entry[0]=sign*41;entry[1]=.3;entry[2]+=2;mid=entry-axis*(length/2+.2);hm=Solid(host).m
    # Fill the previous pilot, then cut exactly the chosen catalogue bore.
    # A square short seat is widened only when the existing wall fails.
    depth=4.4 if name.startswith('Head_Cradle') else length+1.2
    outer_depth=entry_distance+float(np.median([v[1] for v in probes[name]['host_ends'] if v[1] is not None]))
    fill_depth=min(depth+1.5,outer_depth-.05)
    if a['status']=='FAIL' and not name.startswith('Head_Seam'):
        # Preserve each existing seating plane. Extension is toward the host.
        width=6.0
        tr=Matrix.Translation(Vector(entry-axis*depth/2))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
        seat=manifold.Manifold.cube([width,width,depth],True) if name.startswith(('CAM','Rear_Interface')) else manifold.Manifold.cylinder(depth,width/2,width/2,96,center=True)
        hm=hm+seat.transform(np.array(tr)[:3,:])
    else:
        # Fill only the existing bore neighbourhood, retaining the host outline.
        pass
    # Seal the obsolete pilot bottom before cutting the new blind hole.
    hm=hm+axial_solid(pilot/2+.2,fill_depth,entry-axis*fill_depth/2,axis)
    if name.startswith('Frame_'):
        hm=hm+axial_solid(4.0,.6,entry-axis*6.25,axis)
    hm=hm-axial_solid(pilot/2,depth+.02,entry-axis*(depth-.02)/2,axis)
    replace_solid(host,hm)
    remove_generated(name)
    m=axial_solid(od/2,length,mid,axis)-axial_solid(1 if od==3.6 else 1.5,length+.1,mid,axis)
    ins=mm_mesh(name,m);hardware(ins,('FINE SL-M2×3' if od==3.6 else 'FINE SL-M3×4')+' / 选型候选',host.get('group'))
    ins['data_status']='VENDOR_DOCUMENTED';ins['model_fidelity']='DOCUMENTED_MAXIMUM_OUTER_ENVELOPE; knurl shape not modeled';ins['source_url']='https://www.finesz.com/shk.php'
    rows.append({'id':name,'host':host.name.removeprefix(PREFIX),'screw':screw,'entry_mm':entry.tolist(),'outward':axis.tolist(),'insert_center_mm':mid.tolist(),'length_mm':length,'OD_mm':od,'pilot_mm':pilot,'pilot_depth_mm':depth,'seat_changed':a['status']=='FAIL','head_seam_move_pending':name.startswith('Head_Seam')})
    if od==3.6:
        f=fasteners[screw];face=np.array(f['tool_start_mm'])-axis*f['nominal_head_height_mm']
        if name.startswith('Carrier_'):face[2]=122.6
        sl=4 if name.startswith('Head_Buck_') else 5 if name.startswith(('CAM_','Carrier_','Power_Board_','Rear_Interface_','Speaker_','Wheel_Buck_')) else round(f['nominal_shank_length_mm'])
        if name.startswith('Head_Seam'):face[0]=entry[0];face[2]+=2
        sm=axial_solid(1.0,sl,face-axis*sl/2,axis)+axial_solid(1.75,1.4,face+axis*.7,axis)
        bolt=obj(screw);replace_solid(bolt,sm);bolt['label_zh']='GB/T823 M2×'+str(sl)+' / 选型候选';bolt['data_status']='VENDOR_DOCUMENTED';bolt['model_fidelity']='DIMENSIONED_ENVELOPE_WITHOUT_THREAD_HELIX';bolt['source_url']='https://www.wqjgj.cn/product/luoding/shizicao/2158.html'
        rows[-1].update(screw_length_mm=sl,screw_head_bearing_mm=face.tolist(),head_diameter_mm=3.5,head_height_mm=1.4)

bpy.context.view_layer.update();targets={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
collisions=[]
changed={r['host'] for r in rows}|{'Head_Rear'}
for name in sorted(changed):
    old=manifold.Manifold() # Additive region compared with immutable released mesh.
    for other,s in targets.items():
        if other==name or 'Insert' in other:continue
        h=targets[name]
        if np.any(h.hi<s.lo) or np.any(s.hi<h.lo):continue
        v=max(0,(h.m^s.m).volume())
        if v>.02:
            before=max(0,(baseline[name]^baseline[other]).volume()) if name in baseline and other in baseline else 0
            collisions.append({'host':name,'other':other,'overlap_mm3':v,'baseline_overlap_mm3':before,'new_volume_mm3':v-before})
(HERE/'insert_candidate.json').write_text(json.dumps({'status':'CANDIDATE_NOT_ADOPTED','rows':rows,'collision_candidates':collisions,'limits':'Current whole-solid overlaps require comparison with intended contacts. Geometry not released.'},ensure_ascii=False,indent=2))
# Exact geometry section for the hole move review; independent from rendered shading.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="500"><rect width="1000" height="500" fill="#f4f6f8"/><g font-family="Arial,sans-serif"><text x="35" y="38" font-size="23">Head seam: paired hole move proposal (mm)</text>']
for j,(title,m) in enumerate([('M1.41',baseline['Head_Front']),('Candidate',targets['Head_Front'].m)]):
    ox=40+j*490
    svg.append(f'<text x="{ox}" y="75" font-size="20">{title}</text>')
    section=m.rotate([90,0,0]).slice(2.15)
    region=manifold.CrossSection.square([21,27]).translate([33,-272]);section=section^region
    polygons=section.to_polygons();path=[]
    for poly in polygons:
        pp=[(ox+(x-33)*18,95+(zz+272)*12) for x,zz in poly]
        path.append('M '+' L '.join(f'{x:.3f},{y:.3f}' for x,y in pp)+' Z')
    svg.append(f'<path d="{" ".join(path)}" fill="#7197a1" fill-rule="evenodd" stroke="#243e4a" stroke-width="1"/>')
    xx,zz=(43,259) if j==0 else (41,261);px=ox+(xx-33)*18;py=95+(272-zz)*12
    svg.append(f'<circle cx="{px}" cy="{py}" r="5" fill="#cf563e"/><text x="{ox}" y="445" font-size="17">X={xx}; Z={zz}. Section Y=2.15</text>')
svg.append('<text x="40" y="480" font-size="17">Both front insert and rear screw/sleeve move 2 mm inward + 2 mm upward. No extra part.</text></g></svg>')
(HERE/'seam_comparison.svg').write_text(''.join(svg))
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'insert_candidate.blend'))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.render.resolution_x=1000;sc.render.resolution_y=800;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for mode,visible,loc,target,scale in [
 ('seam',{'Head_Front','Head_Rear','Head_Seam_Insert_-1','Head_Seam_Insert_1','Head_Seam_Screw_-1','Head_Seam_Screw_1'},(130,-180,330),(0,0,251),105),
 ('CAM',{'Pitch_Cradle','CAM_Mainboard'}|{n for n in targets if n.startswith('CAM_Mount')},(90,80,280),(0,-23,238),63)]:
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
    camera('insert_candidate_'+mode,loc,target,scale);sc.render.filepath=str(HERE/('insert_'+mode+'.png'));bpy.ops.render.render(write_still=True)
print('INSERT_CANDIDATE_COMPLETE',len(rows),'overlap candidates',len(collisions),flush=True)
