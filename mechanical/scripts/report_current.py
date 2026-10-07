"""Current revision summary; never rewrite the retained historical gallery."""
import hashlib, html, json
from pathlib import Path

def generate(project=None):
    project=Path(project or Path(__file__).resolve().parents[2]);root=project/'mechanical'
    params=json.loads((project/'config/geometry.json').read_text())
    evidence={'revision':params['revision'],'status':'BLOCKED','manufacturing_release':False,'checks':{},'errors':[]}
    paths={'build':'build_manifest.json','validation':'validation.json','delivery':'delivery_consistency.json','export':'export_manifest.json'}
    docs={}
    for key,name in paths.items():
        path=root/'reports'/name
        if not path.is_file():evidence['errors'].append('Missing evidence: '+name);continue
        docs[key]=json.loads(path.read_text())
        evidence['checks'][key]={'file':'reports/'+name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    for name,digest in docs.get('build',{}).get('input_sha256',{}).items():
        path=project/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:evidence['errors'].append('Stale build input: '+name)
    if 'build' in docs and not docs['build'].get('input_sha256'):evidence['errors'].append('Build provenance missing')
    v=docs.get('validation',{})
    if not v.get('counts') or v.get('counts',{}).get('FAIL',0):evidence['errors'].append('Validation missing or has failed checks')
    model=root/'mori_v1_2.blend'
    if not model.is_file() or v.get('source_blend_sha256')!=hashlib.sha256(model.read_bytes()).hexdigest():evidence['errors'].append('Validation does not match current model')
    d=docs.get('delivery',{})
    if d.get('status')!='PASS':evidence['errors'].append('Current delivery consistency has not passed')
    e=docs.get('export',{})
    if not e.get('candidate_count') or e.get('candidate_count')!=e.get('exported_count'):evidence['errors'].append('Candidate STL export incomplete')
    evidence['validation_counts']=v.get('counts',{})
    evidence['status']='FAIL' if evidence['errors'] else 'PASS'
    evidence['scope']='Executed source/export consistency only. No physical, strength, assembly, electrical or manufacturing release.'
    report=root/'reports/current_report.json';report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    esc=html.escape
    rows=''.join('<li>'+esc(s)+'</li>' for s in evidence['errors']) or '<li>源文件、当前检查和候选导出证据一致。</li>'
    links=''.join(f'<li><a href="{esc(v["file"])}">{esc(k)}</a></li>' for k,v in evidence['checks'].items())
    (root/'current_report.html').write_text(f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {esc(params['revision'])} 当前构建报告</title><style>body{{font:17px/1.6 system-ui;max-width:850px;margin:40px auto;padding:0 24px}}code{{word-break:break-all}}</style><h1>MORI {esc(params['revision'])} 当前构建报告</h1><p>证据一致性：<strong>{evidence['status']}</strong>。整机仍为 PROTOTYPE / UNVALIDATED，未制造放行。</p><ul>{rows}</ul><p>实际几何检查统计：<code>{esc(json.dumps(evidence['validation_counts']))}</code>。PASS 仅限原记录的检查范围；其余 BLOCKED / NOT_TESTED 仍保留。</p><ul>{links}</ul><p><a href="../docs/CURRENT_STATUS.md">当前工程卡点</a> · <a href="index.html">保留的图册快照</a> · <a href="reports/current_report.json">机器可读证据</a></p></html>''')
    if evidence['errors']:raise RuntimeError('Current report blocked: '+'; '.join(evidence['errors']))
    return evidence
