"""Read-only snapshots for independently checking approved geometry adoption."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
load_collections();assembled()
kind=sys.argv[sys.argv.index('--')+1]
s={'source':bpy.data.filepath,'sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'parts':{}}
for o in parts():
 n=o.name.removeprefix(PREFIX);s['parts'][n]=geometry_record(o)
 if n in P['head_axial_retention']['changed_existing_ids']+P['head_axial_retention']['new_ids']:
  m=Solid(o).m;d=m.to_mesh64();s[n]={'vertices_mm':d.vert_properties[:,:3].tolist(),'triangles':d.tri_verts.tolist()}
save_json(ROOT/'reports'/('head_retention_'+kind+'_reference.json'),s)
print('REFERENCE_SAVED',kind,len(s['parts']))
