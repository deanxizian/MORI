"""Remove global positive paste growth, preserve Mask and footprint overrides."""
from review_P5R3 import *
old='Source rule mask/paste expansion remains +0.05 mm.'
new='Mask expansion +0.05 mm retained. P5R3 global paste growth 0 mm / 0 percent; local apertures retained; stencil process NOT_TESTED.'
for kind in KINDS:
 e=Edit(kind);ds=e.b.GetDesignSettings()
 before={'global_paste_mm':k.ToMM(ds.m_SolderPasteMargin),'global_paste_ratio':ds.m_SolderPasteMarginRatio,'mask_mm':k.ToMM(ds.m_SolderMaskExpansion)}
 ds.m_SolderPasteMargin=0;ds.m_SolderPasteMarginRatio=0
 for f in e.b.GetFootprints():f.SetLibDescription(f.GetLibDescription().replace(old,new))
 e.save()
 # Description only: maintain board/library identity without changing lands.
 for p in e.d.rglob('*.kicad_mod'):
  t=p.read_text()
  if old in t:p.write_text(t.replace(old,new))
 p=e.d/(e.name+'.kicad_pro');j=json.loads(p.read_text())
 r=j['board']['design_settings']['rules']
 for key in ['solder_paste_margin','solder_paste_margin_ratio']:
  if key in r:r[key]=0
 p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
 if kind=='power':
  p=e.d/(e.name+'.kicad_sch');t=p.read_text();assert '80 x 45 mm PCB;'in t;p.write_text(t.replace('80 x 45 mm PCB;','80 x 55 mm PCB;'))
 dump(e.r/'paste_change.json',{'before':before,'after':{'global_paste_mm':0,'global_paste_ratio':0,'mask_mm':k.ToMM(ds.m_SolderMaskExpansion)},'local_aperture_overrides':'preserved','assembly_status':'NOT_TESTED'})
 print(kind,'paste global 0; mask and local aperture overrides preserved')
