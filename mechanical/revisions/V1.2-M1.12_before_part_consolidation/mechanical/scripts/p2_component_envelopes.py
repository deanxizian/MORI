"""Vendor-dimension conservative envelopes for missing P2 library models.
AMASS2026 catalogue, printed page10: XT30UPB-M30 body10.2x5.6x10.7,
weld legs3mm. This is not an original detailed STEP or a mated connector.
"""
from common import *
SOURCE_URL='https://www.china-amass.com/public/upload/20260207/7fa24f5a6f35ec66c7a115c07a34ab06.pdf'
def missing_xt30_envelopes(inventory):
    result={}
    for fp in inventory['boards']['power']['footprints']:
        if 'XT30UPB-M' not in fp['footprint']:continue
        pads=[p for p in fp['pads'] if p['number'] in ['1','2']]
        assert len(pads)==2
        center=np.mean([p['xy_mm'] for p in pads],axis=0);center[1]*=-1
        rr=np.array(Matrix.Rotation(math.radians(fp['rotation_deg']),3,'Z'))
        body=manifold.Manifold.cube([10.2,5.6,10.7]).translate([-5.1,-2.8,1.56])
        body=body.transform(np.column_stack([rr,np.array([*center,0])]))
        pins=[manifold.Manifold.cylinder(3,.8,.8,32).translate([p['xy_mm'][0],-p['xy_mm'][1],1.56-3]) for p in pads]
        result[fp['reference']]=manifold.Manifold.batch_boolean([body]+pins,manifold.OpType.Add)
    return result
