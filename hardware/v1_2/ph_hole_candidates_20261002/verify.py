"""Read-only invariants and per-hole neighbour review for the four PH candidates."""
from build import *
import csv
import math


def gap_bounds(a,b,limit=2.0):
    """Bracket native copper-shape separation within1um; no centreline shortcut."""
    upper=k.FromMM(limit)
    if not a.Collide(b,upper):return None
    if a.Collide(b,0):return (0.,0.)
    lower=0
    while upper-lower>1000:
        mid=(lower+upper)//2
        if a.Collide(b,mid):upper=mid
        else:lower=mid
    return (k.ToMM(lower),k.ToMM(upper))


def neighbours(board,refs):
    layers=[k.F_Cu,k.B_Cu]if board.GetCopperLayerCount()==2 else[k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]
    objects=[]
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute()==k.PAD_ATTRIB_NPTH:continue
            objects.append((f.GetReference()+'.'+p.GetNumber(),p,p.GetNetCode(),{ly:p.GetEffectiveShape(ly)for ly in layers if p.IsOnLayer(ly)}))
    for t in board.GetTracks():
        objects.append((('via:'if isinstance(t,k.PCB_VIA)else'track:')+t.m_Uuid.AsString(),t,t.GetNetCode(),{ly:t.GetEffectiveShape(ly)for ly in layers if t.IsOnLayer(ly)}))
    rows=[]
    for f in board.GetFootprints():
        if f.GetReference()not in refs:continue
        for p in f.Pads():
            if p.GetAttribute()!=k.PAD_ATTRIB_PTH:continue
            nearest=None
            for layer in layers:
                shape=p.GetEffectiveShape(layer);bbox=shape.BBox();margin=k.FromMM(2)
                for tag,obj,net,shapes in objects:
                    if net==p.GetNetCode()or layer not in shapes:continue
                    other=shapes[layer]
                    bb=other.BBox()
                    # SHAPE_COMPOUND::BBox ignores its clearance argument in
                    # this binding; expand the numeric bounds explicitly.
                    if bb.GetRight()<bbox.GetX()-margin or bb.GetX()>bbox.GetRight()+margin or bb.GetBottom()<bbox.GetY()-margin or bb.GetY()>bbox.GetBottom()+margin:continue
                    gap=gap_bounds(shape,other)
                    if gap is not None and (nearest is None or gap[0]<nearest['gap_lower_bound_mm']):
                        nearest=dict(object=tag,net=obj.GetNetname(),layer=board.GetLayerName(layer),
                                     gap_lower_bound_mm=round(gap[0],6),gap_upper_bound_mm=round(gap[1],6))
            rows.append(dict(ref=f.GetReference(),pin=p.GetNumber(),net=p.GetNetname(),xy_mm=xy(p.GetPosition()),
                             finished_hole_mm=k.ToMM(p.GetDrillSize().x),land_mm=xy(p.GetSize()),
                             drawn_min_annulus_mm=round((min(xy(p.GetSize()))-max(xy(p.GetDrillSize())))/2,6),
                             nearest_foreign_routed_copper_or_pad=nearest))
    return rows


