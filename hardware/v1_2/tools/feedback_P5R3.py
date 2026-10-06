"""Remove redundant adjacent M5_FB via and simplify pin escape."""
from review_P5R3 import *
e=Edit('power')
e.remove(ids=['3df849a6','413f46b2','bda2ac70','88f1bddc'])
e.add('/M5_FB',F,[(26.35,26.95),(27.1012,26.95),(28.0416,26.0096)],.2)
e.check('PWR04_feedback_escape')
