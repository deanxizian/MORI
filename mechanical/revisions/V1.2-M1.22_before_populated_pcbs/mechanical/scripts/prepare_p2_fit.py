"""Read-only P2 PCB inventory and populated STEP export for a mechanical study.

Run with KiCad's bundled Python (pcbnew). Does not save or alter PCB files.
The P2 power layout is historical and is NOT the new S3 layout.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import pcbnew

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / 'mechanical/studies/pcb_P2_fit'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
LIBRARY = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')
OUT.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

report = {'purpose': 'Previous P2 mechanical fit audit; no electrical layout changes',
          'kicad_version': subprocess.check_output([CLI, 'version'], text=True).strip(),
          'units': 'mm', 'pcb_coordinates': '+X right, +Y down, front components +Z',
          'step_coordinates': '+X right, PCB Y negated; verify board Z against exported solid',
          'power_S3_status': json.loads((PROJECT/'hardware/v1_2/handoff/mechanical_S3.json').read_text()),
          'components_contract_sha256': sha(PROJECT/'contracts/components.json'),
          'source_assembly_sha256': sha(PROJECT/'mechanical/mori_v1_2.blend'),
          'boards': {}, 'commands': []}
for kind in ['motion', 'imu', 'power']:
    path = PROJECT/f'hardware/v1_2/kicad/MORI_{kind}_P2/MORI_{kind}_P2.kicad_pcb'
    board = pcbnew.LoadBoard(str(path))
    footprints = []
    for fp in board.GetFootprints():
        models = []
        for m in fp.Models():
            resolved = Path(str(m.m_Filename).replace('${KICAD10_3DMODEL_DIR}', str(LIBRARY)))
            models.append({'path': str(m.m_Filename), 'resolved': str(resolved),
                           'exists': resolved.is_file(), 'sha256': sha(resolved) if resolved.is_file() else None})
        pads = [{'number': p.GetNumber(), 'xy_mm': [p.GetPosition().x/1e6, p.GetPosition().y/1e6],
                 'drill_xy_mm': [p.GetDrillSize().x/1e6, p.GetDrillSize().y/1e6]} for p in fp.Pads()]
        footprints.append({'reference': fp.GetReference(), 'value': fp.GetValue(),
                           'footprint': str(fp.GetFPID().GetLibItemName()),
                           'xy_mm': [fp.GetPosition().x/1e6, fp.GetPosition().y/1e6],
                           'rotation_deg': fp.GetOrientationDegrees(),
                           'side': 'B' if fp.IsFlipped() else 'F', 'models': models, 'pads': pads})
    edges = []
    for item in board.GetDrawings():
        if item.GetLayer() == pcbnew.Edge_Cuts:
            edges.append({'start_mm': [item.GetStart().x/1e6,item.GetStart().y/1e6],
                          'end_mm': [item.GetEnd().x/1e6,item.GetEnd().y/1e6]})
    target = OUT/f'MORI_{kind}_P2_POPULATED_LIBRARY.step'
    cmd = [CLI,'pcb','export','step','--force','--user-origin','0x0mm',
           '--define-var',f'KICAD10_3DMODEL_DIR={LIBRARY}','-o',str(target),str(path)]
    started = time.time()
    done = subprocess.run(cmd,capture_output=True,text=True)
    (OUT/f'export_{kind}.log').write_text(done.stdout+'\n'+done.stderr)
    report['commands'].append({'argv':cmd, 'exit_code':done.returncode,
                                'elapsed_s': round(time.time()-started,1)})
    if done.returncode: raise RuntimeError(done.stderr)
    report['boards'][kind] = {'source':str(path.relative_to(PROJECT)), 'source_sha256':sha(path),
                             'source_status':'NATIVE_DESIGN_NOT_MEASURED',
                             'thickness_mm':board.GetDesignSettings().GetBoardThickness()/1e6,
                             'edge_cuts':edges, 'footprints':footprints,
                             'step':str(target.relative_to(PROJECT)), 'step_sha256':sha(target),
                             'limitations':'KiCad library solids at native footprint coordinates. No unmodeled cable, solder, mating plug or socket is asserted exact. U100 has no linked model; imported separately from manufacturer CAD.'}
    print('EXPORTED', kind, len(footprints), flush=True)
(OUT/'native_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('P2_INVENTORY_COMPLETE',flush=True)
