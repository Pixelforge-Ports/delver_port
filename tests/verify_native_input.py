"""Check the built host with zero or one native controller and no purchased game."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True)
    args = parser.parse_args()
    suffix = '.exe' if os.name == 'nt' else ''
    javac = args.jdk.resolve()/'bin'/('javac'+suffix)
    java = args.jdk.resolve()/'bin'/('java'+suffix)
    parent = ROOT/'build/native-input-tests'
    parent.mkdir(parents=True, exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix='run-', dir=parent))
    sources = {
        'com/interrupt/dungeoneer/input/GamepadBinding.java': '''
package com.interrupt.dungeoneer.input;
public final class GamepadBinding {
 public enum GamepadInputType {BUTTON,AXIS,POV}
 public final int number;
 public final GamepadInputType type;
 public GamepadBinding(int number,GamepadInputType type){this.number=number;this.type=type;}
}
''',
        'com/interrupt/dungeoneer/input/Actions.java': '''
package com.interrupt.dungeoneer.input;
public final class Actions {
 public enum Action {JUMP,MENU_CANCEL}
 public static final java.util.Hashtable<Action,GamepadBinding> gamepadBindings=new java.util.Hashtable<Action,GamepadBinding>();
 static{gamepadBindings.put(Action.MENU_CANCEL,new GamepadBinding(1,GamepadBinding.GamepadInputType.BUTTON));}
}
''',
        'com/interrupt/dungeoneer/input/GamepadDefinition.java': '''
package com.interrupt.dungeoneer.input;
public final class GamepadDefinition {
 public static final java.util.Hashtable<Actions.Action,GamepadBinding> gamepadBindings=new java.util.Hashtable<Actions.Action,GamepadBinding>();
}
''',
        'com/badlogic/gdx/controllers/Controllers.java': '''
package com.badlogic.gdx.controllers;
import com.badlogic.gdx.utils.Array;
public final class Controllers {
 public static final Array<Object> controllers=new Array<Object>();
 public static Array<Object> getControllers(){return controllers;}
}
''',
        'com/interrupt/dungeoneer/GameApplication.java': '''
package com.interrupt.dungeoneer;
import com.badlogic.gdx.ApplicationListener;
public final class GameApplication implements ApplicationListener {
 public static int creates,resizes,pauses,resumes,disposes;
 public void create(){creates++;}
 public void resize(int w,int h){if(w!=720||h!=480)throw new AssertionError();resizes++;}
 public void render(){}
 public void pause(){pauses++;}
 public void resume(){resumes++;}
 public void dispose(){disposes++;}
}
''',
        'com/interrupt/dungeoneer/game/Options.java': '''
package com.interrupt.dungeoneer.game;
public final class Options {
 public static int saves;
 public static void saveOptions(){saves++;}
}
''',
        'NativeInputProbe.java': '''
import com.badlogic.gdx.controllers.Controllers;
import com.interrupt.dungeoneer.GameApplication;
import com.interrupt.dungeoneer.game.Options;
import com.interrupt.dungeoneer.input.Actions;
import com.interrupt.dungeoneer.input.GamepadBinding;
import com.interrupt.dungeoneer.input.GamepadDefinition;
import org.portmaster.delver.Main;
public final class NativeInputProbe {
 public static void main(String[] args){
  System.setProperty("delver.mappedInput","false");
  int count=Integer.parseInt(args[0]);
  for(int i=0;i<count;i++)Controllers.controllers.add(new Object());
  Main host=new Main();
  host.create();host.resize(720,480);host.pause();host.resume();host.dispose();
  GamepadBinding jump=Actions.gamepadBindings.get(Actions.Action.JUMP);
  if(jump==null||jump.number!=1||jump.type!=GamepadBinding.GamepadInputType.BUTTON||
     GamepadDefinition.gamepadBindings.get(Actions.Action.JUMP)!=jump||
     Actions.gamepadBindings.get(Actions.Action.MENU_CANCEL).number!=1)
   throw new AssertionError("B must jump, remain in the defaults and still cancel menus");
  if(GameApplication.creates!=1||GameApplication.resizes!=1||GameApplication.pauses!=2||
     GameApplication.resumes!=1||GameApplication.disposes!=1||Options.saves!=1)
   throw new AssertionError("Native input must preserve the game lifecycle and saved options");
  System.out.println("NATIVE_INPUT_OK controllers="+count+"; B=Jump; B=menu cancel");
 }
}
''',
    }
    paths = []
    for name, text in sources.items():
        path = fixture/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        paths.append(str(path))
    classes = fixture/'classes'
    classes.mkdir()
    host = ROOT/'build/artifacts/delver-host.jar'
    dependencies = ROOT/'build/dependencies'
    classpath = os.pathsep.join(map(str, (
        host, dependencies/'gdx-1.9.9.jar', dependencies/'gdx-backend-lwjgl3-1.9.9.jar',
        dependencies/'gdx-controllers-1.9.9.jar', dependencies/'gdx-controllers-lwjgl3-1.9.9.jar',
    )))
    subprocess.run([str(javac),'--release','8','-Xlint:-options','-encoding','UTF-8','-cp',classpath,
                    '-d',str(classes),*paths,str(ROOT/'tests/XboxControllerManagerTest.java')], check=True)
    for count in (0,1):
        subprocess.run([str(java),'-cp',str(classes)+os.pathsep+classpath,
                        'NativeInputProbe',str(count)], check=True)
    subprocess.run([str(java),'-cp',str(classes)+os.pathsep+classpath,
                    'org.portmaster.delver.XboxControllerManagerTest'], check=True)


if __name__ == '__main__':
    main()
