"""Separate the right-edge bias courtyards by moving the lower resistor 0.5 mm.
Native geometry preview only; the original signal transfer is restored later
only through an exact plan and full native checks.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R164_bias_assignment.py').read_text().split('"""',2)[2]
s=s.replace("out=b/'R164-bias-assignment.json'","out=b/'R164-bias-assignment-v2.json'")
s=s.replace("[68.8,20.75]","[68.8,21.25]")
exec(compile(s,'R164_bias_native_courtyard_correction','exec'))
