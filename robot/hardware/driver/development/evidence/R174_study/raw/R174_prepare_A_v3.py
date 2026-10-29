"""Retain only C1701's outward/upward original ground branch.

v2 identified a source diagonal across the unchanged nominal capacitor body;
do not reinstate it or its dangling horizontal stub in this candidate.
"""
from pathlib import Path
src=Path('robot/.state/c3-completion/trials/R174_prepare_A.py').read_text()
src=src.replace('xfact=-1,yfact=1,origin=old','xfact=-1,yfact=1,origin=tuple(old)')
src=src.replace("'dcb2b41a-82bd-47f9-9a25-09dbdf14ff28','7c457b1b-8640-4205-8467-6ef9cfeae45d',",'')
exec(compile(src,'R174_prepare_A_v3.py','exec'))
