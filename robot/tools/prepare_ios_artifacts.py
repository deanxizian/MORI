"""Optional mirror of exact official Capacitor 7.2.0 binary archives for local SPM.
No bypass of hashes. Package.swift in the generated Xcode checkout is a local cache
only; committed app Package.resolved stays pinned to upstream 7.2.0.
"""
import pathlib,hashlib,subprocess,zipfile,re,json
root=pathlib.Path(__file__).resolve().parents[1]
checkout=root/'.state/ios-build/SourcePackages/checkouts/capacitor-swift-pm'
manifest=checkout/'Package.swift';text=manifest.read_text();evidence=[]
for name,sha in [('Capacitor','368d25296b2b210c86aa4273c4792ef045bb9f6b2c4dcbb9bb7b9f2984f1cfd0'),('Cordova','79a96f814717d7b87aba0f514ed28cd0babd31343c9cc615939b43559f0b10a1')]:
 url=f'https://github.com/ionic-team/capacitor-swift-pm/releases/download/7.2.0/{name}.xcframework.zip';archive=root/'.state'/f'{name}-7.2.0.zip'
 subprocess.run(['curl','-fL','--retry','2','--max-time','60',url,'-o',str(archive)],check=True)
 actual=hashlib.sha256(archive.read_bytes()).hexdigest()
 if actual!=sha:raise SystemExit('CHECKSUM MISMATCH')
 with zipfile.ZipFile(archive) as z:
  for info in z.infolist():
   if pathlib.PurePosixPath(info.filename).is_absolute() or '..' in pathlib.PurePosixPath(info.filename).parts:raise ValueError('unsafe archive')
  z.extractall(checkout)
 text=re.sub(r'url: "'+re.escape(url)+r'",\s*checksum: "'+sha+r'"','path: "'+name+'.xcframework"',text)
 evidence.append({'url':url,'sha256':actual,'status':'PASS'})
manifest.chmod(0o644);manifest.write_text(text);(root/'reports/v1/ios_artifact_verification.json').write_text(json.dumps(evidence,indent=2))
