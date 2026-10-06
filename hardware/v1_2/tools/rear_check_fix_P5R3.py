"""Resolve inherited rear CC2 off-centre via after restoring ignored checks."""
from review_P5R3 import *
from geometry_guard_P5 import Guard
e=Edit('rear')
e.remove(ids=['433afa2d','90045fa3','b17f88ec'])
e.add('/CC2',B,[(13.208,9.9568),(13.208,8.9408),(13.4112,8.7376),(13.75,8.3988),(13.75,7.045)],.2)
e.check('CC2_center_via')
