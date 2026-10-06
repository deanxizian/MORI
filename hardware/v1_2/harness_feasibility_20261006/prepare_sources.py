#!/usr/bin/env python3
"""Capture source evidence only; never edits formal MORI design files."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, urllib.request, concurrent.futures, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(p, obj): p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def main():
    for d in ('sources', 'inputs', 'results'): (HERE / d).mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    if not (HERE/'inputs/protected_baseline.json').exists():
        formal = json.loads((ROOT/'hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json').read_text())
        extra = ['contracts/components.json', 'contracts/electrical_interfaces.json',
                 'hardware/v1_2/interfaces/harness_V1.2-H0.5-P5R7.csv',
                 'hardware/v1_2/head_harness_evidence_20261003/head_interface_pinmap_revA.csv',
                 'hardware/v1_2/reviews/J10_C3_visual_20261003/MORI_power_J10_C4_CANDIDATE/MORI_power_J10_C4_CANDIDATE.kicad_pcb']
        baseline = {p:sha(ROOT/p) for p in formal}
        prior_mismatch = [p for p,h in formal.items() if baseline[p] != h]
        baseline.update({p:sha(ROOT/p) for p in extra})
        write_json(HERE/'inputs/protected_baseline.json', {'captured_utc':now, 'formal_count':len(formal),
                   'preexisting_mismatch_against_formal_manifest':prior_mismatch, 'files':baseline})
        if prior_mismatch: raise RuntimeError('Formal files differ from received manifest; inspect before continuing')
    inputs = ['AGENTS.md','contracts/components.json','contracts/electrical_interfaces.json',
              'contracts/mechanical_interfaces.json','config/geometry.json',
              'hardware/v1_2/interfaces/harness_V1.2-H0.5-P5R7.csv',
              'mechanical/studies/prearrival_finish/head_harness_M1_49/remaining_routes/INTERFACE_NOTES.md',
              'mechanical/studies/prearrival_finish/head_harness_M1_49/remaining_routes/ENDPOINT_REQUIREMENTS.md',
              'mechanical/studies/prearrival_finish/head_harness_M1_49/remaining_routes/sources/alpha_2622_facts.json',
              'mechanical/studies/prearrival_finish/head_harness_M1_49/remaining_routes/sources/xh_compatibility_screen.json']
    captures=[]
    for rel in inputs:
        src=ROOT/rel; dst=HERE/'inputs'/src.name
        if not dst.exists(): shutil.copy2(src,dst)
        captures.append({'path':rel,'copy':str(dst.relative_to(HERE)),'sha256':sha(dst)})
    write_json(HERE/'inputs/source_snapshots.json', {'captured_utc':now, 'files':captures})
    copies = {
      'FEETECH_SCS0009_A0.pdf':'hardware/v1_2/harness_evidence_20261002/sources/feetech_SCS0009_A0.pdf',
      'CAM_V1.pdf':'hardware/v1_2/head_harness_evidence_20261003/sources/CAM_V1.pdf',
      'CAM_V11.pdf':'hardware/v1_2/head_harness_evidence_20261003/sources/CAM_V11.pdf',
    }
    for name,rel in copies.items():
        dst=HERE/'sources'/name
        if not dst.exists(): shutil.copy2(ROOT/rel,dst)
    write_json(HERE/'sources/prior_source_provenance.json', [{'file':n,'copied_from':p,'sha256':sha(HERE/'sources'/n)} for n,p in copies.items()])
    urls = {
      'JST_XH.pdf':'https://www.jst-mfg.com/product/pdf/eng/eXH.pdf',
      'JST_GH.pdf':'https://www.jst-mfg.com/product/pdf/eng/eGH.pdf',
      'Alpha_2622.html':'https://www.alphawire.com/en/products/wire/hook-up-wire/thermothin/2622',
      'Alpha_2626.html':'https://www.alphawire.com/products/wire/hook-up-wire/thermothin/2626',
      'Alpha_6713.html':'https://www.alphawire.com/en/products/wire/ecogen/ecowire/6713',
      'TE_55A0111-22-0.html':'https://www.te.com/en/product-2160123004.html',
      'FEETECH_SCS0009_product.html':'https://www.feetechrc.com/6v-23kg-serial-bus-steering-gear_65522.html',
      'TI_SDAA284_CC.pdf':'https://www.ti.com/lit/an/sdaa284/sdaa284.pdf',
      'Adafruit_5978.html':'https://www.adafruit.com/product/5978',
    }
    def fetch(item):
        name,url=item; dst=HERE/'sources'/name
        entry={'file':name,'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat()}
        if dst.exists(): return dict(entry,status='EXISTING_CAPTURE',sha256=sha(dst),bytes=dst.stat().st_size)
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=25) as r:
                data=r.read(); entry.update(http_status=r.status,content_type=r.headers.get('Content-Type'),final_url=r.url)
            if name.endswith('.pdf') and not data.startswith(b'%PDF'): raise ValueError('Response is not a PDF')
            dst.write_bytes(data)
            return dict(entry,status='PASS',bytes=len(data),sha256=sha(dst))
        except Exception as e: return dict(entry,status='BLOCKED',error=str(e))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(fetch,urls.items()))
    write_json(HERE/'sources/fetch_log.json',{'captured_utc':now,'python':sys.version,'items':results})
    print(json.dumps({'protected_files':len(json.loads((HERE/'inputs/protected_baseline.json').read_text())['files']),
                      'downloads':[{k:x.get(k) for k in ('file','status','error','bytes')} for x in results]},ensure_ascii=False))

if __name__=='__main__': main()
