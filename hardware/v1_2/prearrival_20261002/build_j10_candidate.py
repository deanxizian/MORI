"""Build only the authorized fixed-hole J10 trial. KiCad 10 Python required.

Never modifies a released project, mechanical geometry or manufacturing files.
The candidate may FAIL; do not conceal body collisions by weakening rules.
"""
from pathlib import Path
import csv, hashlib, json, shutil, subprocess, sys
import wx
import pcbnew as k

APP = wx.App(False)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
H = ROOT / 'hardware/v1_2'
sys.path.insert(0, str(H / 'tools'))
from layout_P5 import xy, rect
from body_keepouts_P3R1 import rectangle

OLD = 'MORI_power_P5R6'
NAME = 'MORI_power_P5R7_J10_CANDIDATE'
SOURCE = H / 'kicad' / OLD
DEST = HERE / 'j10_candidate' / NAME
REPORT = HERE / 'j10_candidate' / 'reports'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
FPBASE = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Connector_JST.pretty')
STD = 'JST_PH_S8B-PH-K_1x08_P2.00mm_Horizontal'
LOCAL = STD + '__MORI_1p35land_0p75drill'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
def pad_state(f):
    return sorted((p.GetNumber(), xy(p.GetPosition()), p.GetNetname(), xy(p.GetSize()), xy(p.GetDrillSize())) for p in f.Pads())
def copper(b):
    return sorted((t.m_Uuid.AsString(), t.GetNetname(), t.GetLayer(), xy(t.GetStart()), xy(t.GetEnd()),
                   k.ToMM(t.GetWidth(k.F_Cu) if isinstance(t,k.PCB_VIA) else t.GetWidth())) for t in b.GetTracks())

