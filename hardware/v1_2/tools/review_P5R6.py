"""Local P5R6 review changes; preserve P5R5 power/motion and P5R4 rear/IMU."""
from review_P5R3 import *
import review_P5R3 as base

O = H / 'layout_P5R6'
KINDS = ['motion', 'power', 'rear']
O.mkdir(exist_ok=True)


def paths(kind):
    assert kind in KINDS + ['imu']
    n = 'MORI_imu_P5R4' if kind == 'imu' else f'MORI_{kind}_P5R6'
    d = H / 'kicad' / n
    r = O / 'reports' / kind
    r.mkdir(parents=True, exist_ok=True)
    return n, d, d / (n + '.kicad_pcb'), r


def source(kind):
    rev = 'P5R4' if kind == 'rear' else 'P5R5'
    n = f'MORI_{kind}_{rev}'
    d = H / 'kicad' / n
    return n, d, d / (n + '.kicad_pcb')


base.paths, base.source, base.O, base.KINDS = paths, source, O, KINDS

if __name__ == '__main__' and sys.argv[1] == 'init':
    base.init()
