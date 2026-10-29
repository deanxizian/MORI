"""Build a complete 270-degree alternative with 0.10 mm more upper escape room.

All eight part poses come from the expanded native search except the explicit
0.10 mm downward IC adjustment. The adjustment and all original acceptance
constraints require native validation. Preserve source supply branches; only
the lower 3V3 transfer moves. No source/accepted board is overwritten.
"""
from pathlib import Path
src=Path('robot/.state/c3-completion/trials/R174_prepare_A.py').read_text()
src=src.replace('R174A','R174B').replace('R174-ranked-placement.json','R174-expanded-placement.json')
src=src.replace("chosen=screen['solutions'][0]", "chosen=next(r for r in screen['solutions'] if r['parts'][0]['rotation_deg']==270)\nu=chosen['parts'][0];u['position_mm'][1]=12.35\nfor p in u['pads'].values():p['position_mm'][1]=round(p['position_mm'][1]+.1,6)")
src=src.replace('xfact=-1,yfact=1,origin=old','xfact=-1,yfact=1,origin=tuple(old)')
src=src.replace("'bc3e9793-b9cd-54b1-b44c-64b91f6e9a06','65bcfb8b-ccb8-414b-9655-86c9c7b51068','faea7b4d-249a-47b7-8402-16bf75873e0c','dcb2b41a-82bd-47f9-9a25-09dbdf14ff28','7c457b1b-8640-4205-8467-6ef9cfeae45d','1d4ee9c6-471f-4c4a-bbb3-a128d5d11e6d'", "'bc3e9793-b9cd-54b1-b44c-64b91f6e9a06'")
exec(compile(src,'R174_prepare_B.py','exec'))
