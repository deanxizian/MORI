"""Render full WDI pad-centre approach and Q1602 gate escape for local review."""
import json, subprocess, time
from pathlib import Path
b = Path('robot/.state/c3-completion/trials')
out = b / 'R148E-detail-views'
out.mkdir(exist_ok=False)
py = str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
cairo = '/Users/dean/.local/share/kicad-mcp/venv/bin/python'
records = []
for layer, net in [('F.Cu', '/16 {slash} Actuator_Direct_Switch/ACT_GATE'), ('B.Cu', '/01 {slash} Core/WDI')]:
    svg, png = out / (layer + '.svg'), out / (layer + '.png')
    commands = [
        [py, 'robot/hardware/driver/development/scripts/render_inspection.py', str(b / 'R148E/MORI_Interface_C3.kicad_pcb'), layer, '34.5', '3.8', '40', '10.5', str(svg), '--highlight', net],
        [cairo, '-c', 'import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])', str(svg), str(png)],
    ]
    for args in commands:
        started = time.time()
        r = subprocess.run(args, capture_output=True, text=True)
        records.append(dict(argv=args, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr, seconds=time.time() - started))
        (out / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        assert r.returncode == 0
