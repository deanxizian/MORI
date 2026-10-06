"""Independent short sliding-guide geometry; no Blender scene or file operations."""
import math
import numpy as np
import manifold3d as manifold

def rounded_rect(lo,hi,radius,segments=12):
    x0,y0=lo;x1,y1=hi;r=radius;points=[]
    for x,y,a in [(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)]:
        points.extend([[x+r*math.cos(math.radians(t)),y+r*math.sin(math.radians(t))] for t in np.linspace(a,a+90,segments+1)])
    return np.array(points)

def loft(sections):
    n=len(sections[0][1]);v=np.vstack([np.c_[p,np.full(n,z)] for z,p in sections]);f=[]
    for i in range(1,n-1):f.append([0,i+1,i]);f.append([(len(sections)-1)*n,(len(sections)-1)*n+i,(len(sections)-1)*n+i+1])
    for k in range(len(sections)-1):
        for j in range(n):
            a=k*n+j;b=k*n+(j+1)%n;c=b+n;d=a+n;f.extend([[a,b,c],[a,c,d]])
    result=manifold.Manifold(manifold.Mesh64(v,np.array(f,dtype=np.uint64)))
    assert result.status()==manifold.Error.NoError and result.volume()>0
    return result

def build(root_xmax=-28.9,root_ymax=-4.5,root_top=230.6):
    outer=rounded_rect([-31.75,-13.5],[-24.45,-8.5],.6)
    slab=manifold.CrossSection([outer]).extrude(2.4).translate([0,0,224.3])
    sections=[]
    for z,e in [(224.2,.35),(224.55,0.),(226.45,0.),(226.8,.35)]:
        sections.append((z,rounded_rect([-30.25-e,-12.-e],[-25.95+e,-10.+e],.4+e)))
    window=loft(sections);guide=slab-window
    yz=[[-9.05,225.4],[root_ymax,227.95],[root_ymax,root_top],[-9.05,227.8]]
    root=manifold.CrossSection([yz]).extrude(root_xmax+31.75).transform([[0,0,1,-31.75],[1,0,0,0],[0,1,0,0]])
    result=guide+root
    assert result.status()==manifold.Error.NoError and len(result.decompose())==1
    return result,dict(window_mm=[4.3,2.0],guide_length_mm=2.4,outer_mm=[7.3,5.,2.4],
                       mouth_flare_mm=.25,minimum_nominal_side_wall_mm=1.25,
                       root_x_mm=[-31.75,root_xmax],root_y_mm=[-9.05,root_ymax],root_top_z_mm=root_top,
                       role='Axially sliding guide only; no gripping grooves or tie preload',added_printed_parts=0,added_fasteners=0)
