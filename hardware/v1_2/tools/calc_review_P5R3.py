"""Recompute the documented provisional barrel-only DC budget; no CAD writes."""
from pathlib import Path
import json,math
p=Path(__file__).resolve().parents[1]/'layout_P5R3/reports/power/parallel_via_model.json'
for q in json.loads(p.read_text()):
 rho=1.724e-5*(1+.00393*(q['assumed_temperature_C']-20))
 r=rho*1.6/(math.pi*q['drill_mm']*q['assumed_barrel_plating_mm']);n=len(q['centres_mm']);i=q['scenario_A']
 assert abs(i*r/n*1000-q['ideal_parallel_mV'])<1e-9
 assert i*r/(n-1)*1000<=5
 print(f"{q['id']:18s} N={n}  all={i*r/n*1000:.3f} mV  one_absent={i*r/(n-1)*1000:.3f} mV")
print('Barrel-only DC design scenario. NOT_TESTED thermal/current rating; not manufacturing approval.')
