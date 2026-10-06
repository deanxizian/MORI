"""Rerun body/bridge sequence on current M1.44, including two bridge inserts."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'studies/prearrival_closure/dual_body_sequence.py'
code=source.read_text().replace("bridge={'Yaw_Base','Yaw_Bearing'}|select('Yaw_Base_-1_Nut','Yaw_Base_1_Nut')", "bridge={'Yaw_Base','Yaw_Bearing'}|select('Yaw_Base_-1_Nut','Yaw_Base_1_Nut','Yaw_Keeper_Insert_')")
code=code.replace("(HERE/'dual_body_sequence.json')", "(PROJECT/'mechanical/reports/head_retention_body_sequence.json')").replace('no geometry changes.','M1.44 includes approved head retention; keeper installed after bridge is fixed.')
exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
