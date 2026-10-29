"""Read-only source-ground, clamp and new mounted-face Fab geometry audit.
Uses the preserved R161R nominal-body method without its visual-review claims.
This does not establish whole-board, coupling, thermal or physical qualification.
"""
import json,sys
from pathlib import Path
rev=sys.argv[1]
source=Path('robot/.state/c3-completion/trials/R161R_inspection.py').read_text().split('"""',2)[2]
prefix=source.split('\npath=list(',1)[0].replace('R161R',rev)
ns={};exec(compile(prefix,'R162_preserved_nominal_body_method','exec'),ns)
r={'scope':__doc__,'source_sha256':ns['a'].sha,'board_sha256':ns['c'].sha,'source_ground_vias_preserved':len(ns['ground']),
   'clamps':ns['clamps'],'same_face_nominal_body_hits':ns['same'],'opposite_or_internal_body_hits':ns['opposite'],
   'mounted_face_visual':'NOT_TESTED','whole_board_visual':'NOT_TESTED','thermal_coupling_and_manufacturer_layout':'NOT_TESTED',
   'adopted':False,'manufacturing_release':False}
ns['out'].write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'revision':rev,'same_face_hits':len(ns['same']),'opposite_or_internal_hits':len(ns['opposite']),'ground_vias_preserved':len(ns['ground'])}))
