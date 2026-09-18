"""Run a Windows desktop compatibility check with isolated saves, never a handheld test."""
import argparse,json,os,struct,subprocess
from pathlib import Path
from build import ROOT,dependencies
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--java',type=Path,required=True);p.add_argument('--game-jar',type=Path,required=True);p.add_argument('--all-resolutions',action='store_true');p.add_argument('--width',type=int);p.add_argument('--height',type=int);p.add_argument('--audio',action='store_true');a=p.parse_args()
if os.name!='nt':p.error('This smoke helper currently uses Windows test natives; the shipping package uses ARM64 Linux natives.')
entries=dependencies(testing=True)
cp=[str(ROOT/'package/delver/runtime/delver-host.jar')]
cp += [str(x) for x in sorted((ROOT/'package/delver/runtime/lib').glob('*.jar')) if 'linux-arm64' not in x.name and x.name!='gdx-arm64-natives.jar']
cp += [str(ROOT/'build/dependencies'/e['name']) for e in entries if e['role'] in ['test','native-source']]
cp += [str(a.game_jar.resolve())]
if (a.width is None) != (a.height is None):p.error('--width and --height must be used together')
sizes=[(640,480),(720,480),(720,720),(1024,768),(1280,720)] if a.all_resolutions else [(a.width,a.height) if a.width else (640,480)]
for w,h in sizes:
 folder=ROOT/'build/smoke'/('%dx%d'%(w,h));folder.mkdir(parents=True,exist_ok=True)
 command=[str(a.java.resolve()),'--add-opens=java.base/java.lang=ALL-UNNAMED','--add-opens=java.base/java.util=ALL-UNNAMED','-Xmx384m','-Ddelver.hidden=true','-Ddelver.noAudio='+str(not a.audio).lower(),'-Ddelver.smokeFrames=360','-Ddelver.smokeGameplay=true','-Ddelver.width='+str(w),'-Ddelver.height='+str(h),'-Ddelver.jar='+str(a.game_jar.resolve()),'-Ddelver.capture='+str(folder/'gameplay.png'),'-cp',os.pathsep.join(cp),'org.portmaster.delver.Main']
 with (folder/'run.log').open('w',encoding='utf-8') as log:subprocess.run(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
 text=(folder/'run.log').read_text()
 assert 'GAMEPLAY_ENTERED' in text and 'SMOKE_OK' in text,text[-3000:]
 assert struct.unpack('>II',(folder/'gameplay.png').read_bytes()[16:24])==(w,h)
 assert (folder/'save/options.txt').is_file()
 assert any(x.name.startswith('game_') and x.suffix=='.dat' for x in (folder/'save').rglob('*')),'No game save generated'
 print('DESKTOP_SMOKE_OK',w,h,flush=True)
