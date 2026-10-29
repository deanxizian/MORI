"""Reference only byte-identical archived test-project members already preserved in native; original local trials untouched."""
import gzip,hashlib,json,shutil
from pathlib import Path
s=Path('robot/hardware/driver/development/evidence/R147_study');native=Path('robot/hardware/driver/development/native');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((s/'archive_manifest.json').read_text());keep=[];refs=[]
for r in m['payloads']:
 parts=Path(r['path']).parts
 if len(parts)>=4 and parts[0]=='raw' and parts[1] in ['R147-guard-checks','R147-guard-checks-v2']:
  rel=Path(*parts[3:]);rel=rel.with_name(rel.name[:-3]) if r['gzip'] else rel;target=native/rel
  if rel.name!='MORI_Interface_C3.kicad_pcb' and target.is_file() and sha(target)==r['source_sha256']:
   p=s/r['path'];data=gzip.decompress(p.read_bytes()) if r['gzip'] else p.read_bytes();assert hashlib.sha256(data).hexdigest()==sha(target);refs.append({'archived_test_member':str(Path(*parts[1:3])/rel),'native_member':str(rel),'sha256':sha(target),'bytes':len(data)});p.unlink();continue
 keep.append(r)
q=s/'R147_deduplicate_archive.py';assert not q.exists();shutil.copyfile(__file__,q);keep.append({'path':q.name,'sha256':sha(q),'source_sha256':sha(q),'source_bytes':q.stat().st_size,'gzip':False})
m['payloads']=keep;m['native_member_references']=refs;m['deduplication_scope']=__doc__;(s/'archive_manifest.json').write_text(json.dumps(m,indent=2)+'\n')
for r in keep:
 p=s/r['path'];assert sha(p)==r['sha256'];assert hashlib.sha256(gzip.decompress(p.read_bytes()) if r['gzip'] else p.read_bytes()).hexdigest()==r['source_sha256']
for r in refs:assert sha(native/r['native_member'])==r['sha256']
(s/'archive_verification.json').write_text(json.dumps({'status':'PASS','payload_count':len(keep),'referenced_unchanged_native_members':len(refs),'all_stored_and_original_byte_hashes_match':True,'source_local_trials_untouched':True},indent=2)+'\n')
p=s/'README.md';p.write_text(p.read_text()+'\n测试工程中与当前 `native/` 完全相同的非 PCB 成员用逐项哈希引用保存，避免重复归档厂家/原理图副本；原本机测试目录、所有原生测试板、差异文件和失败日志均保留。复原时按 manifest 的 `native_member_references` 拷贝对应原字节。\n')
print(json.dumps({'payloads':len(keep),'identical_native_member_references':len(refs)}))
