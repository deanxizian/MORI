"""User-approved component-up WeAct E correction; KiCad Python 3.9.

Only writes the new motion P5R7 namespace. Original P5R6 and mechanics stay intact.
"""
import re
from update_native_P5R7 import *

OLD_FP = 'WeAct_F4_64Pin_V11'
NEW_FP = 'WeAct_F4_64Pin_V11_ECorrected_P5R7'


def build():
    name, d = copy_project('motion')
    _, _, p = paths('motion')
    lib = d / 'footprints/MORI_Custom.pretty'
    original = lib / (OLD_FP + '.kicad_mod')
    s = original.read_text().replace('(footprint "' + OLD_FP + '"', '(footprint "' + NEW_FP + '"')
    s, count = re.subn(r'(\(pad "E[1-8]"[^\n]*?\(at )([0-9.]+)',
        lambda m: m[1] + f'{float(m[2])+2.54:.4f}', s)
    assert count == 8
    (lib / (NEW_FP + '.kicad_mod')).write_text(s)
    b = k.LoadBoard(str(p))
    f = next(f for f in b.GetFootprints() if f.GetReference() == 'U100')
    before = pad_state(f)
    changed = []
    for pad in f.Pads():
        if re.fullmatch('E[1-8]', pad.GetNumber()):
            a = xy(pad.GetPosition())
            pad.SetPosition(pt(a[0]+2.54, a[1]))
            changed.append({'pin':pad.GetNumber(),'net':pad.GetNetname(),'before':a,'after':xy(pad.GetPosition())})
    assert len(changed) == 8
    f.SetFPID(k.LIB_ID('MORI_Custom', NEW_FP))
    for t in list(b.GetTracks()):
        if t.GetNetname() == '/NRST':
            assert not isinstance(t,k.PCB_VIA)
            b.Delete(t)
    route = [(30,22.4),(30,25.19),(31.71,26.9),(34.93,26.9)]
    track(b, '/NRST', route, .2, k.B_Cu)
    title = b.GetTitleBlock()
    title.SetTitle('MORI motion / P5R7 / PROTOTYPE')
    title.SetRevision('V1.2-H0.5-P5R7')
    title.SetComment(0,'WeAct component side UP; pins DOWN; E X+2.54mm; NOT_TESTED')
    for g in b.GetDrawings():
        if isinstance(g,k.PCB_TEXT) and 'MOTION P5R6' in g.GetText():
            g.SetText(g.GetText().replace('MOTION P5R6','MOTION P5R7'))
    b.BuildConnectivity()
    k.ZONE_FILLER(b).Fill(b.Zones())
    k.SaveBoard(str(p),b)
    sch=d/(name+'.kicad_sch')
    s=sch.read_text().replace('MORI_Custom:'+OLD_FP+'"','MORI_Custom:'+NEW_FP+'"')
    s=s.replace('(date "2026-09-23")','(date "2026-09-30")')
    s=s.replace('P5R6 layout/assembly review; circuit P5; PROTOTYPE / NOT_TESTED',
                'P5R7 WeAct E correction; component side up; PROTOTYPE / NOT_TESTED')
    sch.write_text(s)
    dump(HERE/'reports/motion/E_correction.json', {
        'date':'2026-09-30','authorization':'User selected downward straight E pins and component side up; all header pins descend from core underside.',
        'footprint':NEW_FP,'pad_delta_mm':[2.54,0],'changed_pads':changed,
        'A_D_preserved':all(x in pad_state(f) for x in before if not x[0].startswith('E')),
        'NRST_route_mm':route,'width_mm':.2,'layer':'B.Cu',
        'physical_tests':'NOT_TESTED','mechanical_stack':'BLOCKED_PENDING_CORRECT_POSE_INTEGRATION'})


if __name__ == '__main__':
    build()
    checks('motion','initial')
