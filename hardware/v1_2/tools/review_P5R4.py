"""Rear/IMU review revision. Only P5R4 candidates are writable.

Native KiCad checks are mandatory; no manufacturing exports.
"""
from review_P5R3 import *
import review_P5R3 as base

O = H / 'layout_P5R4'
KINDS = ['rear', 'imu']

def paths(kind):
    assert kind in KINDS
    n = f'MORI_{kind}_P5R4'
    d = H / 'kicad' / n
    r = O / 'reports' / kind
    r.mkdir(parents=True, exist_ok=True)
    return n, d, d / (n + '.kicad_pcb'), r

def source(kind):
    n = f'MORI_{kind}_P5R3'
    d = H / 'kicad' / n
    return n, d, d / (n + '.kicad_pcb')

base.paths, base.source, base.O, base.KINDS = paths, source, O, KINDS

if __name__ == '__main__':
    if sys.argv[1] == 'init':
        base.init()

