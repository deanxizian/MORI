"""Extract exact horizontal manifold sections for temporary tail planning."""
from pathlib import Path
TP_SCRIPT=Path(__file__).resolve();TP_ROOT=TP_SCRIPT.parent
TP_HELPER=TP_ROOT/'check_CAM_tail_ribbon_access.py';__file__=str(TP_HELPER)
exec(compile(TP_HELPER.read_text().split('\ntr_rows=[];',1)[0],str(TP_HELPER),'exec'),globals())
__file__=str(TP_SCRIPT)
tp_sections={}
for z in [210.65,212.,213.35]:
    rows=[]
    for name,m in tr_targets.items():
        lo=list(m.bounding_box())[:3];hi=list(m.bounding_box())[3:]
        if not lo[2]<=z<=hi[2]:continue
        if hi[0]<-55 or lo[0]>20 or hi[1]<-45 or lo[1]>40:continue
        polygons=m.slice(z).to_polygons()
        if len(polygons):rows.append({'name':name,'polygons':[p.tolist() for p in polygons]})
    tp_sections[str(z)]=rows
(TR_OUT/'sections.json').write_text(json.dumps({'source_main_sha256':source_hash,'sections':tp_sections},indent=2)+'\n')
print('SECTIONS',[(z,len(rows)) for z,rows in tp_sections.items()],flush=True)
