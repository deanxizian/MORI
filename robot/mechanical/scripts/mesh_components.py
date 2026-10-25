"""Connected vertex components, independent of Blender and decimal welding."""
def components(vertices, faces):
    parent=list(range(len(vertices)))
    def root(a):
        while parent[a]!=a:
            parent[a]=parent[parent[a]];a=parent[a]
        return a
    for f in faces:
        for v in f[1:]:parent[root(v)]=root(f[0])
    groups={}
    for i,f in enumerate(faces):groups.setdefault(root(f[0]),[]).append(i)
    result=[]
    for ids in groups.values():
        vs=sorted({v for i in ids for v in faces[i]})
        # Shift the volume origin near the component to avoid cancellation.
        origin=vertices[vs[0]];volume=0.
        for i in ids:
            face=faces[i]
            for j in range(1,len(face)-1):
                a,b,c=[[vertices[v][k]-origin[k] for k in range(3)] for v in (face[0],face[j],face[j+1])]
                volume+=sum(a[k]*(b[(k+1)%3]*c[(k+2)%3]-b[(k+2)%3]*c[(k+1)%3]) for k in range(3))/6
        result.append({'faces':ids,'vertices':vs,'volume_mm3_abs':abs(volume),'bounds_xyz_mm':[[min(vertices[v][k] for v in vs),max(vertices[v][k] for v in vs)] for k in range(3)]})
    return sorted(result,key=lambda x:len(x['faces']),reverse=True)
