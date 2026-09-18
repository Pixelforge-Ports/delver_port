package org.portmaster.delver;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.InputAdapter;
import com.badlogic.gdx.InputProcessor;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.math.Matrix4;
import java.io.*;
import java.lang.reflect.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.ArrayBlockingQueue;

/** Receives only gptokeyb2's mapped events, independently of desktop window focus. */
public final class MappedInput implements AutoCloseable {
 private final Input desktop;
 private final InputAdapter sink=new InputAdapter();
 private final Input proxy;
 private InputProcessor target;
 private final DataInputStream stream;
 private final ArrayBlockingQueue<int[]> events=new ArrayBlockingQueue<>(4096);
 private final Set<Integer> held=new HashSet<>(),justKeys=new HashSet<>();
 private final boolean[] buttons=new boolean[3];
 private volatile boolean closed;
 private volatile IOException failure;
 private boolean caught,touched;
 private int x,y,dx,dy,pendingX,pendingY;
 private ShapeRenderer cursor;
 private final IntBuffer savedViewport=com.badlogic.gdx.utils.BufferUtils.newIntBuffer(4);

 public MappedInput(Input desktop) throws IOException {
  this.desktop=desktop;
  target=desktop.getInputProcessor();
  Path device=findDevice();
  stream=new DataInputStream(new FileInputStream(device.toFile()));
  x=Gdx.graphics.getWidth()/2;y=Gdx.graphics.getHeight()/2;
  proxy=(Input)Proxy.newProxyInstance(Input.class.getClassLoader(),new Class<?>[]{Input.class},(self,method,args)->{
   String name=method.getName();
   if(name.equals("setInputProcessor")){target=(InputProcessor)args[0];return null;}
   if(name.equals("getInputProcessor"))return target;
   if(name.equals("getX"))return x;
   if(name.equals("getY"))return y;
   if(name.equals("getDeltaX"))return dx;
   if(name.equals("getDeltaY"))return dy;
   if(name.equals("isKeyPressed")){int key=(Integer)args[0];return key==Input.Keys.ANY_KEY?!held.isEmpty():held.contains(key);}
   if(name.equals("isKeyJustPressed")){int key=(Integer)args[0];return key==Input.Keys.ANY_KEY?!justKeys.isEmpty():justKeys.contains(key);}
   if(name.equals("isButtonPressed")){int b=(Integer)args[0];return b>=0&&b<buttons.length&&buttons[b];}
   if(name.equals("isTouched"))return buttons[0]||buttons[1]||buttons[2];
   if(name.equals("justTouched"))return touched;
   if(name.equals("getPressure"))return buttons[0]?1f:0f;
   if(name.equals("isCursorCatched"))return caught;
   if(name.equals("setCursorCatched")){caught=(Boolean)args[0];if(!caught)clampPointer();return null;}
   if(name.equals("setCursorPosition")){x=(Integer)args[0];y=(Integer)args[1];if(!caught)clampPointer();return null;}
   if(name.equals("getCurrentEventTime"))return System.nanoTime();
   try{return method.invoke(desktop,args);}catch(InvocationTargetException e){throw e.getCause();}
  });
  install();
  Thread reader=new Thread(this::readEvents,"delver-mapped-input");
  reader.setDaemon(true);reader.start();
 }

 private static Path findDevice() throws IOException {
  List<Path> matches=new ArrayList<>();
  try(DirectoryStream<Path> entries=Files.newDirectoryStream(Paths.get("/sys/class/input"),"event*")){
   for(Path entry:entries){
    Path name=entry.resolve("device/name");
    if(Files.isReadable(name)&&new String(Files.readAllBytes(name),StandardCharsets.UTF_8).trim().equals("Fake Keyboard Mouse"))
     matches.add(Paths.get("/dev/input",entry.getFileName().toString()));
   }
  }
  if(matches.size()!=1)throw new IOException("Expected one gptokeyb2 Fake Keyboard Mouse, found "+matches.size()+". Close other ports and restart Delver.");
  return matches.get(0);
 }

 private void readEvents(){
  // The shipping runtime is 64-bit ARM: timeval occupies 16 bytes.
  byte[] record=new byte[24];
  ByteBuffer fields=ByteBuffer.wrap(record).order(ByteOrder.LITTLE_ENDIAN);
  try{
   while(!closed){
    stream.readFully(record);
    int type=fields.getShort(16)&0xffff,code=fields.getShort(18)&0xffff,value=fields.getInt(20);
    if(type==0&&code==3)throw new IOException("Mapped input overflow (SYN_DROPPED); restart the port");
    if(type<=2&&!events.offer(new int[]{type,code,value}))throw new IOException("Mapped input queue overflow; restart the port");
   }
  }catch(IOException e){if(!closed)failure=e;}
 }

 public void install(){
  // LWJGL restores Gdx.input around its window callbacks.
  InputProcessor current=desktop.getInputProcessor();
  if(current!=sink){target=current;desktop.setInputProcessor(sink);}
  Gdx.input=proxy;
 }

 public void beginFrame(){
  install();dx=0;dy=0;touched=false;justKeys.clear();
  if(failure!=null){releaseAll();throw new IllegalStateException("MAPPED_INPUT_FAILED: "+failure.getMessage(),failure);}
  int[] event;
  for(int count=0;count<4096&&(event=events.poll())!=null;count++){
   int type=event[0],code=event[1],value=event[2];
   if(type==2){
    if(code==0)pendingX+=value;
    else if(code==1)pendingY+=value;
    else if(code==8&&target!=null)target.scrolled(-value);
   }else if(type==0&&code==0)movePointer();
   else if(type==1){movePointer();key(code,value);}
  }
 }

