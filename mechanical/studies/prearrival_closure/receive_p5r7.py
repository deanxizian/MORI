"""Independent P5R7 receipt; no replacement of current source cache or config.

Run with KiCad Python for inventory/export, OCP Python for convert.
"""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'p5r7_receipt';OUT.mkdir(exist_ok=True)
mode=sys.argv[1]
if mode in ['inventory','export']:
    source=ROOT/'mechanical/scripts/prepare_populated_pcbs.py'
    ns={'__file__':str(source),'__name__':'receipt_library'}
    exec(compile(source.read_text(),str(source),'exec'),ns)
    ns['OUT']=OUT
    ns['HANDOFF']='hardware/v1_2/handoff/mechanical_P5R7.json'
    ns['RECEIVED']=json.loads((ROOT/ns['HANDOFF']).read_text())
    ns['BOARDS']={k:next(n for n in ns['RECEIVED']['boards'] if n.startswith('MORI_'+k+'_')) for k in ['motion','imu','power','rear']}
    ns[mode]()
elif mode=='convert':
    source=ROOT/'mechanical/scripts/convert_populated_pcbs.py'
    text=source.read_text();prefix,body=text.split("if __name__=='__main__':",1)
    ns={'__file__':str(source),'__name__':'receipt_library'}
    exec(compile(prefix,str(source),'exec'),ns);ns['OUT']=OUT
    import textwrap
    exec(compile(textwrap.dedent(body),str(source),'exec'),ns)
elif mode=='supplement':
    source=ROOT/'mechanical/scripts/supplement_populated_pcbs.py'
    sys.path.insert(0,str(ROOT/'mechanical/scripts'))
    # Parameterize only the output root in a read-only loaded copy. The native
    # reconstruction logic and all hardware files remain unmodified.
    code=source.read_text()
    expected="P=Path(__file__).resolve().parents[2];OUT=P/'mechanical/sources/populated_P5'"
    assert code.count(expected)==1
    code=code.replace(expected,"P=Path(__file__).resolve().parents[2];OUT=RECEIPT_OUT")
    exec(compile(code,str(source),'exec'),{'__file__':str(source),'__name__':'receipt_library','RECEIPT_OUT':OUT})
else:raise ValueError(mode)
