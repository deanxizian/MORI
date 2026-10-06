"""Conservative connector housing study. Does not edit native PCBs or released CAD."""
import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from native_electronics import board_transform
ROOT=PROJECT

load_collections();assembled();bpy.context.view_layer.update()
bom=json.loads((ROOT/'mechanical/reports/bom.json').read_text())
actual={r['id'] for r in bom if r['group'] not in ('dock','coupon')}
targets={n:Solid(bpy.data.objects[PREFIX+n]) for n in actual if bpy.data.objects.get(PREFIX+n) and bpy.data.objects[PREFIX+n].type=='MESH'}
inventory=json.loads((ROOT/'mechanical/sources/populated_P5/inventory.json').read_text())
rows=[]; ignored=[]
for kind,board in inventory['boards'].items():
    c=json.loads((ROOT/P['native_electronics']['boards'][kind]['mesh']).read_text()); r,t=board_transform(kind,c)
    objname=P['native_electronics']['boards'][kind]['object']
    components={a['reference']:a for a in c['components']}
    for fp in board['footprints']:
        if fp['dnp'] or not fp['reference'].startswith('J'):continue
        ref=fp['reference'];foot=fp['footprint']; comp=components.get(ref)
        if comp is None:continue
        import re
        bb=np.array(comp['bounds_xyz_mm']); vertical=np.array([0.,0.,1. if fp['side']=='F' else -1.])
        pad0=np.array([*fp['pads'][0]['xy_mm'],0.]);pad1=np.array([*fp['pads'][-1]['xy_mm'],0.]);pad0[1]*=-1;pad1[1]*=-1
        xaxis=(pad1-pad0)/np.linalg.norm(pad1-pad0);yaxis=np.cross(vertical,xaxis)
        orientation=np.column_stack((xaxis,yaxis,vertical)); mating_axis=vertical
        method='DOCUMENTED_OUTER_HOUSING_ENVELOPE';source='JST_PH.pdf'
        if 'JST_PH_B' in foot or 'JST_XH_B' in foot:
            n=int(re.search(r'_B(\d+)B-',foot).group(1));family='PH' if 'JST_PH_' in foot else 'XH'
            pitch,depth,height,housing_height,extra_width,header_height=(2.,4.5,8.,6.85,3.8,6.) if family=='PH' else (2.5,5.7,9.8,7.5,4.8,7.)
            top=float(bb[2,1] if fp['side']=='F' else bb[2,0]); topface=top-vertical[2]*header_height
            center=np.array([bb[0].mean(),bb[1].mean(),topface+vertical[2]*(height-housing_height/2)])
            size=np.array([(n-1)*pitch+extra_width,depth,housing_height])
            mating=('PHR-' if family=='PH' else 'XHP-')+str(n);source='JST_'+family+'.pdf'
        elif 'JST_PH_S' in foot:
            n=int(re.search(r'_S(\d+)B-',foot).group(1));family='PH_SIDE';mating='PHR-'+str(n)
            # Native row lies1.35mm from header back,6.25mm from mating face.
            pinmid=(pad0+pad1)/2; lateral=np.array([bb[0].mean(),bb[1].mean(),0.])-pinmid
            mating_axis=lateral/np.linalg.norm(lateral); thickness_axis=vertical
            orientation=np.column_stack((xaxis,thickness_axis,mating_axis))
            if np.linalg.det(orientation)<0:orientation[:,0]*=-1
            frontprojection=9.6-1.35
            center=pinmid+mating_axis*(frontprojection-6.85/2)
            # Conservatively enclose full4.8mm native header height; PHR actual4.5mm.
            body_outer=bb[2,0] if vertical[2]<0 else bb[2,1]
            center[2]=body_outer-vertical[2]*2.4
            size=np.array([(n-1)*2+3.8,4.8,6.85]);height=4.8
            method='DOCUMENTED_HOUSING_WITH_CONSERVATIVE_NORMAL_BOUNDS'
        elif 'XT30UPB-M' in foot:
            family='XT30';mating='AMASS XT30U-F';source='AMASS_catalog.pdf'
            height=10.7+12.4;size=np.array([10.2,5.6,height])
            top=bb[2,1] if vertical[2]>0 else bb[2,0];topface=top-vertical[2]*10.7
            center=np.array([bb[0].mean(),bb[1].mean(),topface+vertical[2]*height/2])
            method='CONSERVATIVE_FULL_UNENGAGED_PLUG_AND_HEADER_LENGTH; engagement depth unknown'
        else:
            ignored.append({'board':kind,'ref':ref,'footprint':foot,'reason':'Service jumpers require selected shunt and access specification'});continue
        worldcenter=r@center+t;worldrot=r@orientation; axis=r@mating_axis
        m=manifold.Manifold.cube(size.tolist(),True).transform(np.c_[worldrot,worldcenter])
        hits=[]
        for name,target in targets.items():
            if name==objname:continue
            bbm=m.bounding_box()
            if np.all(target.hi>=np.array(bbm[:3])) and np.all(np.array(bbm[3:])>=target.lo):
                vol=max(0,(m^target.m).volume())
                if vol>.01:hits.append({'target':name,'overlap_mm3':round(vol,4)})
        # Other native components on the same board are not automatically excluded.
        for other,oc in components.items():
            if other in [ref,'PCB']:continue
            for so in oc['solids']:
                v=np.array(so['vertices_mm'])@r.T+t;f=np.array(so['triangles'],dtype=np.uint64)
                om=manifold.Manifold(manifold.Mesh64(v,f))
                if om.status()!=manifold.Error.NoError:continue
                bbm=m.bounding_box()
                if np.all(v.max(0)>=np.array(bbm[:3])) and np.all(np.array(bbm[3:])>=v.min(0)):
                    vol=max(0,(m^om).volume())
                    if vol>.01:hits.append({'target':objname+'/'+other,'overlap_mm3':round(vol,4)})
        path_hits=[]
        # Rigid straight insertion/removal sampled in 1mm steps; no wire/hand claim.
        for travel in range(1,13):
            shifted=m.translate((axis*travel).tolist())
            for name,target in targets.items():
                if name==objname:continue
                bbs=shifted.bounding_box()
                if np.all(target.hi>=np.array(bbs[:3])) and np.all(np.array(bbs[3:])>=target.lo):
                    vol=max(0,(shifted^target.m).volume())
                    if vol>.01:path_hits.append({'target':name,'travel_mm':travel,'overlap_mm3':round(vol,3)})
        data=m.to_mesh64();o=mesh('PREARRIVAL_Plug_'+kind+'_'+ref,data.vert_properties[:,:3].tolist(),data.tri_verts.tolist())
        o['category']='PURCHASED_REFERENCE';o['data_status']='ASSUMED' if family=='XT30' else 'VENDOR_DOCUMENTED';o['model_fidelity']=method;o['role']='study';o['group']='body';o['evidence']=source+'; conservative occupied envelope, not manufacturer CAD or measured'
        mat=material('prearrival_plug',(.85,.13,.04) if hits else (.1,.55,.65));o.data.materials.append(mat)
        rows.append({'board':kind,'ref':ref,'mating':mating,'source':'sources/'+source,'method':method,'center_mm':worldcenter.tolist(),'axis':axis.tolist(),'bounds_mm':m.bounding_box(),'housing_xyz_mm':size.tolist(),'mated_height_mm':height,'static_status':'BLOCKED' if hits else 'PASS','overlap_candidates':hits,'insertion_status':'BLOCKED' if path_hits else 'PASS','straight_path_12mm_candidates':path_hits})
        print(kind,ref,len(hits),len(path_hits),flush=True)
report={'revision':P['revision'],'method':'Manufacturer dimensioned housing OBB; conservative separation screening, overlaps require detailed-shape review. Own mating header excluded, other components checked. No PCB moved.', 'sources':{'inventory':hashlib.sha256((ROOT/'mechanical/sources/populated_P5/inventory.json').read_bytes()).hexdigest(),**{n:hashlib.sha256((HERE/'sources'/n).read_bytes()).hexdigest() for n in ['JST_PH.pdf','JST_XH.pdf','AMASS_catalog.pdf']}},'rows':rows,'remaining_connector_types':ignored,'scope':'PH/XH documented rigid housings, conservative XT30 full-length allocation and12mm straight paths; harness bends, fingers, latch tools, USB/FPC and full motion not certified'}
(HERE/'mated_connector_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'mated_connector_review.blend'))
print('MATED_CONNECTORS_COMPLETE',len(rows),flush=True)