def main():
    assert not DEST.exists(), 'Do not overwrite a reviewed candidate; create a new trial.'
    hashes = {}
    for p in SOURCE.rglob('*'):
        if not p.is_file() or p.name.startswith('~') or p.suffix in ('.kicad_prl','.lck'): continue
        hashes[str(p.relative_to(ROOT))] = sha(p)
        out = DEST / p.relative_to(SOURCE).parent / p.name.replace(OLD,NAME)
        out.parent.mkdir(parents=True,exist_ok=True)
        data = p.read_bytes()
        if p.suffix in ('.kicad_sch','.kicad_pro'):
            data = data.replace(OLD.encode(),NAME.encode())
        out.write_bytes(data)
    dump(REPORT / 'source_hashes.json',hashes)
    b = k.LoadBoard(str(SOURCE / (OLD+'.kicad_pcb')))
    old = next(f for f in b.GetFootprints() if f.GetReference()=='J10')
    before = pad_state(old)
    before_copper = copper(b)
    oldid = str(old.GetFPID().GetLibNickname()) + ':' + str(old.GetFPID().GetLibItemName())
    new = k.FootprintLoad(str(FPBASE),STD)
    for p in new.Pads():
        op = next(op for op in old.Pads() if op.GetNumber()==p.GetNumber())
        p.SetSize(op.GetSize()); p.SetDrillSize(op.GetDrillSize())
        p.SetShape(op.GetShape()); p.SetNet(op.GetNet())
    new.SetFPID(k.LIB_ID('Connector_JST',LOCAL))
    lib = DEST/'footprints/Connector_JST.pretty'
    k.FootprintSave(str(lib),new)
    new.SetUuid(old.m_Uuid)
    new.SetReference('J10');new.SetValue(old.GetValue());new.SetPath(old.GetPath())
    new.SetOrientationDegrees(old.GetOrientationDegrees());new.SetPosition(old.GetPosition())
    new.Reference().SetVisible(False);new.Value().SetVisible(False)
    b.Remove(old);b.Add(new)
    assert before == pad_state(new), 'Numbered pad geometry/net changed'
    assert before_copper == copper(b), 'Copper changed in footprint-only trial'
    # Rebuild only J10 body guards, both outer layers, without blanket net exceptions.
    for z in list(b.Zones()):
        if z.GetZoneName() in ['BODY_J10','NETBODY_J10','BODY_J10_OPPOSITE','NETBODY_J10_OPPOSITE']:
            b.Delete(z)
    r = rect(new)
    full = rectangle(r);body = rectangle(r)
    for p in new.Pads():
        bb=p.GetBoundingBox()
        x1,y1,x2,y2=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
        # All lands exit away from the horizontal shell, toward board +X.
        body.BooleanSubtract(rectangle([x1-.005,y1-.005,r[2]+1,y2+.005]))
    body.Simplify()
    for layer in [k.F_Cu,k.B_Cu]:
        suffix='' if layer==k.F_Cu else '_OPPOSITE'
        for prefix,shape,forbid in [('NETBODY_',full,False),('BODY_',body,True)]:
            z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetZoneName(prefix+'J10'+suffix)
            z.SetDoNotAllowTracks(forbid);z.SetDoNotAllowVias(forbid)
            z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
            z.Outline().BooleanAdd(shape);b.Add(z)
    b.GetTitleBlock().SetTitle('MORI power J10 side-entry / CANDIDATE / NOT FOR FABRICATION')
    b.GetTitleBlock().SetRevision('P5R7-J10-C1')
    pcb=DEST/(NAME+'.kicad_pcb');k.SaveBoard(str(pcb),b)
    # The localized footprint is shared by schematic and PCB. Circuit remains unchanged.
    sch=DEST/(NAME+'.kicad_sch')
    for p in [sch,DEST/'MORI.kicad_sym']:
        t=p.read_text().replace(oldid,'Connector_JST:'+LOCAL)
        p.write_text(t)
    for p in [DEST/'assembly_bom.csv',DEST/'connectivity.json']:
        p.write_text(p.read_text().replace(oldid,'Connector_JST:'+LOCAL))
    overlaps=[]
    for f in b.GetFootprints():
        if f.GetReference()=='J10' or f.GetLayer()!=k.F_Cu:continue
        q=rect(f)
        if q and r[0]<q[2] and q[0]<r[2] and r[1]<q[3] and q[1]<r[3]:
            overlaps.append({'ref':f.GetReference(),'fab_bounds_mm':q,
                'xy_projection_overlap_mm':[min(r[2],q[2])-max(r[0],q[0]),min(r[3],q[3])-max(r[1],q[1])]})
    dump(REPORT/'geometry.json',{
        'revision':'P5R7-J10-C1','status':'FAIL' if overlaps else 'NOT_TESTED',
        'user_approval':'2026-10-02: fixed-hole side-entry candidate; mechanical receipt required before release',
        'product':'JST S8B-PH-K-S(LF)(SN)','housing':'PHR-8','contact':'SPH-002T-P0.5S',
        'source':'https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
        'source_sha256':sha(HERE/'sources/jst_ph.pdf'),
        'vendor_body_length_width_height_mm':[17.9,7.6,4.8],
        'body_envelope_status':'VENDOR_DOCUMENTED; not measured',
        'position_mm':xy(new.GetPosition()),'rotation_deg':new.GetOrientationDegrees(),
        'pads_before_and_after':before,'numbered_holes_and_nets_unchanged':True,
        'tracks_and_vias_unchanged':True,'board_outline_holes_other_footprints_unchanged':True,
        'fab_bounds_mm':r,'mating_direction_board_xy':[-1,0],
        'unplug_straight_allocation_mm':12,'allocation_evidence':'ASSUMED project inspection allowance, not JST rating',
        'side_comparison':[
            {'orientation':'F.Cu -90deg','preserves_numbered_holes':True,'exit':'-X'},
            {'orientation':'F.Cu +90deg','preserves_numbered_holes':False,'exit':'+X','reason':'Numbered positions reverse; not permitted'},
            {'orientation':'B.Cu mirror','preserves_numbered_holes':'requires checked transform','status':'BLOCKED','reason':'4.8mm header exceeds previous 3mm backside allocation; not adopted'}],
        'same_face_body_projection_collisions':overlaps,
        'complete_mated_fit':'BLOCKED','physical_validation':'NOT_TESTED',
        'candidate_sha256':sha(pcb),'standard_footprint_sha256':sha(FPBASE/(STD+'.kicad_mod'))
    })
    commands=[]
    for args in [
        ['pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations','-o',str(REPORT/'drc.json'),str(pcb)],
        ['sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(REPORT/'erc.json'),str(sch)],
        ['pcb','export','svg','--layers','F.Cu,F.Silkscreen,F.Fab,Edge.Cuts','--mode-single','--page-size-mode','2','--output',str(REPORT/'J10_candidate_front.svg'),str(pcb)]
    ]:
        cp=subprocess.run([CLI]+args,capture_output=True,text=True)
        commands.append({'argv':[CLI]+args,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
        print(args[:2],cp.returncode,cp.stdout,flush=True)
    assert all(sha(ROOT/p)==v for p,v in hashes.items()),'Released sources changed'
    dump(REPORT/'commands.json',{'version':subprocess.check_output([CLI,'--version'],text=True).strip(),'commands':commands,'released_sources_unchanged':True})
    (DEST/'README.md').write_text('# J10 侧出线试装候选 C1\n\nPROTOTYPE / NOT FOR FABRICATION. 保持 P5R6 孔位、针序和铜线，仅变更 J10 封装及其本体规则区。原版不变。\n\n此目录用于暴露固定孔位替换的碰撞，不能因有原生文件就称为通过。真实 DRC/ERC 与几何结果在 ../reports/。未导出生产文件，完整机械插拔与线束仍待复核。\n')

if __name__=='__main__':main()
