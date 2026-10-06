"""Recheck suspicious normal rays with the solid kernel and make exact sections."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
data=json.loads((HERE/'baseline_audit.json').read_text());out=[]
for row in data['walls']:
 if not row['under_1mm']:continue
 name=row['id'];s=Solid(bpy.data.objects[PREFIX+name]);tri=s.v[s.f];cent=tri.mean(1);cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norms=cross/np.maximum(np.linalg.norm(cross,axis=1)[:,None],1e-15);rr=[]
 for old,p in row['critical_samples']:
  p=np.array(p);i=int(np.argmin(np.linalg.norm(cent-p,axis=1)));p=cent[i];n=norms[i];start=p-n*.00001;hs=s.m.ray_cast(start.tolist(),(start-n*300).tolist());h=hs[0] if hs else None
  rr.append({'previous_BVH_mm':old,'p':p.tolist(),'normal':n.tolist(),'solid_ray_mm':h.distance*300+.00001 if h else None,'exit_normal_dot':float(np.dot(h.normal,n)) if h else None})
 out.append({'id':name,'rays':rr})
(HERE/'thin_recheck.json').write_text(json.dumps(out,indent=2));print('THIN_RECHECK',[(r['id'],[(round(x['solid_ray_mm'],4),x['p']) for x in r['rays'][:2]]) for r in out],flush=True)
# All sections are actual manifold intersections, not shading artifacts.
specs=[('Drive_Bridge',0,0,(30,39,53,67),'X/Z at Y=0'),('Pitch_Yoke',1,-40,(-9,219,9,236),'Y/Z at X=-40'),('Display_Frame',0,27.54,(-9,249,9,271),'X/Z at Y=27.54'),('Body_Lower',0,56.7,(44,77,61,92),'X/Z at Y=56.7')]
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1300" height="900" viewBox="0 0 1300 900"><rect width="1300" height="900" fill="#f6f7f8"/><g font-family="Arial,sans-serif">']
for j,(name,mode,coord,box,title) in enumerate(specs):
 s=Solid(bpy.data.objects[PREFIX+name]);m=s.m
 if mode==0:section=m.rotate([90,0,0]).slice(coord);polys=[[(x,-z) for x,z in poly] for poly in section.to_polygons()]
 else:section=m.rotate([0,90,90]).slice(-coord);polys=[[(y,z) for y,z in poly] for poly in section.to_polygons()]
 # In mode1 rotate maps world(x,y,z)->(-y,z,x), so swap first sign.
 if mode==1:polys=[[(-a,b) for a,b in poly] for poly in section.to_polygons()]
 x0,z0,x1,z1=box;ox=40+(j%2)*640;oy=55+(j//2)*435;scale=min(570/(x1-x0),355/(z1-z0));path=[]
 region=manifold.CrossSection([list(reversed(p)) for p in polys])^manifold.CrossSection.square([x1-x0,z1-z0]).translate([x0,z0])
 for poly in region.to_polygons():path.append('M '+' L '.join(f'{ox+(a-x0)*scale:.3f},{oy+(z1-b)*scale:.3f}' for a,b in poly)+' Z')
 svg.append(f'<text x="{ox}" y="{oy-15}" font-size="20">{name}: {title}</text><path d="{" ".join(path)}" fill="#789ea8" stroke="#294453" stroke-width="1" fill-rule="evenodd"/>')
 svg.append(f'<text x="{ox}" y="{oy+385}" font-size="15">Exact section; axes mm. Unchanged released geometry.</text>')
svg.append('</g></svg>');(HERE/'thin_sections.svg').write_text(''.join(svg))
