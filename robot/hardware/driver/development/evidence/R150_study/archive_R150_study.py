"""Preserve R150 independent trials and routing proposals without adopting a PCB."""
import gzip,hashlib,json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
out=dev/'evidence/R150_study';assert not out.exists();out.mkdir()
board='MORI_Interface_C3.kicad_pcb';source=dev/'native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
expected='958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
assert sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R148E' and status['unconnected_items']==26
adoption=read(dev/'evidence/R148E/adoption.json')
for x in adoption['member_checks']:assert sha(source/x['member'])==x['sha256']
payloads=[]
def preserve(src,rel):
    data=src.read_bytes();compressed=src.suffix=='.kicad_pcb' or len(data)>524288;dest=out/rel
    if compressed:dest=dest.with_name(dest.name+'.gz')
    dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
    dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
    payloads.append(dict(path=dest.relative_to(out).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
trials=[];projects={'R150A','R150B','R150C','R150D'}
for p in sorted(b.glob('R150*')):
    if p.is_file():preserve(p,Path('raw')/p.name)
    elif p.name in projects:
        preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
        row=dict(revision=p.name,board_sha256=sha(p/board),adopted=False)
        d=b/(p.name+'-drc.json');a=b/(p.name+'-audit.json')
        if d.exists():row.update({k:len(read(d).get(k,[])) for k in ['unconnected_items','violations','schematic_parity']})
        else:row['build_status']='FAILED_BEFORE_SAVE_SOURCE_COPY_ONLY'
        if a.exists():
            r=read(a)
            row.update(power_width_failures=[dict(net=x['net'],width_mm=x['width_mm'],lost_pair_count=len(x['lost_pairs'])) for x in r['power_width'] if x['status']=='FAIL'],lost_pad_connections=[dict(net=x['net'],lost_pair_count=len(x['lost_pad_pairs'])) for x in r['lost_pad_connections']],retained_reference_losses=r['retained_trace_reference_loss'],new_reference_gap_count=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in r['new_copper_review']),ground_groups=len(r['GND_groups']),ground_pad_count=sum(len(x) for x in r['GND_groups']),critical_placement_failures=sum(x['status']=='FAIL' for x in r['critical_placement']),reference_transition_failures=sum(x['status']=='FAIL' for x in r['reference_transitions']))
        trials.append(row)
    else:
        for q in sorted(p.rglob('*')):
            if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
preserve(Path(__file__),Path('archive_R150_study.py'))
def write(name,data):(out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
write('summary.json',dict(scope=__doc__,accepted_revision='R148E',accepted_board_sha256=expected,accepted_remaining_connections=26,remaining_connectivity_fraction=.65,not_engineering_progress=True,adopted_trials=[],candidates=trials,source_non_pcb_members_unchanged=77,candidate_visual_qualification='NOT_TESTED',erc_in_this_study='NOT_RUN',manufacturing_release=False,goal_complete=False))
write('archive_manifest.json',dict(scope=__doc__,payloads=payloads))
for row in payloads:
    p=out/row['path'];assert sha(p)==row['sha256']
    data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes()
    assert hashlib.sha256(data).hexdigest()==row['source_sha256']
assert sha(source/board)==expected
write('archive_verification.json',dict(status='PASS',payload_count=len(payloads),stored_and_original_bytes_verified=True,accepted_board_unchanged=True,source_non_pcb_members_unchanged=77,all_local_trials_preserved=True))
print(json.dumps(dict(status='PASS',archive_payloads=len(payloads),accepted_revision='R148E',remaining=26,goal_complete=False)))
