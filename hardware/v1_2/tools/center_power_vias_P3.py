"""One-time P3 endpoint cleanup after enabling all native DRC warnings.

Not a full board generator. The saved native PCB remains authoritative.
"""
import sys
import pcbnew as k
from layout_P3 import paths, pt, xy, track
from geometry_guard_P3 import Guard, via_clear

name, directory, path, report = paths('power')
b = k.LoadBoard(str(path))
items = {t.m_Uuid.AsString(): t for t in b.GetTracks()}

def segment(uid, a=None, z=None):
    t = items[uid]
    a = a or xy(t.GetStart())
    z = z or xy(t.GetEnd())
    assert Guard(b, t.GetNetname()).line_clear(a, z, t.GetLayer(), k.ToMM(t.GetWidth())), (uid, a, z)
    t.SetStart(pt(*a)); t.SetEnd(pt(*z))

def move_via(uid, pos):
    t = items[uid]
    assert via_clear(b, t.GetNetname(), pos, k.ToMM(t.GetWidth(k.F_Cu))), (uid, pos)
    t.SetPosition(pt(*pos))

# Ground stitch at the actual two-segment junction, with a deliberate 45°
# approach on the other side instead of a track ending at the via rim.
move_via('60400ab6-9e39-45f3-94c5-ad57ecec9bc1', (39.008, 41.54))
segment('1911f12a-23e1-4db9-aadc-a5c49aa2cae6', (42, 38.548), (39.008, 41.54))
assert Guard(b, '/GND').line_clear((42,38),(42,38.548),k.B_Cu,.3)
track(b, '/GND', [(42,38),(42,38.548)], .3, k.B_Cu)

# Match the exact converter/header coordinates; keep diagonal runs at 45°.
segment('df86dfd7-7398-47bd-ba09-70667d0a06d7', (48.4,35.775), (45.625,33))
segment('86eff4cd-659a-4612-83ca-655871cb81ea', z=(48.4,35.775))
segment('6473965e-eeed-4db8-bfd9-22c577e4c20c', (46.875,31.125), (46.875,33))
segment('c1e48820-1945-4a33-8b1b-fc3dc60eb493', z=(46.875,31.125))
segment('bebb2d79-a08a-493f-96f4-be49737055a4', (23.0625,24.55), (22.35,24.55))
segment('75e9174f-bae9-4be1-a8d9-d20d201a9f8a', a=(22.35,24.55))
segment('fea23f5d-0fb9-450f-82e7-0d9e70150821', (47.8,33.325), (48.125,33))
segment('bc5466d2-9138-49cc-bd93-af217dafc48e', z=(47.8,33.325))

move_via('2fb93761-9bb3-4745-8b0b-824a90bdb779', (46.775,23.905))
for t in list(b.GetTracks()):
    if isinstance(t,k.PCB_VIA) or t.GetNetname()!='/W_VM': continue
    a,z=xy(t.GetStart()),xy(t.GetEnd())
    changed=False
    if a==(49.0,26.15):a=(49,26.13);changed=True
    if z==(49.0,26.15):z=(49,26.13);changed=True
    if z==(46.75,23.9):z=(46.775,23.905);changed=True
    if changed:segment(t.m_Uuid.AsString(),a,z)

# The two small steps in this gate path are unnecessary: relocate its first
# via by 0.2mm and use one straight horizontal trace above the fuse pads.
move_via('ae1e2147-304d-4fac-9c18-aa7bcab8a3c7', (33.9375,11.1))
segment('9b6e74a7-682f-4e6d-b339-da8bc9c306e4', z=(32.9375,12.1))
segment('b117e247-cf8c-4545-8b43-5804bef3e9bf', (32.9375,12.1), (33.9375,11.1))
assert Guard(b,'/W_GATE_LOW').line_clear((33.9375,11.1),(45.325,11.1),k.F_Cu,.2)
gate = items['58193bdc-0d59-484c-9c09-4f40b7853a82']
gate.SetStart(pt(33.9375,11.1)); gate.SetEnd(pt(45.325,11.1))
for t in list(b.GetTracks()):
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='/W_GATE_LOW' and t.GetLayer()==k.F_Cu and t.m_Uuid!=gate.m_Uuid:b.Delete(t)

k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(path),b)
print('Power P3: exact via junctions and straight gate corridor saved; native DRC required')
