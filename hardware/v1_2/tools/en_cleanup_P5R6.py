"""Smooth the previous two M5_EN free-corner exceptions without touching feedback."""
from review_P5R6 import *
e=Edit('power')
ids=['18ae0e0c','1ef77b49','47448f6f','4bf1048e','aaf121a4','d5264435','eafff13b','f9954114']
e.remove(ids=ids)
points=[(29.89,26),(29.89,27.15),(30.39,27.65),(30.8,27.65),(31.3,28.15),(31.3,28.85),(30.8,29.35),(28.65,29.35),(28.1,28.8),(20.2,28.8)]
e.add('/M5_EN',B,points,.2)
ok,report=e.check('EN_smooth')
dump(e.r/'EN_smooth_geometry.json',{'status':'PASS' if ok else 'FAIL','path_mm':points,'native_drc_accepted':ok,'previous_free_corners_mm':[[31,28],[31,29.1]],'reason':'Clear diagonal corridor around R60, no feedback/quiet-return movement.'})
