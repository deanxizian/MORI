"""Replay unchanged M1.43 body assembly against independent candidate solids."""
from pathlib import Path
HERE_OUT=Path(__file__).resolve().parent
source=HERE_OUT.parent/'prearrival_closure/dual_body_sequence.py'
code=source.read_text().replace("(HERE/'dual_body_sequence.json')", repr(str(HERE_OUT/'body_sequence.json')))
code=code.replace("'"+str(HERE_OUT/'body_sequence.json')+"'.write_text", "Path("+repr(str(HERE_OUT/'body_sequence.json'))+").write_text")
code=code.replace("hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest()","hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()")
code=code.replace("no geometry changes.","Independent head-retention candidate; main remains unchanged.")
exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
