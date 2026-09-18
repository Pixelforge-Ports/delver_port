"""Build Delver.zip without Steam files. Python 3.9+ and a JDK 17+ are required."""
import argparse, hashlib, json, os, subprocess, urllib.request, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def put(archive,name,data):
 info=zipfile.ZipInfo(name,(2026,9,13,0,0,0));info.create_system=3
 info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
 archive.writestr(info,data)

def dependencies(offline=False,testing=False):
 entries=json.loads((ROOT/'tools/runtime-lock.json').read_text())
 folder=ROOT/'build/dependencies';folder.mkdir(parents=True,exist_ok=True)
 for e in entries:
  if e['role']=='test' and not testing:continue
  p=folder/e['name']
  if not p.exists():
   if offline:raise SystemExit('Missing cached dependency: '+p.name)
   with urllib.request.urlopen(e['url'],timeout=60) as response:data=response.read()
   if hashlib.sha256(data).hexdigest()!=e['sha256']:raise SystemExit('Download checksum mismatch: '+p.name)
   p.write_bytes(data)
  if hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:raise SystemExit('Cached checksum mismatch: '+p.name)
 return entries

def runtime(entries):
 folder=ROOT/'package/delver/runtime/lib';folder.mkdir(parents=True,exist_ok=True)
 names=[]
 for e in entries:
  if e['role']=='runtime':
   (folder/e['name']).write_bytes((ROOT/'build/dependencies'/e['name']).read_bytes());names.append(e['name'])
 native=next(e for e in entries if e['role']=='native-source')
 with zipfile.ZipFile(ROOT/'build/dependencies'/native['name']) as source,zipfile.ZipFile(folder/'gdx-arm64-natives.jar','w') as out:
  put(out,'libgdxarm64.so',source.read('libgdxarm64.so'))
 names.append('gdx-arm64-natives.jar')
 compat=next(e for e in entries if e['role']=='compat-source')
 with zipfile.ZipFile(ROOT/'build/dependencies'/compat['name']) as source,zipfile.ZipFile(folder/'gdx-matrix-compat.jar','w') as out:
  put(out,'com/badlogic/gdx/math/Matrix4.class',source.read('com/badlogic/gdx/math/Matrix4.class'))
 names.append('gdx-matrix-compat.jar')
 manifest=[dict(name=n,sha256=hashlib.sha256((folder/n).read_bytes()).hexdigest()) for n in sorted(names)]
 (ROOT/'build/runtime-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--jdk',type=Path,required=True);parser.add_argument('--offline',action='store_true')
 a=parser.parse_args();javac=a.jdk/'bin'/('javac.exe' if os.name=='nt' else 'javac')
 if not javac.is_file():parser.error('Compiler missing; pass your installed JDK folder in double quotes.')
 entries=dependencies(a.offline);runtime(entries)
 classes=ROOT/'build/classes';classes.mkdir(parents=True,exist_ok=True)
 for p in classes.rglob('*.class'):p.resolve().relative_to(classes.resolve());p.unlink()
 cp=os.pathsep.join(str(ROOT/'build/dependencies'/e['name']) for e in entries if e['name'] in ['gdx-1.9.9.jar','gdx-backend-lwjgl3-1.9.9.jar'])
 subprocess.run([str(javac),'--release','8','-Xlint:-options','-encoding','UTF-8','-cp',cp,'-d',str(classes),*map(str,sorted((ROOT/'src').rglob('*.java')))],check=True)
 with zipfile.ZipFile(ROOT/'package/delver/runtime/delver-host.jar','w') as out:
  for p in sorted(classes.rglob('*.class')):put(out,p.relative_to(classes).as_posix(),p.read_bytes())
 from portmaster_package import export
 export(ROOT)
 from verify_package import verify
 verify(ROOT)
if __name__=='__main__':main()
