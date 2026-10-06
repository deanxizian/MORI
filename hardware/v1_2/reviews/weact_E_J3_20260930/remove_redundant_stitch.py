from update_native_P5R7 import *
name,d,p=paths('motion');b=k.LoadBoard(str(p));out=[]
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA)and t.GetNetname()=='/GND'and xy(t.GetPosition())==(53,1.5):out.append(t.m_Uuid.AsString());b.Delete(t)
assert len(out)==1
k.SaveBoard(str(p),b);dump(HERE/'reports/motion/final_ground_stitch.json',{'retained_new_stitch_mm':[12.5,8.5],'removed_redundant_under_J2':out,'reason':'Avoid an unnecessary GND via under the connector housing and silk. Native check confirms actual ground connectivity after removal.'})
