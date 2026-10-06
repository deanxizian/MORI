"""Compare source records, keeping unapproved guidance separate from process limits."""
from pathlib import Path
from decimal import Decimal as D
from html.parser import HTMLParser
import csv,datetime,hashlib,json,re,shutil

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
MECH=ROOT/'mechanical/studies/prearrival_finish/harness_A8'
OLD=ROOT/'hardware/v1_2/harness_process_reference_20261003'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
assert not(HERE/'delivery_manifest.json').exists(),'Published archive: use a new revision'
(HERE/'sources').mkdir(exist_ok=True)
records=json.loads((MECH/'tooling_lookup_sources.json').read_text())
files=['TOOLING_DETAILS.md','tooling_lookup_sources.json']+[r['file']for r in records if 'file'in r]
received=[]
for name in files:
    p=MECH/name;out=HERE/'sources'/p.name
    if out.exists():assert sha(out)==sha(p)
    else:shutil.copy2(p,out)
    expected=next((r['sha256']for r in records if r.get('file')==name),None)
    if expected:assert sha(out)==expected,name
    received.append(dict(source=str(p.relative_to(ROOT)),snapshot=str(out.relative_to(ROOT)),sha256=sha(out)))

class Text(HTMLParser):
    def __init__(self):super().__init__();self.values=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in('script','style'):self.skip+=1
    def handle_endtag(self,t):
        if t in('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,s):
        if not self.skip:self.values.append(s)
def text(path):
    p=Text();p.feed(path.read_text());return re.sub(r'\s+',' ',' '.join(p.values))
faq=text(HERE/'sources/JST_FAQ_SH_H.html')
assert 'Both contacts share the same application crimp tooling' in faq
index=text(HERE/'sources/JST_application_tooling_index.html')
assert 'Strip Length (mm) AWG Crimp Height (mm) Tensile Spec (N)' in index

def interval(raw):
    if '~'in raw:
        a,b=raw.split('~');return [float(D(a)),float(D(b))]
    if '±'in raw:
        a,b=map(D,raw.split('±'));return [float(a-b),float(a+b)]
    return None  # A scalar without a tolerance does not certify zero tolerance.

old=json.loads((OLD/'reference_values.json').read_text())['reference_rows'];rows=[];tools=[]
for mpn in ['SPH-004T-P0.5S','SSH-003T-P0.2-H']:
    f=HERE/'sources'/('JST_tooling_'+mpn+'.json');j=json.loads(f.read_text())
    assert j['title']==mpn and j['tool_name']==mpn
    tools.append(dict(mpn=mpn,sap_scp=j['sap_scp'],is_scp=j['is_scp'],yrs_series=j['yrs_series'],scope='Returned public test-host fields; not selected manufacturing equipment'))
    for i in range(1,10):
        if not j.get('awg'+str(i)):continue
        awg=int(j['awg'+str(i)])
        o=next(r for r in old if r['awg']==awg and r['series_as_printed'].startswith(mpn[:3]+'-'))
        lo=float(D(str(o['conductor_height_mm']))-D(str(o['conductor_height_tolerance_mm'])))
        hi=float(D(str(o['conductor_height_mm']))+D(str(o['conductor_height_tolerance_mm'])))
        ch=j['crimp_height'+str(i)];bounds=interval(ch)
        pull=float(j['tensile_spec'+str(i)]);same=pull==o['printed_tensile_N']
        rows.append(dict(mpn=mpn,awg=awg,old_source=o['source'],query_file=str(f.relative_to(ROOT)),
          old_strip_length_mm=o['strip_length_mm'],old_strip_tolerance_mm=None,
          query_strip_raw=j['strip_length'+str(i)],query_strip_interval_mm=interval(j['strip_length'+str(i)]),
          old_conductor_height_interval_mm=[lo,hi],query_height_raw=ch,query_conductor_height_interval_mm=bounds,
          query_height_within_old=(lo<=bounds[0]and bounds[1]<=hi),
          old_tensile_N=o['printed_tensile_N'],query_tensile_N=pull,tensile_match=same,
          source_conflict_status='PASS'if same else'BLOCKED',
          conflict_reason=None if same else'Source discrepancy; do not choose or average without authority',
          approved_strip_length_mm=None,approved_conductor_height_mm=None,approved_tensile_N=None,
          source_record_revision=None,actual_wire_process_approval='BLOCKED'))
assert len(rows)==6
conflicts=[r for r in rows if not r['tensile_match']]
assert len(conflicts)==1 and conflicts[0]['mpn']=='SSH-003T-P0.2-H'and conflicts[0]['awg']==32
dump(HERE/'comparison.json',dict(revision='H06-CRIMP-COMPARE-01',date='2026-10-03',source_read_status='PASS',scope='Source comparison only; not process approval',
  inherited_reference=str((OLD/'reference_values.json').relative_to(ROOT)),inherited_reference_sha256=sha(OLD/'reference_values.json'),
  rows=rows,query_tools=tools,full_mpn_reference_available='PASS',H_suffix_same_crimp_tooling='PASS',
  official_faq_url='https://www.jst.com/resources/faq/',current_production_process_version='BLOCKED',
  actual_candidate_process='BLOCKED',manufacturing='BLOCKED',physical='NOT_TESTED',
  source_host='test-jst.jst.com',query_record_revision=None,metadata_date_is_process_revision=False))
fields=['mpn','awg','old_strip_length_mm','query_strip_raw','old_conductor_height_interval_mm','query_height_raw','old_tensile_N','query_tensile_N','tensile_match','source_conflict_status','actual_wire_process_approval']
with (HERE/'comparison.csv').open('w',newline='')as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

checks=[]
for rel in ['hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json',
 'hardware/v1_2/head_harness_evidence_20261003/delivery_manifest.json',
 'hardware/v1_2/reviews/J10_C3_visual_20261003/delivery_manifest.json',
 'hardware/v1_2/head_harness_A8_20261003/delivery_manifest.json',
 'hardware/v1_2/harness_process_reference_20261003/delivery_manifest.json']:
    j=json.loads((ROOT/rel).read_text());items=j.get('files',j)
    diff=[n for n,h in items.items()if not(ROOT/n).exists()or sha(ROOT/n)!=h]
    checks.append(dict(manifest=rel,checked=len(items),changed=diff,status='FAIL'if diff else'PASS'))
assert all(x['status']=='PASS'for x in checks)
dump(HERE/'preservation_check.json',checks)
dump(HERE/'receipt.json',dict(received_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Source-only addendum',received_sources=received,
  FAQ_current_direct_web_read='BLOCKED_403',FAQ_verification='Saved production HTML hash verified and official search result crosschecked',
  PCB_changed=False,pinmap_changed=False,formal_wire_selection_changed=False,supplier_contacted=False,source_conflicts=len(conflicts)))
items={str(p.relative_to(ROOT)):sha(p)for p in HERE.rglob('*')if p.is_file()and p.name!='delivery_manifest.json'}
dump(HERE/'delivery_manifest.json',dict(status='PASS',scope='File integrity only',files=items))
print(json.dumps(dict(files=len(items),compared_rows=len(rows),conflicts=[dict(mpn=r['mpn'],awg=r['awg'],old_N=r['old_tensile_N'],query_N=r['query_tensile_N'])for r in conflicts],preservation=checks),ensure_ascii=False,indent=2))
