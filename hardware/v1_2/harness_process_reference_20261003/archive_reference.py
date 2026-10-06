"""Archive verified historical crimp references without changing released designs."""
from pathlib import Path
import datetime,hashlib,json,shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/'mechanical/studies/prearrival_finish/harness_A8'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
if (HERE/'delivery_manifest.json').exists():
    raise SystemExit('Published archive exists; do not overwrite.')
(HERE/'sources').mkdir(exist_ok=True)
received=[]
for rel in ['CRIMP_REFERENCE.md','crimp_guide_sources.json','sources/JST_SPH004_crimp.pdf','sources/JST_SSH003_crimp.pdf','JST_SPH004_crimp.png','JST_SSH003_crimp.png']:
    src=SOURCE/rel
    dst=HERE/'sources'/src.name
    if dst.exists():assert sha(dst)==sha(src),'Refuse changed receipt'
    else:shutil.copy2(src,dst)
    received.append(dict(source=str(src.relative_to(ROOT)),snapshot=str(dst.relative_to(ROOT)),sha256=sha(src)))
expected={'JST_SPH004_crimp.pdf':'3fa679edf3394e047080d271f52dc52e47c62cc1cd8803d8cbfed40156d1e5ff',
          'JST_SSH003_crimp.pdf':'ab071f092d2ec6523deeb2d5626db7f0e354982f53ac2d1dd0bd84f89e6ec352'}
for n,h in expected.items():assert sha(HERE/'sources'/n)==h

values=[]
for series,file,strip,width,inswidth,heights,pulls in [
 ('SPH-004-P0.5S','JST_SPH004_crimp.pdf',2.3,1.0,1.2,[.50,.53,.58],[3,5,10]),
 ('SSH-003()-()0.2 / SSHL-003()-()0.2','JST_SSH003_crimp.pdf',1.5,.7,.7,[.40,.42,.45],[5,5,10])]:
    for awg,height,pull in zip([32,30,28],heights,pulls):
        values.append(dict(source='sources/'+file,page=1,series_as_printed=series,awg=awg,strip_length_mm=strip,strip_length_tolerance_mm=None,
          conductor_height_mm=height,conductor_height_tolerance_mm=.05,conductor_width_mm=width,conductor_width_tolerance_mm=.05,
          insulation_height_mm=None,insulation_height_reason='Depends on specific wire; star in original table',insulation_width_mm=inswidth,insulation_width_tolerance_mm=.10,
          printed_tensile_N=pull,approved_MORI_pull_limit_N=None,evidence='VENDOR_DOCUMENTED_SERIES_REFERENCE',applies_to_exact_current_combination='BLOCKED'))
actual=dict(terminal_body='SPH-004T-P0.5S',terminal_head='SSH-003T-P0.2-H',wire_reference='Alpha 2841/7; not procurement release',
  suffix_applicability='BLOCKED',process_approval='BLOCKED',strip_length_mm=None,strip_tolerance_mm=None,conductor_height_mm=None,conductor_width_mm=None,
  insulation_height_mm=None,insulation_width_mm=None,pull_limit_N=None,pull_method=None,terminal_retention_limit_N=None,dynamic_life=None,physical_status='NOT_TESTED')
dump(HERE/'reference_values.json',dict(revision='H06-CRIMP-REF-01',date='2026-10-03',source_date_printed='29-01-01',interpreted_source_date='2001-01-29',
  source_doc_number='H4009/017-00',source_revision_currently_latest=None,reference_rows=values,current_candidate_approved_process=actual,
  scope='Historical series guidance only. Source transcription PASS is not process approval. No formal CAD/BOM/pinmap substitution.'))

checks=[]
for rel in ['hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json',
            'hardware/v1_2/head_harness_evidence_20261003/delivery_manifest.json',
            'hardware/v1_2/reviews/J10_C3_visual_20261003/delivery_manifest.json',
            'hardware/v1_2/head_harness_A8_20261003/delivery_manifest.json']:
    m=json.loads((ROOT/rel).read_text());files=m.get('files',m)
    differences=[n for n,h in files.items()if not(ROOT/n).exists()or sha(ROOT/n)!=h]
    checks.append(dict(manifest=rel,checked=len(files),changed=differences,status='FAIL'if differences else'PASS'))
assert all(r['status']=='PASS'for r in checks),checks
dump(HERE/'preservation_check.json',checks)
dump(HERE/'receipt.json',dict(date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',scope='Source hash and complete-page content review only',
  received_sources=received,viewed=['sources/JST_SPH004_crimp.png','sources/JST_SSH003_crimp.png'],page_counts=[1,1],
  web_checks=[dict(url='https://www.jst-india.com/downloads/series/SPH-004-P0.5S.pdf',status='PASS',scope='Read source contents'),
              dict(url='https://www.jst-india.com/downloads/series/SSH-003-02_SSHL-003-02_2.pdf',status='PASS',scope='Read source contents'),
              dict(url='https://www.jst.com/zh/contact/global-contact/',status='BLOCKED',reason='403 direct read'),
              dict(url='https://www.jst.com/contact/global-contact/',status='PASS',scope='Official page search result lists jst-india.com; not a saved HTML download')],
  supplier_contacted=False,pcb_changed=False,formal_pinmap_changed=False,manufacturing_status='BLOCKED',preservation_checks=checks))
entries={str(p.relative_to(ROOT)):sha(p)for p in HERE.rglob('*')if p.is_file()and p.name!='delivery_manifest.json'}
dump(HERE/'delivery_manifest.json',dict(status='PASS',scope='File integrity only',files=entries))
print(json.dumps(dict(files=len(entries),checks=checks,reference_rows=len(values),status='PASS'),ensure_ascii=False,indent=2))
