"""Archive unadopted R149 routing diagnostics and the verified coordinate-tool fix; preserve R148E."""
import gzip,hashlib,json,shutil,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');out=dev/'evidence/R149_study';assert not out.exists();out.mkdir()
board='MORI_Interface_C3.kicad_pcb';source=dev/'native';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
expected='958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1';assert sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R148E' and status['unconnected_items']==26
adoption=read(dev/'evidence/R148E/adoption.json')
for x in adoption['member_checks']:assert sha(source/x['member'])==x['sha256']
checks=read(b/'R149-coordinate-checks/result.json');compat=read(b/'R149-compat-R148E-verify/result.json');planned=read(b/'R149-compat-planned-delta.json')
assert checks['status']=='PASS' and len(checks['results'])==9
assert compat['board_sha256']==expected and (compat['unconnected_items'],compat['violations'],compat['schematic_parity'],compat['erc_violations'])==(26,0,0,0)
assert planned['status']=='PASS' and len(planned['checks'])==2528
diagnosis=read(b/'R149-soft-obstacle-diagnostic/diagnosis.json')[0];assert diagnosis['status']=='INVALID_SOFT_OBSTACLE_PATH'
payloads=[]
def preserve(src,rel):
    data=src.read_bytes();compressed=src.suffix=='.kicad_pcb' or len(data)>524288;dest=out/rel
    if compressed:dest=dest.with_name(dest.name+'.gz')
    dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
    payloads.append(dict(path=dest.relative_to(out).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
projects={'R149A','R149B','R149C','R149-compat-R148E'}
trials=[]
for p in sorted(b.glob('R149*')):
    if p.is_file():preserve(p,Path('raw')/p.name)
    elif p.name in projects:
        preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
        d=b/(p.name+'-drc.json');row=dict(revision=p.name,board_sha256=sha(p/board),adopted=False)
        if d.exists():row.update({k:len(read(d).get(k,[])) for k in ['unconnected_items','violations','schematic_parity']})
        trials.append(row)
    else:
        for q in sorted(p.rglob('*')):
            if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
before=b/'R149-build_trial-before.py';after=b/'R149-build_trial-after.py';diff=b/'R149-build_trial.diff'
for p in [before,after,diff]:assert not p.exists()
before.write_bytes(subprocess.check_output(['git','show','HEAD:robot/hardware/driver/development/scripts/build_trial.py']))
shutil.copy2(dev/'scripts/build_trial.py',after)
diff.write_bytes(subprocess.check_output(['git','diff','--','robot/hardware/driver/development/scripts/build_trial.py']))
for p in [before,after,diff]:preserve(p,Path('tool_change')/p.name)
preserve(Path(__file__),Path('archive_R149_study.py'))
def write(name,data):(out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
write('summary.json',dict(scope=__doc__,accepted_revision='R148E',accepted_board_sha256=expected,accepted_remaining_connections=26,remaining_connectivity_fraction=.65,not_engineering_progress=True,adopted_trials=[],candidates=trials,coordinate_checks=9,compatibility_checks=2528,compatibility_pcb_byte_identical=True,source_non_pcb_members_unchanged=77,source_images_actually_viewed=['raw/R149-source-views/F.Cu.png','raw/R149-source-views/B.Cu.png','raw/R149-source-views/MUX-B.Cu.png'],candidate_visual_qualification='NOT_TESTED',manufacturing_release=False,goal_complete=False))
write('archive_manifest.json',dict(scope=__doc__,payloads=payloads))
for row in payloads:
    p=out/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['source_sha256']
assert sha(source/board)==expected
write('archive_verification.json',dict(status='PASS',payload_count=len(payloads),stored_and_original_bytes_verified=True,accepted_board_unchanged=True,all_local_trials_preserved=True))
print(json.dumps(dict(status='PASS',archive_payloads=len(payloads),accepted_revision='R148E',remaining=26,goal_complete=False)))