 private void clampPointer(){
  x=Math.max(0,Math.min(Gdx.graphics.getWidth()-1,x));
  y=Math.max(0,Math.min(Gdx.graphics.getHeight()-1,y));
 }

 private void movePointer(){
  if(pendingX==0&&pendingY==0)return;
  dx+=pendingX;dy+=pendingY;x+=pendingX;y+=pendingY;pendingX=0;pendingY=0;
  // Captured coordinates must keep moving past screen edges for continuous turning.
  if(!caught)clampPointer();
  if(target!=null){
   if(buttons[0]||buttons[1]||buttons[2])target.touchDragged(x,y,0);
   else target.mouseMoved(x,y);
  }
 }

 private void key(int code,int value){
  if(code>=272&&code<=274){
   int button=code-272;boolean down=value!=0;
   if(buttons[button]==down)return;
   buttons[button]=down;touched|=down;
   if(target!=null){if(down)target.touchDown(x,y,0,button);else target.touchUp(x,y,0,button);}
   return;
  }
  int key=keyCode(code);if(key<0)return;
  if(value==0){if(held.remove(key)&&target!=null)target.keyUp(key);}
  else{
   if(held.add(key)){justKeys.add(key);if(target!=null)target.keyDown(key);}
   char c=character(key);if(c!=0&&target!=null)target.keyTyped(c);
  }
 }

 static int keyCode(int code){
  if(code>=2&&code<=10)return Input.Keys.NUM_1+code-2;
  if(code==11)return Input.Keys.NUM_0;
  int[] linux={16,17,18,19,20,21,22,23,24,25,30,31,32,33,34,35,36,37,38,44,45,46,47,48,49,50};
  String letters="qwertyuiopasdfghjklzxcvbnm";
  for(int i=0;i<linux.length;i++)if(code==linux[i])return Input.Keys.A+letters.charAt(i)-'a';
  switch(code){
   case 1:return Input.Keys.ESCAPE;case 14:return Input.Keys.BACKSPACE;
   case 15:return Input.Keys.TAB;case 26:return Input.Keys.LEFT_BRACKET;
   case 27:return Input.Keys.RIGHT_BRACKET;case 28:return Input.Keys.ENTER;
   case 29:return Input.Keys.CONTROL_LEFT;case 42:return Input.Keys.SHIFT_LEFT;
   case 54:return Input.Keys.SHIFT_RIGHT;case 57:return Input.Keys.SPACE;
   case 103:return Input.Keys.UP;case 105:return Input.Keys.LEFT;
   case 106:return Input.Keys.RIGHT;case 108:return Input.Keys.DOWN;
   default:return -1;
  }
 }

 private char character(int key){
  if(key>=Input.Keys.A&&key<=Input.Keys.Z){char c=(char)('a'+key-Input.Keys.A);return held.contains(Input.Keys.SHIFT_LEFT)||held.contains(Input.Keys.SHIFT_RIGHT)?Character.toUpperCase(c):c;}
  if(key>=Input.Keys.NUM_0&&key<=Input.Keys.NUM_9)return (char)('0'+key-Input.Keys.NUM_0);
  if(key==Input.Keys.SPACE)return ' ';if(key==Input.Keys.ENTER)return '\r';
  if(key==Input.Keys.BACKSPACE)return '\b';return 0;
 }

 public void drawCursor(){
  if(caught)return;
  if(cursor==null)cursor=new ShapeRenderer();
  clampPointer();
  savedViewport.clear();Gdx.gl.glGetIntegerv(GL20.GL_VIEWPORT,savedViewport);
  Gdx.gl.glViewport(0,0,Gdx.graphics.getBackBufferWidth(),Gdx.graphics.getBackBufferHeight());
  boolean depth=Gdx.gl.glIsEnabled(GL20.GL_DEPTH_TEST),scissor=Gdx.gl.glIsEnabled(GL20.GL_SCISSOR_TEST);
  Gdx.gl.glDisable(GL20.GL_DEPTH_TEST);Gdx.gl.glDisable(GL20.GL_SCISSOR_TEST);
  cursor.setProjectionMatrix(new Matrix4().setToOrtho2D(0,0,Gdx.graphics.getWidth(),Gdx.graphics.getHeight()));
  float cy=Gdx.graphics.getHeight()-y;
  cursor.begin(ShapeRenderer.ShapeType.Filled);
  cursor.setColor(Color.BLACK);cursor.rect(x-7,cy-2,15,5);cursor.rect(x-2,cy-7,5,15);
  cursor.setColor(Color.WHITE);cursor.rect(x-6,cy-1,13,3);cursor.rect(x-1,cy-6,3,13);
  cursor.end();
  if(depth)Gdx.gl.glEnable(GL20.GL_DEPTH_TEST);if(scissor)Gdx.gl.glEnable(GL20.GL_SCISSOR_TEST);
  Gdx.gl.glViewport(savedViewport.get(0),savedViewport.get(1),savedViewport.get(2),savedViewport.get(3));
 }

 private void releaseAll(){
  if(target!=null){
   for(int key:held)target.keyUp(key);
   for(int b=0;b<buttons.length;b++)if(buttons[b])target.touchUp(x,y,0,b);
  }
  held.clear();Arrays.fill(buttons,false);
 }

 @Override public void close(){
  closed=true;
  try{stream.close();}catch(IOException ignored){}
  releaseAll();desktop.setInputProcessor(target);Gdx.input=desktop;
  if(cursor!=null)cursor.dispose();
 }
}
