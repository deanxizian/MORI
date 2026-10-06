"""C5 local wire envelope with an analytical 3D wall offset.

This designs a geometric wall reserve, not a PA12 strength acceptance rule.
The inner cross section encloses all sampled yaw curves plus the original
reaction-stem bore. The outer support planes enclose the 3D offset of the
piecewise-linear inner support function. Final meshes require distance checks.
"""
import numpy as np, math
from common import manifold

def make_neck(pack,data,q):
    params=q["candidate_parameters"]["neck_profile"];c=q["construction"]
    count=params["normal_count"]
    angles=np.arange(count)*2*math.pi/count
    normals=np.c_[np.cos(angles),np.sin(angles)]
    zi=c["inner_z_sampling_mm"]; step=params["support_z_spacing_mm"]
    zs=np.unique(np.r_[zi[0],np.arange(zi[1],zi[2],step),c["special_z_mm"],zi[3]])
    tight=np.full((len(zs),count),params["reference_reaction_bore_r_mm"])
    for i,slot in enumerate(pack['selected']):
        for yaw in range(-60,61,10):
            p=data[f'wire{i}_y{yaw}']
            xy=np.c_[np.interp(zs,p[:,2],p[:,0]),np.interp(zs,p[:,2],p[:,1])]
            a=math.radians(-yaw)
            rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
            tight=np.maximum(tight,xy@rot.T@normals.T+slot['OD_mm']/2+params["inner_wire_nominal_margin_mm"])
    # Fill the unnecessary round bore gradually, inside the existing journal.
    # The lower transition now has 9 mm instead of C4's abrupt 3 mm transition.
    lower=params["lower_transition_z_mm"];upper=params["upper_transition_z_mm"]
    low=np.clip((zs-lower[0])/(lower[1]-lower[0]),0,1);low=low*low*(3-2*low)
    high=np.clip((upper[1]-zs)/(upper[1]-upper[0]),0,1);high=high*high*(3-2*high)
    w=np.minimum(low,high)
    # Do not let the circular blend shrink below any required wire envelope.
    h=np.maximum((1-w[:,None])*q["candidate_parameters"]["journal_inner_r_mm"]+w[:,None]*tight,tight)
    radius=params["offset_radius_mm"] # Includes mesh allowance, not strength qualification.
    zo=c["outer_z_sampling_mm"];oz=np.unique(np.r_[zo[0],np.arange(zo[0],zo[1],step),zo[2]])
    oh=[]
    slopes=np.diff(h,axis=0)/np.diff(zs)[:,None]
    for z in oz:
        ids=np.flatnonzero((zs[:-1]<z+radius)&(zs[1:]>z-radius))
        a=zs[ids,None];b=zs[ids+1,None];m=slopes[ids]
        x=z+radius*m/np.sqrt(1+m*m)
        x=np.maximum(np.maximum(a,z-radius),np.minimum(np.minimum(b,z+radius),x))
        support=h[ids]+m*(x-a)+np.sqrt(np.maximum(0,radius*radius-(x-z)**2))
        oh.append(support.max(axis=0))
    oh=np.asarray(oh)
    def polygon(support):
        delta=2*math.pi/count
        along=(np.roll(support,-1)-support*math.cos(delta))/math.sin(delta)
        tangent=np.c_[-normals[:,1],normals[:,0]]
        return support[:,None]*normals+along[:,None]*tangent
    def loft(zvalues,supports):
        vertices=np.vstack([np.c_[polygon(s),np.full(count,z)] for z,s in zip(zvalues,supports)])
        faces=[]
        for j in range(len(zvalues)-1):
            for k in range(count):
                a=j*count+k;b=j*count+(k+1)%count;c=(j+1)*count+k;d=(j+1)*count+(k+1)%count
                faces.extend([(a,b,c),(b,d,c)])
        for k in range(1,count-1):faces.append((0,k+1,k))
        last=(len(zvalues)-1)*count
        for k in range(1,count-1):faces.append((last,last+k,last+k+1))
        m=manifold.Manifold(manifold.Mesh64(vertices,np.asarray(faces,dtype=np.uint64)))
        assert m.status()==manifold.Error.NoError and m.volume()>0
        return m
    outer=loft(oz,oh);inner=loft(zs,h)
    return outer-inner,outer,inner,params
