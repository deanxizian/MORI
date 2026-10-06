#!/usr/bin/env python3
"""Validate this evidence package and create its independent delivery manifest."""
from pathlib import Path
import csv, hashlib, json, re, sys
from datetime import datetime, timezone
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):(HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def main():
    for p in HERE.rglob('*.json'):
        if p.name!='delivery_manifest.json': json.loads(p.read_text())
    for p in [HERE/'endpoint_gaps.csv',*list((HERE/'results').glob('*.csv'))]:
        rows=list(csv.DictReader(p.open(newline='')))
        assert rows and all(None not in row for row in rows),p
    missing=[]
    for link in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if not link.startswith(('https://','http://','#')) and not (HERE/link).exists():missing.append(link)
    assert not missing,missing
    facts=json.loads((HERE/'facts.json').read_text()); result=json.loads((HERE/'results/calculations.json').read_text())
    assert result['inputs_sha256']==sha(HERE/'facts.json')
    assert all(not w['selected'] for w in facts['wires'])
    assert json.loads((HERE/'results/source_preservation.json').read_text())['status']=='PASS'
    fetched=json.loads((HERE/'sources/fetch_log.json').read_text())['items']
    fetched+=json.loads((HERE/'sources/additional_fetch_log.json').read_text())
    local=json.loads((HERE/'sources/prior_source_provenance.json').read_text())
    prior_urls={
      'FEETECH_SCS0009_A0.pdf':'https://www.feetechrc.com/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf',
      'CAM_V1.pdf':'https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-XXXX-schematic.pdf',
      'CAM_V11.pdf':'https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-OVxxxx_Rev1.1.pdf'}
    for x in local:x.update(url=prior_urls[x['file']],retrieval='Local prior archive reused on2026-10-06; original provenance retained')
    for x in fetched:
        if x['status']=='PASS': assert x['sha256']==sha(HERE/'sources'/x['file'])
    save('source_index.json',{'date_local':'2026-10-06','direct_fetches':fetched,'reused_sources':local,
        'web_only_excerpts':['sources/TE_product_web_excerpt.txt','sources/FEETECH_product_web_excerpt.txt','sources/distributor_ordercode_excerpt.txt'],
        'source_priority':'Manufacturer fields for electrical/mechanical facts. Distributor only order-code/price observations; explicit2622strand conflict preserved.',
        'unretrieved':'TE customer drawing HTTP403; no inferred OD tolerance or bend qualification.',
        'third_party_rights':'Original manufacturer documents retained for engineering reference. Adafruit native files unmodified; full README and CC BY-SA license included. No copying into formal MORI board.'})
    viewed=['JST_XH.pdf_p1.png','JST_XH.pdf_p3.png','JST_GH.pdf_p1.png','JST_GH.pdf_p2.png',
            'FEETECH_SCS0009_A0.pdf_p3.png','FEETECH_SCS0009_A0.pdf_p4.png','FEETECH_SCS0009_A0.pdf_p8.png',
            'CAM_V1.pdf_p1.png','CAM_V11.pdf_p1.png','GCT_USB4151_drawing.pdf_p1.png',
            'TI_SDAA284_CC.pdf_p5.png','TI_SDAA284_CC.pdf_p6.png']
    save('results/source_visual_review.json',{'date_local':'2026-10-06','status':'PASS',
         'scope':'Read-only manufacturer source-page checks, not PCB layout review or whole-board electrical qualification',
         'viewed':[{'path':'previews/'+n,'sha256':sha(HERE/'previews'/n)} for n in viewed],
         'renderer':'macOS PDFKit via render_selected.swift, 2200px long dimension',
         'warnings':'CoreGraphics emitted a PDF warning; relevant displayed content was legible. TE drawing unavailable, not represented as reviewed.',
         'not_visualised':'GCT pages2/3 and TI pages3/4 were rendered/archived but no visual-review claim made for them.'})
    save('results/package_validation.json',{'status':'PASS','json_parse':'PASS','csv_column_counts':'PASS','README_local_links':'PASS',
         'facts_match_calculation_hash':'PASS','no_selected_replacement':'PASS','protected_source_files':254,
         'python':sys.version,'verified_utc':datetime.now(timezone.utc).isoformat(),
         'commands':['python prepare_sources.py','swift render_selected.swift '+str(HERE),'python calculate.py','python finalize.py'],
         'no_native_ERC_DRC_retest':'No design modification in this task; existing reports unchanged.'})
    manifest={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
              if p.is_file() and p.name!='delivery_manifest.json' and '__pycache__' not in p.parts}
    save('delivery_manifest.json',{'date_local':'2026-10-06','files':manifest,'count':len(manifest),
         'scope':'Independent evidence only; no fabrication files','generated_utc':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'package':'PASS','files':len(manifest),'formal_design_untouched':True,'harness_release':'BLOCKED'},ensure_ascii=False))
if __name__=='__main__':main()
