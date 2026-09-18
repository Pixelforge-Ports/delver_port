package org.portmaster.delver;
import com.badlogic.gdx.*;
import com.badlogic.gdx.backends.lwjgl3.*;
import com.badlogic.gdx.graphics.*;
import com.badlogic.gdx.utils.GdxNativesLoader;
import java.nio.file.*;
import java.io.*;
import java.lang.reflect.*;

/** Starts the owner's unchanged game on an ARM-capable desktop backend. */
public final class Main implements ApplicationListener {
 private ApplicationListener game;
 private MappedInput mappedInput;
 private int frames;
 private long start, lastFrame;
 private final java.util.Set<com.badlogic.gdx.scenes.scene2d.ui.Table> fittedTables=java.util.Collections.newSetFromMap(new java.util.WeakHashMap<com.badlogic.gdx.scenes.scene2d.ui.Table,Boolean>());
 private boolean overlayFitFailed;
 public static void main(String[] args) throws Exception {
  VerifyGame.check(Paths.get(System.getProperty("delver.jar","delver.jar")));
  loadNatives();
  Class.forName("com.badlogic.gdx.controllers.Controllers").getField("preferredManager").set(null,"com.badlogic.gdx.controllers.ControllerManagerStub");
  Class.forName("com.interrupt.api.steam.SteamApi").getField("api").set(null,Class.forName("com.interrupt.api.steam.NullSteamApi").getDeclaredConstructor().newInstance());
  Class<?> options=Class.forName("com.interrupt.dungeoneer.game.Options");
  boolean fresh=!java.nio.file.Files.exists(Paths.get("save/options.txt"));
  options.getMethod("loadOptions").invoke(null);
  Object settings=options.getField("instance").get(null);
  if(fresh){
   options.getField("shadowsEnabled").setBoolean(settings,false);
   options.getField("fxaaEnabled").setBoolean(settings,false);
   options.getField("enablePostProcessing").setBoolean(settings,false);
   options.getField("graphicsDetailLevel").setInt(settings,1);
   options.getField("antiAliasingSamples").setInt(settings,0);
   options.getField("alwaysShowCrosshair").setBoolean(settings,true);
  }
  options.getField("fullScreen").setBoolean(settings,Boolean.getBoolean("delver.fullscreen"));
  options.getMethod("saveOptions").invoke(null);
  int width=Integer.getInteger("delver.width",640),height=Integer.getInteger("delver.height",480);
  if(width<160||height<160||width>8192||height>8192)throw new IllegalArgumentException("Invalid display dimensions");
  Lwjgl3ApplicationConfiguration cfg=new Lwjgl3ApplicationConfiguration();
  cfg.setTitle("Delver");cfg.setWindowedMode(width,height);cfg.setResizable(false);
  cfg.setBackBufferConfig(8,8,8,8,24,8,0);cfg.setIdleFPS(30);cfg.useVsync(false);
  cfg.disableAudio(Boolean.getBoolean("delver.noAudio"));cfg.setInitialVisible(!Boolean.getBoolean("delver.hidden"));
  if(Boolean.getBoolean("delver.fullscreen"))cfg.setFullscreenMode(Lwjgl3ApplicationConfiguration.getDisplayMode());
  new Lwjgl3Application(new Main(),cfg);
  System.exit(0);
 }
 private static void loadNatives() throws Exception {
  String arch=System.getProperty("os.arch"),os=System.getProperty("os.name");
  String name=os.startsWith("Windows")?"gdx64.dll":((arch.equals("aarch64")||arch.equals("arm64"))?"libgdxarm64.so":"libgdx64.so");
  Path directory=Paths.get(System.getProperty("java.io.tmpdir"),"delver-gdx-1.10.0");
  java.nio.file.Files.createDirectories(directory);Path nativeFile=directory.resolve(name);
  try(InputStream in=Main.class.getResourceAsStream("/"+name)){
   if(in==null)throw new IOException("Missing native runtime: "+name);
   if(!java.nio.file.Files.exists(nativeFile))java.nio.file.Files.copy(in,nativeFile);
  }
  System.load(nativeFile.toAbsolutePath().toString());GdxNativesLoader.disableNativesLoading=true;
 }
 @Override public void create(){
  try{
   if(Boolean.getBoolean("delver.mappedInput"))mappedInput=new MappedInput(Gdx.input);
   game=(ApplicationListener)Class.forName("com.interrupt.dungeoneer.GameApplication").getDeclaredConstructor().newInstance();
   game.create();
   configureKeyboardControls();
   int controllers=((com.badlogic.gdx.utils.Array<?>)Class.forName("com.badlogic.gdx.controllers.Controllers").getMethod("getControllers").invoke(null)).size;
   if(controllers!=0)throw new IllegalStateException("Direct controller input must be disabled");
   start=System.nanoTime();
   System.out.println("GAME_CREATE_OK Delver v1.08; offline; input=gptokeyb2 keyboard/mouse; native controllers=0; attack=R2; drop=L2; jump=B");
  }catch(Exception e){throw new RuntimeException(e);}
 }
 private static void configureKeyboardControls() throws Exception {
  Class<?> actions=Class.forName("com.interrupt.dungeoneer.input.Actions");
  Class<?> action=Class.forName("com.interrupt.dungeoneer.input.Actions$Action");
  Method valueOf=action.getMethod("valueOf",String.class);
  Object bindings=actions.getField("keyBindings").get(null);
  Method put=bindings.getClass().getMethod("put",Object.class,Object.class);
  String[] names={"FORWARD","BACKWARD","STRAFE_LEFT","STRAFE_RIGHT","USE","ATTACK","DROP","JUMP","INVENTORY","MAP","ITEM_PREVIOUS","ITEM_NEXT","PAUSE","MENU_SELECT","MENU_CANCEL"};
  int[] keys={Input.Keys.W,Input.Keys.S,Input.Keys.A,Input.Keys.D,Input.Keys.E,Input.Keys.CONTROL_LEFT,Input.Keys.Q,Input.Keys.SPACE,Input.Keys.I,Input.Keys.M,Input.Keys.LEFT_BRACKET,Input.Keys.RIGHT_BRACKET,Input.Keys.ESCAPE,Input.Keys.ENTER,Input.Keys.ESCAPE};
  for(int i=0;i<names.length;i++)put.invoke(bindings,valueOf.invoke(null,names[i]),keys[i]);
  Class<?> options=Class.forName("com.interrupt.dungeoneer.game.Options");
  options.getField("mouseButton1Action").set(options.getField("instance").get(null),valueOf.invoke(null,"ATTACK"));
 }
 private void fitOptionsOverlay(){
  if(overlayFitFailed)return;
  try{
   Class<?> manager=Class.forName("com.interrupt.dungeoneer.overlays.OverlayManager");
   Object overlay=manager.getMethod("current").invoke(manager.getField("instance").get(null));
   if(overlay==null)return;
   if(!overlay.getClass().getSimpleName().startsWith("Options"))return;
   Class<?> window=Class.forName("com.interrupt.dungeoneer.overlays.WindowOverlay");
   if(!window.isInstance(overlay))return;
   Field ui=Class.forName("com.interrupt.dungeoneer.overlays.Overlay").getDeclaredField("ui");
   ui.setAccessible(true);
   final com.badlogic.gdx.scenes.scene2d.Stage stage=(com.badlogic.gdx.scenes.scene2d.Stage)ui.get(overlay);
   final com.badlogic.gdx.scenes.scene2d.ui.Table table=(com.badlogic.gdx.scenes.scene2d.ui.Table)window.getField("stageTable").get(overlay);
   if(stage==null || table==null || fittedTables.contains(table))return;
   // Stage actions run after the game's option/resize updates, before drawing.
   table.addAction(new com.badlogic.gdx.scenes.scene2d.Action(){
    @Override public boolean act(float delta){
     com.badlogic.gdx.utils.viewport.Viewport viewport=stage.getViewport();
     int w=Gdx.graphics.getWidth(),h=Gdx.graphics.getHeight();
     if(w<=0 || h<=0)return false;
     float units=Math.max(viewport.getWorldWidth()/w,viewport.getWorldHeight()/h);
     units=Math.max(units,Math.max((table.getPrefWidth()+16f)/w,(table.getPrefHeight()+16f)/h));
     float worldWidth=w*units,worldHeight=h*units;
     if(Math.abs(viewport.getWorldWidth()-worldWidth)>0.01f || Math.abs(viewport.getWorldHeight()-worldHeight)>0.01f){
      viewport.setWorldSize(worldWidth,worldHeight);
      viewport.update(w,h,true);
      table.invalidateHierarchy();
     }
     return false;
    }
   });
   fittedTables.add(table);
   System.out.println("OPTIONS_FIT enabled: "+overlay.getClass().getSimpleName());
  }catch(Exception e){overlayFitFailed=true;System.err.println("OPTIONS_FIT failed: "+e);}
 }
 @Override public void resize(int w,int h){if(mappedInput!=null)mappedInput.install();if(game!=null)game.resize(w,h);}
 @Override public void render(){
  long now=System.nanoTime();
  while(lastFrame!=0 && now-lastFrame<16666667L){java.util.concurrent.locks.LockSupport.parkNanos(16666667L-(now-lastFrame));now=System.nanoTime();}
  lastFrame=now;
  if(mappedInput!=null)mappedInput.beginFrame();
  fitOptionsOverlay();
  game.render();
  if(mappedInput!=null)mappedInput.drawCursor();
  frames++;
  int smoke=Integer.getInteger("delver.smokeFrames",0);
  if(smoke>0 && frames==180 && Boolean.getBoolean("delver.smokeGameplay")) {
   try{Class.forName("com.interrupt.dungeoneer.GameApplication").getMethod("ShowMainScreen").invoke(null);System.out.println("GAMEPLAY_ENTERED");}
   catch(Exception e){throw new RuntimeException(e);}
  }
  if(smoke>0 && frames>=smoke){
   String capture=System.getProperty("delver.capture");
   if(capture!=null){Pixmap pix=com.badlogic.gdx.utils.ScreenUtils.getFrameBufferPixmap(0,0,Gdx.graphics.getBackBufferWidth(),Gdx.graphics.getBackBufferHeight());try{PixmapIO.PNG writer=new PixmapIO.PNG();try{writer.setFlipY(true);writer.write(Gdx.files.absolute(capture),pix);}catch(IOException e){throw new RuntimeException(e);}finally{writer.dispose();}}finally{pix.dispose();}}
   System.out.println("SMOKE_OK frames="+frames+" elapsed="+(System.nanoTime()-start)/1e9);Gdx.app.exit();
   new Thread(new Runnable(){@Override public void run(){try{Thread.sleep(500);}catch(InterruptedException ignored){}System.exit(0);}},"delver-smoke-exit").start();
  }
 }
 @Override public void pause(){if(mappedInput!=null)mappedInput.install();if(game!=null)game.pause();}
 @Override public void resume(){if(mappedInput!=null)mappedInput.install();if(game!=null)game.resume();}
 @Override public void dispose(){
  if(mappedInput!=null)mappedInput.close();
  if(game!=null){game.pause();game.dispose();}
  try{Class.forName("com.interrupt.dungeoneer.game.Options").getMethod("saveOptions").invoke(null);}
  catch(Exception e){throw new RuntimeException("Cannot save settings",e);}
 }
}
