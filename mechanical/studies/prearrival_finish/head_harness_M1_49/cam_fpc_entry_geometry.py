"""Photo-direction corrections of two existing reconstructed CAM packages.

Only outlet directions are established by the official installed photographs.
Internal slot/contact geometry remains illustrative. This module is not a
connector manufacturer model or a source of mating dimensions.
"""
import copy
from waveshare_detail import component, block, source_solid

def corrected_component(row, board_thickness=1.6):
    ref=row['reference']; assert ref in ['CAMERA_FPC_24','DISPLAY_FPC_18']
    if ref=='CAMERA_FPC_24':
        result=copy.deepcopy(component(row)); u,v=row['center_uv_mm']
        for solid in result['solids']:
            for point in solid['vertices_mm']:
                point[0]=2*u-point[0]; point[1]=2*v-point[1]
        result['dimension_basis']='Original photo-estimated outline unchanged; package rotated180deg about local W to match CAM-FPC-EXIT-R1 official inserted-camera photographs.'
        result['entry_direction_uvw']=[0,1,0]
        result['entry_revision']='CAM-FPC-EXIT-R1'
        result['limitations']='Direction observed; slot height, depth, contact plane/pin1, latch mechanics and actual supply revision remain unknown. Contacts are unnumbered illustrations.'
        return result
    # Preserve the photographed layout: white housing at -U/outboard, black
    # actuator at +U/inboard. The old generic cavity opened on the wrong side.
    u,v=row['center_uv_mm']; w=row['height_v_mm']; h=row['width_mm']; d=row['projection_mm']; t=board_thickness/2
    shapes=[]
    def add(m,material):
        m=m.rotate([0,0,90]).mirror([0,0,1]).translate([u,v,0])
        shapes.append(source_solid(m,material))
    add(block((w,h,.55),(0,0,t+.275)),'dark')
    # Illustrative through-mouth inside the existing white-housing silhouette;
    # no mouth dimension is promoted to VENDOR_DOCUMENTED.
    housing=block((w,h*.52,d-.55),(0,h*.2,t+.55+(d-.55)/2))
    slot_width=w-1.2; slot_height=.45; slot_center_height=.95
    cutter=block((slot_width,h*.70,slot_height),(0,h*.30,t+slot_center_height))
    add(housing-cutter,'ivory')
    add(block((w-.8,.6,.55),(0,-h*.36,t+d-.275)),'dark')
    # A shallow dark back closes the false visible entrance, inside the old
    # component bounds; its internal shape is explicitly not a physical drawing.
    add(block((w-1.2,h*.38,.5),(0,-h*.28,t+.80)),'dark')
    for x in [-w/2+.3,w/2-.3]: add(block((.6,h,d),(x,0,t+d/2)),'ivory')
    for i in range(row['pins']):
        add(block((.2,1.1,.10),((i-(row['pins']-1)/2)*row['pitch_mm'],h*.27,t+.75)),'gold')
    return dict(reference=ref,value=row.get('value','18pin display FPC'),evidence='PHOTO_ESTIMATED',
        dimension_basis='Original photo-estimated package outline and black/white placement preserved. Official installed photograph establishes outward -U direction only.',
        limitations='Slot width/height/depth and gold fingers are unnumbered visual assumptions, not verified insertion/contact data; no physical mating qualification.',
        entry_direction_uvw=[-1,0,0],entry_revision='CAM-FPC-EXIT-R1',
        illustrative_mouth=dict(width_mm=slot_width,height_mm=slot_height,height_from_board_face_mm=slot_center_height,
            evidence='ASSUMED',may_define_harness_datums=False),solids=shapes)
