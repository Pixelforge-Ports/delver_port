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
 private int frames;
 private long start, lastFrame;
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
  try{game=(ApplicationListener)Class.forName("com.interrupt.dungeoneer.GameApplication").getDeclaredConstructor().newInstance();game.create();start=System.nanoTime();System.out.println("GAME_CREATE_OK Delver v1.08; offline; keyboard/mouse");}
  catch(Exception e){throw new RuntimeException(e);}
 }
 @Override public void resize(int w,int h){if(game!=null)game.resize(w,h);}
 @Override public void render(){
  long now=System.nanoTime();
  while(lastFrame!=0 && now-lastFrame<16666667L){java.util.concurrent.locks.LockSupport.parkNanos(16666667L-(now-lastFrame));now=System.nanoTime();}
  lastFrame=now;
  game.render();frames++;
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
 @Override public void pause(){if(game!=null)game.pause();}
 @Override public void resume(){if(game!=null)game.resume();}
 @Override public void dispose(){
  if(game!=null){game.pause();game.dispose();}
  try{Class.forName("com.interrupt.dungeoneer.game.Options").getMethod("saveOptions").invoke(null);}
  catch(Exception e){throw new RuntimeException("Cannot save settings",e);}
 }
}
