import json,pathlib,urllib.request
images={'python':'3.12.10-slim-bookworm','caddy':'2.10.0-alpine'};out={}
for image,tag in images.items():
 token=json.load(urllib.request.urlopen(f'https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/{image}:pull'))['token']
 req=urllib.request.Request(f'https://registry-1.docker.io/v2/library/{image}/manifests/{tag}',headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json'})
 with urllib.request.urlopen(req,timeout=20) as r:out[image]={'tag':tag,'digest':r.headers['Docker-Content-Digest'],'source':'https://registry-1.docker.io','status':'PASS'}
p=pathlib.Path('backend/images.lock.json');p.write_text(json.dumps(out,indent=2))
f=pathlib.Path('backend/Dockerfile');f.write_text(f.read_text().replace('FROM python:'+images['python'],'FROM python:'+images['python']+'@'+out['python']['digest']))
f=pathlib.Path('backend/compose.yaml');f.write_text(f.read_text().replace('image: caddy:'+images['caddy'],'image: caddy:'+images['caddy']+'@'+out['caddy']['digest']))
