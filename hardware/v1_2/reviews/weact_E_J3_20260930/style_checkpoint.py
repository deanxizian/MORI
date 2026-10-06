from update_native_P5R7 import *
import all_trace_review_P5R2 as a
import sys
q=HERE/'reports/motion'/sys.argv[1];out=HERE/'reports/motion/style_checkpoint';out.mkdir(exist_ok=True)
n,d,p=paths('motion')
a.paths=lambda kind:(n,d,q,out);a.source=lambda kind:paths(kind,'P5R6')
x=a.extract('motion','before');y=a.extract('motion','after')
old={(f['type'],f['net'],tuple(f['uuids']))for f in x['candidates']}
new=[f for f in y['candidates']if(f['type'],f['net'],tuple(f['uuids']))not in old]
print(json.dumps(new,indent=2));dump(out/'new.json',new)
