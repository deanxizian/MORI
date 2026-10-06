from update_native_P5R7 import *
name,d,p=paths('motion');b=k.LoadBoard(str(p));changed=[]
for item in b.GetDrawings():
 if isinstance(item,k.PCB_TEXT)and 'P5R6' in item.GetText():
  old=item.GetText();item.SetText(old.replace('P5R6','P5R7'));changed.append({'old':old,'new':item.GetText()})
assert changed
k.SaveBoard(str(p),b);dump(HERE/'reports/motion/silkscreen_revision.json',changed)
