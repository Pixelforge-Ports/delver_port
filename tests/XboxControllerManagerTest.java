package org.portmaster.delver;

import com.badlogic.gdx.controllers.*;
import com.badlogic.gdx.math.Vector3;
import com.badlogic.gdx.utils.Array;

/** Check event delivery and polling without a window, native devices or game data. */
public final class XboxControllerManagerTest {
 static final class Device implements Controller {
  final String name;
  final float[] axes={0,0,-1,0,0,-1};
  final boolean[] buttons=new boolean[11];
  final Array<ControllerListener> listeners=new Array<ControllerListener>();
  Device(String name){this.name=name;}
  void move(int n,float value){axes[n]=value;for(ControllerListener l:listeners)l.axisMoved(this,n,value);}
  void press(int n,boolean value){buttons[n]=value;for(ControllerListener l:listeners){if(value)l.buttonDown(this,n);else l.buttonUp(this,n);}}
  public boolean getButton(int n){return buttons[n];}
  public float getAxis(int n){return axes[n];}
  public PovDirection getPov(int n){return PovDirection.center;}
  public boolean getSliderX(int n){return false;}
  public boolean getSliderY(int n){return false;}
  public Vector3 getAccelerometer(int n){return Vector3.Zero;}
  public void setAccelerometerSensitivity(float value){}
  public String getName(){return name;}
  public void addListener(ControllerListener l){listeners.add(l);}
  public void removeListener(ControllerListener l){listeners.removeValue(l,true);}
 }
 static final class Backend implements ControllerManager {
  final Array<Controller> controllers=new Array<Controller>();
  final Array<ControllerListener> listeners=new Array<ControllerListener>();
  public Array<Controller> getControllers(){return controllers;}
  public void addListener(ControllerListener l){listeners.add(l);}
  public void removeListener(ControllerListener l){listeners.removeValue(l,true);}
  public Array<ControllerListener> getListeners(){return listeners;}
  public void clearListeners(){listeners.clear();}
  void connect(Device d){controllers.add(d);for(ControllerListener l:listeners)l.connected(d);}
  void disconnect(Device d){controllers.removeValue(d,true);for(ControllerListener l:listeners)l.disconnected(d);}
 }
 static final class Events extends ControllerAdapter {
  int axis=-1,button=-1,connected,disconnected;
  float value;
  Controller controller;
  @Override public boolean axisMoved(Controller c,int n,float v){controller=c;axis=n;value=v;return false;}
  @Override public boolean buttonDown(Controller c,int n){controller=c;button=n;return false;}
  @Override public void connected(Controller c){connected++;}
  @Override public void disconnected(Controller c){disconnected++;}
 }
 static void check(boolean ok,String what){if(!ok)throw new AssertionError(what);}
 static void equal(float actual,float expected,String what){check(Math.abs(actual-expected)<.0001f,what+": "+actual+" != "+expected);}
 public static void main(String[] args){
  Backend backend=new Backend();
  Device physical=new Device("muOS-Keys"),xbox=new Device("Microsoft X-Box 360 pad");
  backend.controllers.add(physical);backend.controllers.add(xbox);
  XboxControllerManager manager=new XboxControllerManager(backend);
  check(manager.getControllers().size==1,"Expose only the gptokeyb2 Xbox device");
  Controller pad=manager.getControllers().first();
  Events global=new Events(),local=new Events();
  manager.addListener(global);pad.addListener(local);
  physical.move(0,.75f);
  check(global.axis==-1,"Ignore duplicate physical-pad events");
  // All eight directions must keep their signs and reach the correct legacy axis.
  int[] raw={0,1,3,4},legacy={1,0,3,2};
  for(int i=0;i<raw.length;i++)for(float value:new float[]{-.75f,.75f}){
   xbox.move(raw[i],value);
   check(global.axis==legacy[i]&&local.axis==legacy[i],"Stick axis order");
   check(global.controller==pad&&local.controller==pad,"Wrapped controller identity");
   equal(global.value,value,"Stick event direction");
   equal(pad.getAxis(legacy[i]),value,"Stick polling direction");
   xbox.move(raw[i],0);
  }
  equal(pad.getAxis(4),0,"Neutral triggers");
  xbox.move(2,1);equal(global.value,1,"Left trigger");equal(pad.getAxis(4),1,"Left trigger polling");
  xbox.move(2,-1);equal(global.value,0,"Left trigger release");
  xbox.move(5,1);equal(global.value,-1,"Right trigger");equal(pad.getAxis(4),-1,"Right trigger polling");
  xbox.move(2,1);equal(global.value,0,"Both triggers");
  xbox.move(2,-1);xbox.move(5,-1);equal(global.value,0,"Both triggers released");
  for(int rawButton:new int[]{0,7,9,10}){
   int expected=rawButton<8?rawButton:rawButton-1;
   xbox.press(rawButton,true);
   check(global.button==expected&&pad.getButton(expected),"Button translation "+rawButton);
   xbox.press(rawButton,false);check(!pad.getButton(expected),"Button release");
  }
  global.button=-1;xbox.press(8,true);check(global.button==-1,"Guide does not become left-stick click");
  Device extra=new Device("DeviceHub Gamepad");backend.connect(extra);
  check(manager.getControllers().size==1&&global.connected==0,"Ignore generic pads at hotplug");
  backend.disconnect(xbox);
  check(manager.getControllers().size==0&&global.disconnected==1,"Xbox disconnect");
  backend.connect(xbox);
  check(manager.getControllers().size==1&&global.connected==1,"Xbox reconnect");
  System.out.println("XBOX_LAYOUT_OK eight stick directions, triggers, buttons, duplicate filtering and hotplug");
 }
}
