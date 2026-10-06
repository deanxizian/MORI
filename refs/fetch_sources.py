#!/usr/bin/env python3
"""Archive selected primary-source files at an immutable, observed commit."""
import concurrent.futures,datetime,hashlib,json,pathlib,urllib.request,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
REPOS=['LuwuDynamics/rig_omni','m5stack/StackChan-BSP','stack-chan/stack-chan','jeremy-prt/bloub','78/xiaozhi-esp32','espressif/esp-sr','lvgl/lvgl','xinnan-tech/xiaozhi-esp32-server','espressif/esp-who']
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'MORI-source-audit/1.0'})
 with urllib.request.urlopen(req,timeout=35) as r:return r.read()
def fetch(repo):
 out={'repository':repo,'url':'https://github.com/'+repo,'usage':'REFERENCE_ONLY','retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  cache=ROOT/'.objects'/repo.replace('/','__');cache.parent.mkdir(exist_ok=True)
  if not cache.exists():
   subprocess.run(['git','clone','--filter=blob:none','--bare','--depth','1','https://github.com/'+repo+'.git',str(cache)],check=True,capture_output=True)
  sha=subprocess.check_output(['git','--git-dir='+str(cache),'rev-parse','HEAD'],text=True).strip();out['commit']=sha
  paths=subprocess.check_output(['git','--git-dir='+str(cache),'ls-tree','--name-only','-r',sha],text=True).splitlines()
  directory=ROOT/repo.replace('/','__');directory.mkdir(exist_ok=True)
  (directory/'tree.json').write_text(json.dumps(paths,indent=2))
  selected=[]
  for p in paths:
   low=p.lower()
   base=p.rsplit('/',1)[-1].lower()
   if '/' not in p and (base.startswith(('license','copying','readme')) or base in ['cmakelists.txt','package.json','sdkconfig.defaults']):selected.append(p)
   elif repo=='LuwuDynamics/rig_omni' and p.startswith('main/boards/hover/') and p.endswith(('.cc','.h','.cpp','.c','.json','.yml')):selected.append(p)
   elif repo=='jeremy-prt/bloub' and p.startswith('src/bot/') and p.endswith(('.ts','.tsx','.css','.json')):selected.append(p)
   elif repo=='78/xiaozhi-esp32' and (p in ['main/idf_component.yml','main/application.cc','docs/websocket.md'] or p.startswith('main/audio/') and p.endswith(('.cc','.h'))):selected.append(p)
   elif repo=='m5stack/StackChan-BSP' and any(k in low for k in ['servo','motor','head']) and p.endswith(('.hpp','.cpp','.h','.c')):selected.append(p)
   elif repo=='stack-chan/stack-chan' and any(k in low for k in ['servo','driver','limit']) and p.endswith(('.js','.ts')):selected.append(p)
   elif repo=='espressif/esp-sr' and (p in ['idf_component.yml','model/README.md'] or 'wn9' in low and p.endswith('.md')):selected.append(p)
   elif repo=='espressif/esp-who' and p.endswith('idf_component.yml'):selected.append(p)
   elif repo=='xinnan-tech/xiaozhi-esp32-server' and p.endswith(('protocol.py','requirements.txt')):selected.append(p)
  files={}
  for p in selected[:70]:
   try:
    content=get('https://raw.githubusercontent.com/'+repo+'/'+sha+'/'+p)
    target=directory/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    files[p]=hashlib.sha256(content).hexdigest()
   except Exception as e:files[p]={'error':str(e)}
  out['files']=files;out['status']='PASS'
 except Exception as e:out.update(status='BLOCKED',error=str(e))
 print(repo,out['status'],out.get('commit',''),flush=True);return out
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(fetch,REPOS))
 (ROOT/'sources.lock.json').write_text(json.dumps({'reference_only':True,'sources':results},indent=2)+'\n')