def run():
    formal=json.loads((HERE/'formal_source_hashes.json').read_text())
    before=json.loads((HERE/'before_snapshot.json').read_text())
    changes=json.loads((HERE/'pad_changes.json').read_text())
    current_hashes={};results={};csvrows=[]
    for kind in REVS:
        base,name,source,dest=paths(kind);pcb=dest/(name+'.kicad_pcb');b=k.LoadBoard(str(pcb));after=snapshot(b)
        original=before[kind];allowed={r['ref']:r for r in changes[kind]}
        changed=[];pose_ok=True;padmap_ok=True;other_pads_ok=True;only_size=True
        for ref,f in after['footprints'].items():
            old=original['footprints'][ref]
            for key in ['xy_mm','angle_deg','layer','value']:pose_ok &= f[key]==old[key]
            padmap_ok &= [(p['number'],p['xy_mm'],p['net'],p['shape'],p['angle_deg'],p['attribute'])for p in f['pads']]==[(p['number'],p['xy_mm'],p['net'],p['shape'],p['angle_deg'],p['attribute'])for p in old['pads']]
            if f!=old:changed.append(ref)
            if ref not in allowed:other_pads_ok &= f==old
            else:
                row=allowed[ref]
                only_size &= f['footprint']==row['new_footprint']
                only_size &= all(p['drill_mm']==[row['finished_hole_nominal_mm']]*2 and p['size_mm']==[row['copper_land_mm']]*2 for p in f['pads'])
        pro=json.loads((dest/(name+'.kicad_pro')).read_text())
        oldpro=json.loads((source/(base+'.kicad_pro')).read_text())
        drc=json.loads((HERE/'reports'/kind/'initial_drc.json').read_text())
        erc=json.loads((HERE/'reports'/kind/'initial_erc.json').read_text())
        commands=json.loads((HERE/'reports'/kind/'initial_commands.json').read_text())
        checks=dict(only_PH_footprints_changed=set(changed)==set(allowed),all_component_positions_orientations_values_fixed=pose_ok,
          all_numbered_pad_centres_nets_shapes_fixed=padmap_ok,other_pads_unchanged=other_pads_ok,PH_pad_dimensions_match=only_size,
          all_tracks_vias_widths_unchanged=after['tracks']==original['tracks'],board_edge_unchanged=after['edges']==original['edges'],
          copper_layers_unchanged=after['copper_layers']==original['copper_layers'],
          custom_rules_byte_identical=(dest/(name+'.kicad_dru')).read_bytes()==(source/(base+'.kicad_dru')).read_bytes(),
          design_settings_unchanged=pro['board']['design_settings']==oldpro['board']['design_settings'],
          no_DRC_exclusions=pro['board']['design_settings']['drc_exclusions']==[],
          ERC_zero=not[v for sh in erc['sheets']for v in sh['violations']],
          DRC_zero=not drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity'],
          command_exit_codes_zero=all(c['returncode']==0 for c in commands),
          checked_inputs_match_current=commands[0]['input_sha256']==sha(dest/(name+'.kicad_sch'))and commands[1]['input_sha256']==sha(pcb))
        rows=neighbours(b,set(allowed))
        checks['all_PH_pads_have_checked_neighbours']=all(r['nearest_foreign_routed_copper_or_pad']is not None for r in rows)
        checks['minimum_drawn_annulus_0p30']=all(r['drawn_min_annulus_mm']>=.3 for r in rows)
        # This numeric review is independent of same-package DRC exceptions.
        checks['different_net_pad_track_gap_at_least_0p20']=all(r['nearest_foreign_routed_copper_or_pad']is None or r['nearest_foreign_routed_copper_or_pad']['gap_lower_bound_mm']>=.199 for r in rows)
        # Local libraries must carry the same new hole/land, not only embedded PCB copies.
        lib_ok=True
        for r in changes[kind]:
            nick,item=r['new_footprint'].split(':',1);f=k.FootprintLoad(str(dest/'footprints'/(nick+'.pretty')),item)
            lib_ok &= f is not None and all(xy(p.GetSize())==[r['copper_land_mm']]*2 and xy(p.GetDrillSize())==[r['finished_hole_nominal_mm']]*2 for p in f.Pads()if p.GetAttribute()==k.PAD_ATTRIB_PTH)
        checks['local_footprint_libraries_match']=lib_ok
        results[kind]=dict(board=name,status='PASS'if all(checks.values())else'FAIL',checks=checks,
          footprints=len(changes[kind]),changed_holes=len(rows),routed_segments_and_vias=len(after['tracks']),
          per_hole_review=rows,needed_component_moves=[],needed_connector_rotations=[],needed_route_edits=[],
          manufacturing_release=False,physical_tests='NOT_TESTED')
        for r in rows:
            near=r['nearest_foreign_routed_copper_or_pad']or{}
            row=allowed[r['ref']]
            csvrows.append(dict(board=name,ref=r['ref'],pin=r['pin'],net=r['net'],x_mm=r['xy_mm'][0],y_mm=r['xy_mm'][1],
              finished_hole_nominal_mm=r['finished_hole_mm'],finished_tolerance_minus_mm=-.05,finished_tolerance_plus_mm=0,
              land_width_mm=r['land_mm'][0],land_height_mm=r['land_mm'][1],drawn_annulus_mm=r['drawn_min_annulus_mm'],
              nearest_foreign_copper=near.get('object'),layer=near.get('layer'),
              nearest_gap_lower_mm=near.get('gap_lower_bound_mm'),nearest_gap_upper_mm=near.get('gap_upper_bound_mm'),
              factory_tolerance_confirmed=False))
        for p in dest.rglob('*'):
            if p.is_file()and p.suffix not in ['.kicad_prl','.lck']and not p.name.startswith('~'):
                current_hashes[p.relative_to(ROOT).as_posix()]=sha(p)
        dump(HERE/'reports'/kind/'invariants_and_neighbours.json',results[kind])
        print(kind,results[kind]['status'],'changed holes',len(rows),'min neighbour gap',min(r['nearest_foreign_routed_copper_or_pad']['gap_lower_bound_mm']for r in rows if r['nearest_foreign_routed_copper_or_pad']),flush=True)
    with(HERE/'PH_69_finished_holes_and_neighbours.csv').open('w',newline='',encoding='utf-8-sig')as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    unchanged=all(sha(ROOT/p)==h for p,h in formal.items())
    result=dict(status='PASS'if unchanged and all(r['status']=='PASS'for r in results.values())else'FAIL',
      scope='Independent candidate CAD checks and unchanged-interface proof, NOT manufacturing or physical qualification.',
      formal_source_files_unchanged=unchanged,formal_source_file_count=len(formal),boards=results,
      total_PH_connectors=sum(r['footprints']for r in results.values()),total_changed_holes=len(csvrows),
      nearest_gap_method='Native filled copper pad/track/via shapes on each copper layer, binary clearance bracket<=0.001mm within2mm. Same-net copper and plane fills excluded; full native DRC separately checks zones/thermals/rules. Not fabrication tolerance analysis.',
      needed_mechanical_interface_changes=False,all_copper_tracks_and_vias_unchanged=True,
      fabrication_tolerance='BLOCKED pending PCB-factory confirmation of finished +0/-0.05mm holes and registration/annulus capability',
      manufacturing_release=False,physical_tests='NOT_TESTED')
    dump(HERE/'validation.json',result);dump(HERE/'candidate_source_hashes.json',current_hashes)
    assert result['status']=='PASS','Inspect validation.json before publishing this candidate.'


if __name__=='__main__':run()
