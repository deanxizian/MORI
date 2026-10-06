"""Extract genuine before/after nut-pocket sections from the saved assembly."""
from pathlib import Path
import sys,json,subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold,P
ctx=Context();rows=[]
for name,host in P['reaction_nut_alignment']['nut_hosts'].items():
    old=np.load(OUT/(name+'_native_baseline.npz'))
    before=manifold.Manifold(manifold.Mesh64(old['vertices_mm'],old['triangles'].astype(np.uint64)))
    after=ctx.ss[name].m;carrier=ctx.ss[host].m
    center=(old['vertices_mm'].min(0)+old['vertices_mm'].max(0))/2
    # Map world X/Z to section X/Y and section normal to world -Y.
    tr=np.array([[1,0,0,-center[0]],[0,0,1,-center[2]],[0,-1,0,center[1]]])
    row=dict(nut=name,host=host,center_mm=center.tolist(),sections={},nominal_gap_mm=float(after.min_gap(carrier,3)))
    for label,m in [('host',carrier),('before',before),('after',after),('old_overlap',before^carrier)]:
        row['sections'][label]=[a.tolist() for a in m.transform(tr).slice(0).to_polygons()]
    rows.append(row)
ctx.assert_unchanged()
(OUT/'sections.json').write_text(json.dumps(dict(revision=P['revision'],source_blend_sha256=ctx.source_hash,
    rows=rows,sources=ctx.sources,script_sha256=sha(Path(__file__))),ensure_ascii=False,indent=2)+'\n')
subprocess.run(['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python',str(OUT/'plot.py')],check=True)
