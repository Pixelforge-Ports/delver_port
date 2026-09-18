package org.portmaster.delver;
import java.nio.file.*;
import java.security.MessageDigest;
import java.io.*;
public final class VerifyGame {
 public static final String SHA256="a2d58e87b09f588ff8389508e43accf7d3c6ce949b5aa4d31d6380574ec095ae";
 public static void check(Path file) throws Exception {
  if(!Files.isRegularFile(file)) throw new IOException("Copy Steam Delver v1.08 delver.jar into the delver folder.");
  MessageDigest digest=MessageDigest.getInstance("SHA-256");
  try(InputStream in=Files.newInputStream(file)){byte[] buf=new byte[65536];int n;while((n=in.read(buf))!=-1)digest.update(buf,0,n);}
  StringBuilder sum=new StringBuilder();for(byte b:digest.digest())sum.append(String.format("%02x",b&255));
  if(!SHA256.equals(sum.toString()))throw new IOException("Unsupported delver.jar. Required Steam depot 249631 manifest 6680730644186394716; see delver.md.");
 }
 public static void main(String[] args) throws Exception {check(Paths.get(args[0]));System.out.println("GAME_DATA_OK Delver v1.08");}
}
