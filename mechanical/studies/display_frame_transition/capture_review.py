"""Immutable before/accepted solid evidence; never writes the main model."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
from monocoque_structure import obj
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
mode='approved' if '--approved' in sys.argv else 'baseline'
path=Path(__file__).parent/(mode+'_geometry.json')
if path.exists():raise RuntimeError('Evidence already captured; do not overwrite')
d=Solid(obj('Display_Frame')).m.to_mesh64()
rows={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
path.write_text(json.dumps({'revision':P['revision'],'source_blend':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'mode':mode,'parts':rows,'Display_Frame':{'vertices_mm':d.vert_properties[:,:3].tolist(),'triangles':d.tri_verts.tolist()}})+'\n')
print('CAPTURED',mode,len(rows),path,flush=True)
