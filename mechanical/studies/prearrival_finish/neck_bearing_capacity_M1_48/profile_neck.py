"""Simple closed convex neck; constant centre profile with smooth transitions.

Inner profile is the convex enclosure of the selected finite wire positions
and the original reaction-stem bore. Offset planes form the2.2mm horizontal
wall reserve. This is geometry, not a qualified minimum3Dwall/strength rule.
"""
import numpy as np,math
from build_candidate import manifold

def make_neck(pack,data):
    count=128;angles=np.arange(count)*2*math.pi/count
    normals=np.c_[np.cos(angles),np.sin(angles)]
    tight=np.full(count,7.7)
    for i,slot in enumerate(pack['selected']):
        for yaw in range(-60,61,10):
            p=data[f'wire{i}_y{yaw}'];p=p[(p[:,2]>=160)&(p[:,2]<=174)]
            a=math.radians(-yaw);rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
            xy=p[:,:2]@rot.T
            tight=np.maximum(tight,np.max(xy@normals.T,axis=0)+slot['OD_mm']/2+.38)
    def weight(z):
        if z<=159.2 or z>=171.5:return 0.
        if z<162.2:t=(z-159.2)/3.
        elif z<=167.5:return 1.
        else:t=(171.5-z)/4.
        return t*t*(3-2*t)
    def profile(z,extra=0.):
        w=weight(z);h=(1-w)*12.6+w*tight+extra
        following=np.roll(h,-1);delta=2*math.pi/count
        along=(following-h*math.cos(delta))/math.sin(delta)
        tangent=np.c_[-normals[:,1],normals[:,0]]
        return h[:,None]*normals+along[:,None]*tangent
    def loft(zs,extra):
        rings=[np.c_[profile(z,extra),np.full(count,z)] for z in zs]
        vertices=np.vstack(rings);faces=[]
        for j in range(len(zs)-1):
            for k in range(count):
                a=j*count+k;b=j*count+(k+1)%count;c=(j+1)*count+k;d=(j+1)*count+(k+1)%count
                faces.extend([(a,b,c),(b,d,c)])
        for k in range(1,count-1):faces.append((0,k+1,k))
        last=(len(zs)-1)*count
        for k in range(1,count-1):faces.append((last,last+k,last+k+1))
        m=manifold.Manifold(manifold.Mesh64(vertices,np.asarray(faces,dtype=np.uint64)))
        assert m.status()==manifold.Error.NoError
        if m.volume()<0:m=manifold.Manifold(manifold.Mesh64(vertices,np.asarray(faces,dtype=np.uint64)[:,::-1].copy()))
        assert m.volume()>0
        return m
    zs=np.unique(np.r_[156.5,np.arange(159.2,162.21,.2),162.2,167.5,np.arange(167.5,171.51,.2),171.5,173.6])
    outer=loft(zs,2.2);inner=loft(np.r_[156.4,zs,173.7],0.)
    tube=outer-inner
    params=dict(normal_count=count,neck_z_mm=[156.5,173.6],tight_z_mm=[162.2,167.5],
        lower_transition_z_mm=[159.2,162.2],upper_transition_z_mm=[167.5,171.5],
        inner_support_mm=tight.tolist(),normals=normals.tolist(),inner_wire_nominal_margin_mm=.38,
        horizontal_wall_reserve_mm=2.2,reference_reaction_bore_r_mm=7.7,
        tight_inner_polygon_mm=profile(165).tolist(),tight_outer_polygon_mm=profile(165,2.2).tolist(),
        full_3Dwall_or_strength_qualification=False)
    return tube,outer,inner,params
