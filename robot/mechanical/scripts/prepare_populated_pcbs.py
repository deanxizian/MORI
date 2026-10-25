"""Read native, published PCB projects without altering hardware-owned sources.

Run with KiCad Python: inventory or export. All output is mechanical-owned.
Board layouts/holes are native design, library bodies are not measured hardware.
"""
from pathlib import Path
import json, hashlib, subprocess, datetime, sys
import pcbnew, wx
APP=wx.App(False)

PROJECT=Path(__file__).resolve().parents[2]
OUT=PROJECT/'mechanical/sources/populated_P5'
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
LIB=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')
PARAMS=json.loads((PROJECT/'config/geometry.json').read_text())
HANDOFF=PARAMS['native_electronics']['handoff']
RECEIVED=json.loads((PROJECT/HANDOFF).read_text())
BOARDS={k:next(n for n in RECEIVED['boards'] if n.startswith('MORI_'+k+'_'))
        for k in ['motion','imu','power','rear']}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def inventory():
    OUT.mkdir(parents=True,exist_ok=True)
    report={'units':'mm','native_axes':'+X right,+Y down,+Z front','STEP_axes':'+X right,+Y up; PCB exported from Z0 to thickness',
      'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'hardware_contract_revision':json.loads((PROJECT/'contracts/components.json').read_text())['revision'],
      'hardware_contract_sha256':sha(PROJECT/'contracts/components.json'),
      'handoff':HANDOFF,'boards':{},'kicad':pcbnew.Version()}
    for kind,name in BOARDS.items():
        src=PROJECT/f'hardware/v1_2/kicad/{name}/{name}.kicad_pcb';source_hash=sha(src)
        assert source_hash==RECEIVED['boards'][name]['pcb_sha256'], 'Native board differs from published handoff: '+name
        b=pcbnew.LoadBoard(str(src));fps=[]
        for fp in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
            models=[]
            for m in fp.Models():
                raw=str(m.m_Filename);path=raw.replace('${KICAD10_3DMODEL_DIR}',str(LIB)).replace('${KIPRJMOD}',str(src.parent))
                resolved=Path(path)
                if not resolved.is_absolute():resolved=src.parent/resolved
                models.append({'path':raw,'resolved':str(resolved),'exists':resolved.is_file(),
                  'sha256':sha(resolved) if resolved.is_file() else None,
                  'offset_mm':[m.m_Offset.x,m.m_Offset.y,m.m_Offset.z],
                  'rotation_deg':[m.m_Rotation.x,m.m_Rotation.y,m.m_Rotation.z],
                  'scale':[m.m_Scale.x,m.m_Scale.y,m.m_Scale.z]})
            fps.append({'reference':fp.GetReference(),'value':fp.GetValue(),'footprint':str(fp.GetFPID().GetLibItemName()),
              'xy_mm':[fp.GetPosition().x/1e6,fp.GetPosition().y/1e6], 'rotation_deg':fp.GetOrientationDegrees(),
              'side':'B' if fp.IsFlipped() else 'F','dnp':bool(fp.IsDNP()),'models':models,
              'fields':{f.GetName():f.GetText() for f in fp.GetFields()},
              'pads':[{'number':a.GetNumber(),'xy_mm':[a.GetPosition().x/1e6,a.GetPosition().y/1e6],
                'size_xy_mm':[a.GetSize().x/1e6,a.GetSize().y/1e6],
                'drill_xy_mm':[a.GetDrillSize().x/1e6,a.GetDrillSize().y/1e6]} for a in fp.Pads()]})
        edges=[{'start_mm':[e.GetStart().x/1e6,e.GetStart().y/1e6],'end_mm':[e.GetEnd().x/1e6,e.GetEnd().y/1e6],
                'shape':str(e.GetShape())} for e in b.GetDrawings() if e.GetLayer()==pcbnew.Edge_Cuts]
        snapshot=OUT/(name+'_READONLY.kicad_pcb')
        # Resolve paths in the copy, preserving every footprint, position and rotation.
        text=src.read_text()
        for fp in fps:
            for m in fp['models']:text=text.replace('"'+m['path']+'"','"'+m['resolved']+'"')
        snapshot.write_text(text)
        missing=[f['reference'] for f in fps if not f['dnp'] and not any(m['exists'] for m in f['models']) and not f['reference'].startswith(('H','TP'))]
        report['boards'][kind]={'name':name,'source':str(src.relative_to(PROJECT)),'source_sha256':source_hash,
          'snapshot':str(snapshot.relative_to(PROJECT)),'snapshot_sha256':sha(snapshot),'thickness_mm':b.GetDesignSettings().GetBoardThickness()/1e6,
          'edge_cuts':edges,'footprints':fps,'missing_models':missing,'dnp_references':[f['reference'] for f in fps if f['dnp']]}
        assert sha(src)==source_hash,'Native source changed during snapshot'
        print(kind,'footprints',len(fps),'missing',missing,flush=True)
    (OUT/'inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

def export():
    inv=json.loads((OUT/'inventory.json').read_text());records=[]
    for kind,b in inv['boards'].items():
        target=OUT/(kind+'.step');cmd=[CLI,'pcb','export','step','--force','--no-dnp','--subst-models','--user-origin','0x0mm',
            '--define-var',f'KICAD10_3DMODEL_DIR={LIB}','-o',str(target),str(PROJECT/b['snapshot'])]
        start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (OUT/(kind+'_export.log')).open('w') as f:done=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        records.append({'stage':kind,'command':cmd,'started_utc':start,'returncode':done.returncode,'step_sha256':sha(target) if target.exists() else None})
        (OUT/'export_commands.json').write_text(json.dumps(records,indent=2)+'\n')
        assert done.returncode==0,kind
        print('EXPORTED',kind,flush=True)

if __name__=='__main__':{'inventory':inventory,'export':export}[sys.argv[1]]()
