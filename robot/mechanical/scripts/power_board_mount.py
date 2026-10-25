"""Local P4-hole-based seats, not a claim of current populated PCB fit."""
import hashlib
from common import *
from structural_simplification import hardware


def mount_sites():
    bay=P['layout_cleanup']['power_bay'];s=bay['local_mount']
    path=PROJECT/s['native_handoff']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=s['native_handoff_sha256']:
        raise RuntimeError('Power PCB source changed; review hole coordinates before rebuilding')
    board=json.loads(path.read_text())['boards'][s['native_board']]
    if board['outline_mm']!=bay['max_pcb_xy_mm']:
        raise RuntimeError('Power board outline and mechanical capacity differ')
    w,h=board['outline_mm'];cx,cy=bay['center_xy_mm']
    return [{'ref':v['ref'],'xy_mm':[v['xy_mm'][0]-w/2+cx,h/2-v['xy_mm'][1]+cy],
             'native_xy_mm':v['xy_mm'],'hole_diameter_mm':v['hole_mm'][0],
             'fastened':v['ref'] in s['fastened_hole_refs']} for v in sorted(board['holes'],key=lambda h:h['ref'])]


def build_mount(deck,capacity):
    bay=P['layout_cleanup']['power_bay'];s=bay['local_mount'];z=bay['pcb_bottom_z_mm']
    top=z+bay['nominal_pcb_thickness_mm'];decktop=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    low=z-bay['component_below_mm'];high=top+bay['component_above_mm'];rows=mount_sites()
    for row in rows:
        x,y=row['xy_mm'];ref=row['ref']
        # Only local component-free regions are removed from the capacity box.
        # They are PCB design requirements, not validated component vacancies.
        boolean(capacity,cyl('power_underseat_keepout',(x,y,(low-.1+z)/2),s['underside_local_keepout_diameter_mm']/2,z-low+.1))
        boolean(capacity,cyl('native_power_PCB_hole',(x,y,(low+high)/2),row['hole_diameter_mm']/2,high-low+.4))
        if row['fastened']:
            boolean(capacity,cyl('power_top_tool_keepout',(x,y,(top+high+.1)/2),s['top_tool_keepout_diameter_mm']/2,high-top+.1))
        union(deck,cyl('power_short_seat',(x,y,(decktop-.15+z)/2),s['support_diameter_mm']/2,z-decktop+.15))
        if not row['fastened']:
            # Empty native hole remains visible; the surrounding PCB rests on the seat.
            boolean(deck,cyl('power_unfastened_hole',(x,y,z-.8),row['hole_diameter_mm']/2,1.8))
            continue
        boolean(deck,cyl('power_insert_pilot',(x,y,z-s['pilot_depth_mm']/2+.05),s['pilot_diameter_mm']/2,s['pilot_depth_mm']+.1))
        boolean(deck,cyl('power_blind_tip_clearance',(x,y,z-s['screw_tip_clearance_depth_mm']/2+.05),s['screw_tip_clearance_diameter_mm']/2,s['screw_tip_clearance_depth_mm']+.1))
        iz=z-s['insert_top_inset_mm']-s['insert_length_mm']/2
        ins=ring('Power_Board_'+ref+'_Insert',(x,y,iz),s['insert_outer_diameter_mm']/2,s['insert_inner_diameter_mm']/2,s['insert_length_mm'])
        hardware(ins,'电源板M2短嵌件 / 试配尺寸')
        screw=cyl('Power_Board_'+ref+'_Screw',(x,y,top-s['screw_length_mm']/2),s['screw_shank_model_diameter_mm']/2,s['screw_length_mm'])
        union(screw,cyl('power_M2_head',(x,y,top+s['screw_head_height_mm']/2),s['screw_head_diameter_mm']/2,s['screw_head_height_mm']))
        hardware(screw,'电源板对角M2×6 / P4孔位参考')
        for obj in [ins,screw]:
            obj['interface_status']='ASSUMED trial hardware; native P4 hole location only; P5, installed components and coupon fit pending'
    capacity['model_fidelity']='CAPACITY_ENVELOPE_WITH_P4_NATIVE_HOLES; P5_POPULATED_CAD_PENDING'
    capacity['assembly_note']='Four low integral seats, two diagonal trial screws. Top/underside local keepouts are requirements, not confirmed free component areas.'
    deck['power_board_mount']='Four diameter5.6 low seats; no long rails. Two diagonal M2x6 trial joints, source P4 native holes. Install before fixed yaw bridge/head.'
    save_json(ROOT/'reports/power_board_mount_geometry.json',{
        'revision':P['revision'],'status':'GENERATED_PENDING_VALIDATION','native_source':s['native_handoff'],
        'native_board':s['native_board'],'source_sha256':s['native_handoff_sha256'],'sites':rows,
        'support_diameter_mm':s['support_diameter_mm'],'support_height_mm':z-decktop,
        'PCB_bottom_z_mm':z,'underside_allocated_component_gap_to_deck_mm':low-decktop,
        'printed_parts_added':0,'screws_added':2,'inserts_added':2,
        'whole_populated_fit':'BLOCKED','limits':s['status']})
