from pathlib import Path
exec((Path(__file__).parent/'close_geometry_P5R7.py').read_text().split('routes=[')[0])
g=Guard(b,'/+3V3')
for y in [6.5,6.6,6.7,6.8,6.9,7,7.1,7.2,7.3]:
 print(y,[(x/20,y)for x in range(198,219)if g.via_clear((x/20,y))])
