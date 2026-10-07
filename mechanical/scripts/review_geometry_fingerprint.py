"""Canonical triangle fingerprints for the bounded publication repair."""
import hashlib, json
from mesh_components import components
def fingerprint(vertices,faces,digits=None):
    rows=[]
    for face in faces:
        points=tuple(tuple(round(float(v),digits) if digits is not None else float(v) for v in vertices[i]) for i in face)
        rows.append(min(points[i:]+points[:i] for i in range(len(points))))
    return hashlib.sha256(json.dumps(sorted(rows),separators=(',',':')).encode()).hexdigest()
def record(vertices,faces):
    groups=components(vertices,faces);main=[faces[i] for i in groups[0]['faces']]
    return {'triangles':len(faces),'exact_sha256':fingerprint(vertices,faces),'rounded_0p0001mm_sha256':fingerprint(vertices,faces,4),'components':len(groups),'main_triangles':len(main),'main_exact_sha256':fingerprint(vertices,main),'bounds_xyz_mm':[[float(min(p[k] for p in vertices)),float(max(p[k] for p in vertices))] for k in range(3)]}
