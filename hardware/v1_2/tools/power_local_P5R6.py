"""P5R6 local SW/bootstrap placement trial. Source P5R5 remains immutable."""
from review_P5R6 import *


def apply():
    # Rebuild only this task-owned candidate from the recorded immutable source.
    n, d, p, r = paths('power')
    p.write_bytes(source('power')[2].read_bytes())
    e = Edit('power')
    moves = []
    banks = []
    for num, net, dx, dy in [(60, 'M5', 0, 0), (70, 'C5', -.75, 14)]:
        sw, boot = '/' + net + '_SW', '/' + net + '_BOOT'
        e.remove(net=sw)
        e.remove(net=boot)
        cap = 'C' + str(num + 2)
        cap_y = 22.8 if num == 60 else 36.6
        cap_x = 27.575 if num == 60 else 27.0
        before = {'xy_mm': xy(e.f[cap].GetPosition()), 'angle': e.f[cap].GetOrientationDegrees()}
        e.move(cap, (cap_x, cap_y), 180)
        moves.append({'ref': cap, 'before': before, 'after': {'xy_mm': xy(e.f[cap].GetPosition()), 'angle': 180}})
        chip = (24.4 + dx, 26 + dy)
        chip_pair = [(chip[0], chip[1] - .4), (chip[0], chip[1] + .5)]
        inductor = (21.5, 24 + dy)
        inductor_pair = [(21.5, 24 + dy), (22.4, 24 + dy)]
        for label, points in [('chip', chip_pair), ('inductor', inductor_pair)]:
            for point in points:
                e.via(sw, point, .8, .3)
            # Each pair has explicit F and B copper; cannot be counted by net name alone.
            e.add(sw, F, points, .6 if label == 'chip' else .8)
            e.add(sw, B, points, .8)
            banks.append({'net': sw, 'position': label, 'centres_mm': points, 'diameter_mm': .8, 'drill_mm': .3, 'parallel_count': 2})
        e.add(sw, F, [e.pos('U' + str(num), 2), chip], .6)
        e.add(sw, F, [e.pos('L' + str(num), 1), inductor], .8)
        e.add(sw, B, [chip, (chip[0], inductor[1]), inductor], .8)
        portal = (25, cap_y) if num == 60 else (chip[0], cap_y)
        e.via(sw, portal, .8, .3)
        branch = [(chip[0], inductor[1]), (chip[0], cap_y + .6), portal] if num == 60 else [(chip[0], inductor[1]), portal]
        e.add(sw, B, branch, .6)
        e.add(sw, F, [portal, e.pos(cap, 2)], .2)
        # Align the right-hand cap pad with BOOT; route stays outside the IC body.
        end = e.pos(cap, 1)
        pin = e.pos('U' + str(num), 6)
        # The offset C72 route starts inside BOOT's 1.1 mm copper land; no tiny jog.
        start = pin if num == 60 else (end[0], pin[1])
        assert e.pad('U' + str(num), 6).HitTest(pt(*start))
        e.add(boot, F, [start, end], .2)
    dump(r / 'bootstrap_trial.json', {'placements': moves, 'SW_banks': banks,
                                     'scope': 'Only SW/BOOT tracks/vias and C62/C72 placements',
                                     'electrical_performance': 'NOT_TESTED'})
    return e.check('bootstrap_final_candidate', accept=True)


if __name__ == '__main__':
    ok, report = apply()
    if not ok:
        for row in report['violations']:
            print(row)
        raise SystemExit(1)
