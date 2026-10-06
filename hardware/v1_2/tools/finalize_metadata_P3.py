"""Refresh placement records and mark native P3 titles; no electrical edits."""
import sys,json
import pcbnew as k
from layout_P3 import paths,update_records
from functional_schematic import sexpr,encode,q
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));tb=b.GetTitleBlock();tb.SetTitle(name+' / PROTOTYPE');tb.SetRevision('V1.2-H0.3-P3');tb.SetDate('2026-09-22');tb.SetComment(0,'NOT BENCH VALIDATED - NOT RELEASED FOR FABRICATION');tb.SetComment(1,'Source rule exceptions and mechanical installation: layout_P3/README.md');k.SaveBoard(str(p),b)
data=json.loads((d/'connectivity.json').read_text());data['layout_revision']='V1.2-H0.3-P3';data['pcb_status']='PROTOTYPE_ROUTED_NOT_BENCH_VALIDATED';data['mechanical_outline_status']='DESIGN_GENERATED: '+('user-authorized80x55; populated assembly remains unqualified' if kind=='power' else 'retained starting outline; populated assembly remains unqualified');update_records(kind,b,data)
s=d/(name+'.kicad_sch');tree=sexpr(s.read_text());tb=next(x for x in tree if isinstance(x,list) and x[0]=='title_block')
for row in tb[1:]:
 if row[0]=='title':row[1]=q('MORI / '+kind+' / P3 - FUNCTIONAL SCHEMATIC')
 if row[0]=='rev':row[1]=q('V1.2-H0.3-P3')
s.write_text(encode(tree)+'\n')
(d/'README.md').write_text('# '+name+'\n\nPROTOTYPE / NOT_TESTED — 未台架验证，未制造放行。\n\n保存的 `.kicad_pcb` 是最终布线真值。`.dsn/.ses` 仅是过程快照，不能重导入覆盖后续局部修订。\n\n[三板说明和规则边界](../../layout_P3/README.md) · [本版原生检查](../../layout_P3/reports/'+name+'/drc.json)\n')
print(name,'P3 titles and final placement refreshed')
