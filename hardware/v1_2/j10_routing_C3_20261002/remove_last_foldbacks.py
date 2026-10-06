from candidate import *
b=load();changes=[]
ids=['454d4b9e-d7b1-436e-8773-b17371761f91','5af2903c-390d-4740-b61b-dc7918af0805','7d6f6ccd-20c6-4bcb-9b82-9d172d70b50f'];ts=[t for t in b.GetTracks()if t.m_Uuid.AsString()in ids];assert len(ts)==3
w=k.ToMM(ts[0].GetWidth());assert all(t.GetWidth()==ts[0].GetWidth()for t in ts)
pts=[(22.1,33.8),(21.4576,34.4424),(12.5984,34.4424)];g=Guard(b,'/+5V_CAM');assert all(g.line_clear(a,z,B,w)for a,z in zip(pts,pts[1:]))
for t in ts:b.Delete(t)
track(b,'/+5V_CAM',pts,w,B);assert len(clusters(b,'/+5V_CAM'))==1
changes.append({'net':'/+5V_CAM','new_B_route':pts,'width':w})
save(b);dump(R/'38_foldback_cleanup.json',changes);check('38_clean')
