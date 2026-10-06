"""Independent PH finished-hole correction candidates. KiCad Python required.

Never modifies formal boards, mechanical geometry or the J10 side-entry C2.
Initial changes are pad/drill/library identity only; all interfaces remain fixed.
"""
from pathlib import Path
import collections
import hashlib
import json
import shutil
import subprocess
import sys

import pcbnew as k
import wx

app=wx.App(False)
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
REVS={'motion':'P5R7','power':'P5R6','rear':'P5R7','imu':'P5R4'}
SUFFIX='PHC1'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def xy(p): return [round(k.ToMM(p.x),6),round(k.ToMM(p.y),6)]
def point(x,y): return k.VECTOR2I(k.FromMM(x),k.FromMM(y))
def fid(f): return str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName())
def paths(kind):
    base='MORI_'+kind+'_'+REVS[kind]
    name=base+'_'+SUFFIX
    source=ROOT/'hardware/v1_2/kicad'/base
    dest=HERE/'candidates'/name
    return base,name,source,dest


def snapshot(board):
    footprints={}
    for f in board.GetFootprints():
        footprints[f.GetReference()]=dict(xy_mm=xy(f.GetPosition()),angle_deg=f.GetOrientationDegrees(),
          layer=board.GetLayerName(f.GetLayer()),value=f.GetValue(),footprint=fid(f),
          pads=sorted([dict(number=p.GetNumber(),xy_mm=xy(p.GetPosition()),size_mm=xy(p.GetSize()),
                           drill_mm=xy(p.GetDrillSize()),net=p.GetNetname(),shape=int(p.GetShape()),
                           angle_deg=p.GetOrientationDegrees(),attribute=int(p.GetAttribute()))for p in f.Pads()],key=lambda q:q['number']))
    tracks={t.m_Uuid.AsString():dict(start=xy(t.GetStart()),end=xy(t.GetEnd()),width_mm=k.ToMM(t.GetWidth(k.F_Cu)if isinstance(t,k.PCB_VIA)else t.GetWidth()),
              layer=board.GetLayerName(t.GetLayer()),net=t.GetNetname(),kind='via'if isinstance(t,k.PCB_VIA)else'track',
              drill_mm=k.ToMM(t.GetDrillValue())if isinstance(t,k.PCB_VIA)else None)for t in board.GetTracks()}
    edges=sorted([dict(type=int(s.GetShape()),start=xy(s.GetStart()),end=xy(s.GetEnd()),width_mm=k.ToMM(s.GetWidth()))
                  for s in board.GetDrawings()if s.GetLayer()==k.Edge_Cuts],key=str)
    return dict(footprints=footprints,tracks=tracks,edges=edges,copper_layers=board.GetCopperLayerCount())


