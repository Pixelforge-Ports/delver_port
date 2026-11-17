package org.portmaster.delver;

import com.badlogic.gdx.controllers.*;
import com.badlogic.gdx.controllers.lwjgl3.Lwjgl3ControllerManager;
import com.badlogic.gdx.math.Vector3;
import com.badlogic.gdx.utils.Array;
import com.badlogic.gdx.utils.ObjectMap;

/** Translate Linux Xbox axes to the older layout used by Delver v1.08. */
public final class XboxControllerManager implements ControllerManager {
 private final Array<Controller> controllers=new Array<Controller>();
 private final Array<ControllerListener> listeners=new Array<ControllerListener>();
 private final ObjectMap<Controller,Pad> pads=new ObjectMap<Controller,Pad>();

 public XboxControllerManager(){this(new Lwjgl3ControllerManager());}
 XboxControllerManager(ControllerManager backend){
  for(Controller source:backend.getControllers())connect(source,false);
  backend.addListener(new ControllerAdapter(){
   @Override public void connected(Controller source){connect(source,true);}
   @Override public void disconnected(Controller source){
    Pad pad=pads.remove(source);
    if(pad==null)return;
    source.removeListener(pad.relay);
    controllers.removeValue(pad,true);
    for(ControllerListener listener:listeners)listener.disconnected(pad);
   }
  });
 }
 private void connect(Controller source,boolean notify){
  // Use the device made by gptokeyb2 -x, avoiding duplicate physical-pad events.
  if(!"Microsoft X-Box 360 pad".equals(source.getName())||pads.containsKey(source))return;
  Pad pad=new Pad(source);
  pads.put(source,pad);
  controllers.add(pad);
  if(notify)for(ControllerListener listener:listeners)listener.connected(pad);
 }
 @Override public Array<Controller> getControllers(){return controllers;}
 @Override public void addListener(ControllerListener listener){listeners.add(listener);}
 @Override public void removeListener(ControllerListener listener){listeners.removeValue(listener,true);}
 @Override public Array<ControllerListener> getListeners(){return listeners;}
 @Override public void clearListeners(){listeners.clear();}

 private interface Event {boolean send(ControllerListener listener);}
 private final class Pad implements Controller {
  private final Controller source;
  private final Array<ControllerListener> local=new Array<ControllerListener>();
  private final ControllerAdapter relay;
  Pad(Controller source){
   this.source=source;
   relay=new ControllerAdapter(){
    @Override public boolean buttonDown(Controller c,int n){
     final int mapped=button(n);return mapped>=0&&fire(l->l.buttonDown(Pad.this,mapped));
    }
    @Override public boolean buttonUp(Controller c,int n){
     final int mapped=button(n);return mapped>=0&&fire(l->l.buttonUp(Pad.this,mapped));
    }
    @Override public boolean axisMoved(Controller c,int n,float value){
     final int mapped=axis(n);
     final float translated=(n==2||n==5)?getAxis(4):value;
     return mapped>=0&&fire(l->l.axisMoved(Pad.this,mapped,translated));
    }
    @Override public boolean povMoved(Controller c,int n,PovDirection value){return fire(l->l.povMoved(Pad.this,n,value));}
    @Override public boolean xSliderMoved(Controller c,int n,boolean value){return fire(l->l.xSliderMoved(Pad.this,n,value));}
    @Override public boolean ySliderMoved(Controller c,int n,boolean value){return fire(l->l.ySliderMoved(Pad.this,n,value));}
    @Override public boolean accelerometerMoved(Controller c,int n,Vector3 value){return fire(l->l.accelerometerMoved(Pad.this,n,value));}
   };
   source.addListener(relay);
  }
  private boolean fire(Event event){
   boolean handled=false;
   for(ControllerListener listener:local)handled|=event.send(listener);
   for(ControllerListener listener:listeners)handled|=event.send(listener);
   return handled;
  }
  private int axis(int raw){
   switch(raw){case 0:return 1;case 1:return 0;case 3:return 3;case 4:return 2;case 2:case 5:return 4;default:return -1;}
  }
  private int button(int raw){
   if(raw<8)return raw;
   return raw==9?8:raw==10?9:-1;
  }
  @Override public float getAxis(int legacy){
   switch(legacy){
    case 0:return source.getAxis(1);
    case 1:return source.getAxis(0);
    case 2:return source.getAxis(4);
    case 3:return source.getAxis(3);
    // The original backend presents both triggers on one signed axis.
    case 4:return (source.getAxis(2)-source.getAxis(5))*.5f;
    default:return 0;
   }
  }
  @Override public boolean getButton(int legacy){return legacy>=0&&legacy<10&&source.getButton(legacy<8?legacy:legacy+1);}
  @Override public PovDirection getPov(int n){return source.getPov(n);}
  @Override public boolean getSliderX(int n){return source.getSliderX(n);}
  @Override public boolean getSliderY(int n){return source.getSliderY(n);}
  @Override public Vector3 getAccelerometer(int n){return source.getAccelerometer(n);}
  @Override public void setAccelerometerSensitivity(float value){source.setAccelerometerSensitivity(value);}
  @Override public String getName(){return source.getName();}
  @Override public void addListener(ControllerListener listener){local.add(listener);}
  @Override public void removeListener(ControllerListener listener){local.removeValue(listener,true);}
 }
}
