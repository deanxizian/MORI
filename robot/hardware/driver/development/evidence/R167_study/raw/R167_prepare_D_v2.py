"""Keep the initial D preflight rejection and widen the two pin-corner turns."""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');code=(b/'R167_prepare_D.py').read_text()
changes={
 '[[59.35,12.575],[59.35,15.7375],[58.7,16.3875]]':'[[59.35,12.575],[59.35,16.1],[59.0625,16.3875],[58.7,16.3875]]',
 '[57.35,13.1],[56.5,13.1],[55.3,14.3]':'[57.35,13.1],[56.25,13.1],[55.3,14.05]',
 "b/'R167D-route-preflight.json'":"b/'R167D-route-preflight-v2.json'",
}
for old,new in changes.items():
 assert code.count(old)==1,old
 code=code.replace(old,new)
exec(compile(code,str(__file__),'exec'))