def init():
    assert not(HERE/'candidates').exists(),'Existing candidates must not be reset.'
    all_sources={};changes={};before={}
    for kind in REVS:
        base,name,source,dest=paths(kind)
        for p in source.rglob('*'):
            if not p.is_file()or p.suffix in ['.kicad_prl','.lck']or p.name.startswith('~'):continue
            all_sources[p.relative_to(ROOT).as_posix()]=sha(p)
            q=dest/p.relative_to(source).parent/p.name.replace(base,name)
            q.parent.mkdir(parents=True,exist_ok=True)
            data=p.read_bytes()
            if p.suffix in ['.kicad_sch','.kicad_pro']:data=data.replace(base.encode(),name.encode())
            q.write_bytes(data)
        pcb=dest/(name+'.kicad_pcb');b=k.LoadBoard(str(pcb));before[kind]=snapshot(b)
        replacements={};rows=[]
        for f in b.GetFootprints():
            old=fid(f)
            if 'JST_PH_'not in old:continue
            pads=[p for p in f.Pads()if p.GetAttribute()==k.PAD_ATTRIB_PTH]
            num=len(pads);assert 2<=num<=16
            hole,land=(.85,1.45)if num==2 else(.90,1.50)
            nickname,item=old.split(':',1);newitem=item+'__PHC1_H'+str(round(hole*100))+'_L'+str(round(land*100))
            new=nickname+':'+newitem;replacements[old]=new
            oldpads=before[kind]['footprints'][f.GetReference()]['pads']
            for pad in pads:pad.SetSize(point(land,land));pad.SetDrillSize(point(hole,hole))
            f.SetFPID(k.LIB_ID(nickname,newitem))
            lib=dest/'footprints'/(nickname+'.pretty')
            local=k.FootprintLoad(str(lib),item);assert local is not None,old
            for pad in local.Pads():
                if pad.GetAttribute()==k.PAD_ATTRIB_PTH:pad.SetSize(point(land,land));pad.SetDrillSize(point(hole,hole))
            local.SetFPID(k.LIB_ID(nickname,newitem))
            k.FootprintSave(str(lib),local)
            rows.append(dict(ref=f.GetReference(),pin_count=num,old_footprint=old,new_footprint=new,
                             old_pads=oldpads,finished_hole_nominal_mm=hole,proposed_finished_tolerance_mm=[-.05,0],
                             finished_window_mm=[round(hole-.05,2),hole],copper_land_mm=land,
                             drawn_annulus_mm=round((land-hole)/2,3),fabricator_tolerance_confirmed=False))
        for p in [dest/(name+'.kicad_sch'),dest/'MORI.kicad_sym',dest/'assembly_bom.csv',dest/'connectivity.json']:
            text=p.read_text()
            # Simultaneous replacement avoids replacing a short base id inside
            # longer custom ids a second time.
            import re
            matcher=re.compile('|'.join(re.escape(x)for x in sorted(replacements,key=len,reverse=True)))
            text=matcher.sub(lambda m:replacements[m.group(0)],text)
            p.write_text(text)
        b.GetTitleBlock().SetRevision(REVS[kind]+'-'+SUFFIX+' / CANDIDATE / NOT FOR FABRICATION')
        b.GetTitleBlock().SetTitle('MORI '+kind+' PH finished-hole correction / independent candidate')
        k.SaveBoard(str(pcb),b)
        changes[kind]=rows
        (dest/'README.md').write_text('# PHC1 成品孔修正独立候选\n\nPROTOTYPE / NOT RELEASED。保持正式板接口位置、针序、朝向、板框和电路。只在此候选中修正 PH 孔径/铜盘及必要邻线；不包含电源 J10 侧出线 C2。成品孔公差与插装未验证，不得制造。检查与逐项差异见 ../../README.md。\n')
    dump(HERE/'formal_source_hashes.json',all_sources)
    dump(HERE/'before_snapshot.json',before)
    dump(HERE/'pad_changes.json',changes)
    dump(HERE/'proposal.json',dict(date='2026-10-02',status='BLOCKED',source='https://www.jst.com/resources/faq/',
      source_local='hardware/v1_2/prearrival_20261002/j10_refinement_C2/jst_faq.html',
      source_sha256=sha(ROOT/'hardware/v1_2/prearrival_20261002/j10_refinement_C2/jst_faq.html'),
      rationale='JST glass-epoxy plated-hole finished dimensions. Drawn annulus retained0.30mm; manufactured annulus also depends on tool/plating/registration.',
      nominal_holes_mm={'2P':.85,'3_to_16P':.90},land_diameters_mm={'2P':1.45,'3_to_16P':1.50},
      proposed_finished_hole_tolerance_mm=[-.05,0],fabricator_capability='BLOCKED',physical_tests='NOT_TESTED',
      manufacturing_release=False,formal_boards_replaced=False))
    print('Created four independent candidates;',sum(map(len,changes.values())),'PH footprints.',flush=True)


def check(kind,label='initial'):
    _,name,_,dest=paths(kind);report=HERE/'reports'/kind;report.mkdir(parents=True,exist_ok=True)
    commands=[]
    for typ in ['erc','drc']:
        infile=dest/(name+('.kicad_sch'if typ=='erc'else'.kicad_pcb'))
        out=report/(label+'_'+typ+'.json')
        argv=[CLI,'sch'if typ=='erc'else'pcb',typ,'--format','json','--severity-all','--exit-code-violations']
        if typ=='drc':argv+=['--all-track-errors','--schematic-parity','--refill-zones']
        argv+=['-o',str(out),str(infile)]
        cp=subprocess.run(argv,capture_output=True,text=True)
        commands.append(dict(argv=argv,returncode=cp.returncode,stdout=cp.stdout,stderr=cp.stderr,input_sha256=sha(infile)))
        if out.exists():
            d=json.loads(out.read_text());vs=d.get('violations',[])if typ=='drc'else[v for s in d['sheets']for v in s['violations']]
            print(kind,label,typ,cp.returncode,'types',dict(collections.Counter(v['type']for v in vs)),
                  'opens',len(d.get('unconnected_items',[])),'parity',len(d.get('schematic_parity',[])),flush=True)
    dump(report/(label+'_commands.json'),commands)


if __name__=='__main__':
    if sys.argv[1]=='init':init()
    elif sys.argv[1]=='check':check(sys.argv[2],sys.argv[3]if len(sys.argv)>3 else'initial')
