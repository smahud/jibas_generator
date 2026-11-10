using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using System.Data;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

public static class ClientImportProbe {
 static bool tracing;
 static List<string[]> comparisons=new List<string[]>();
 static List<string[]> indexes=new List<string[]>();
 [DllImport("kernel32.dll")] static extern bool VirtualProtect(IntPtr p,UIntPtr n,uint protect,out uint old);
 [MethodImpl(MethodImplOptions.NoInlining|MethodImplOptions.NoOptimization)]
 static bool EqualTrace(string a,string b) { if(tracing) comparisons.Add(new string[]{a,b}); return string.Equals(a,b,StringComparison.Ordinal); }
 [MethodImpl(MethodImplOptions.NoInlining|MethodImplOptions.NoOptimization)]
 static int IndexTrace(string a,string b) {if(tracing)indexes.Add(new string[]{a,b});return a.IndexOf(b,StringComparison.CurrentCulture);}
 static unsafe void TraceEquality() {
  foreach(MethodInfo original in new MethodInfo[]{typeof(string).GetMethod("op_Equality",BindingFlags.Static|BindingFlags.Public),typeof(string).GetMethod("Equals",new Type[]{typeof(string)}),typeof(string).GetMethod("Equals",new Type[]{typeof(string),typeof(string)})}) {
  MethodInfo hook=typeof(ClientImportProbe).GetMethod("EqualTrace",BindingFlags.Static|BindingFlags.NonPublic);
  RuntimeHelpers.PrepareMethod(original.MethodHandle);RuntimeHelpers.PrepareMethod(hook.MethodHandle);
  IntPtr p=original.MethodHandle.GetFunctionPointer(),h=hook.MethodHandle.GetFunctionPointer();
  byte* pcode=(byte*)p.ToPointer();if(pcode[0]==0xE9)p=new IntPtr(p.ToInt64()+5+*((int*)(pcode+1)));
  uint old;VirtualProtect(p,(UIntPtr)12,0x40,out old);byte* b=(byte*)p.ToPointer();
  b[0]=0x48;b[1]=0xB8;*((long*)(b+2))=h.ToInt64();b[10]=0xFF;b[11]=0xE0;
  uint ignored;VirtualProtect(p,(UIntPtr)12,old,out ignored);
  }
  MethodInfo indexOriginal=typeof(string).GetMethod("IndexOf",new Type[]{typeof(string)});
  MethodInfo indexHook=typeof(ClientImportProbe).GetMethod("IndexTrace",BindingFlags.Static|BindingFlags.NonPublic);
  RuntimeHelpers.PrepareMethod(indexOriginal.MethodHandle);RuntimeHelpers.PrepareMethod(indexHook.MethodHandle);
  IntPtr ip=indexOriginal.MethodHandle.GetFunctionPointer(),ih=indexHook.MethodHandle.GetFunctionPointer();byte* ic=(byte*)ip.ToPointer();if(ic[0]==0xE9)ip=new IntPtr(ip.ToInt64()+5+*((int*)(ic+1)));
  uint io;VirtualProtect(ip,(UIntPtr)12,0x40,out io);byte* ib=(byte*)ip.ToPointer();ib[0]=0x48;ib[1]=0xB8;*((long*)(ib+2))=ih.ToInt64();ib[10]=0xFF;ib[11]=0xE0;uint ii;VirtualProtect(ip,(UIntPtr)12,io,out ii);
 }
 static Module m;
 static object Call(int t, params object[] a) {return m.ResolveMethod(t).Invoke(null,a);}
 static void Set(int t,object v){m.ResolveField(t).SetValue(null,v);}
 static object Get(int t){return m.ResolveField(t).GetValue(null);}
 public static int Main(string[] args) {
  string target=@"C:\YIM\JIBAS Generator\JIBAS Face & Fingerprint Client 16.10";
  string sandbox=Path.GetFullPath(args[0]);Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
  var result=new Dictionary<string,object>();
  AppDomain.CurrentDomain.AssemblyResolve+=delegate(object s,ResolveEventArgs ev){string p=Path.Combine(target,new AssemblyName(ev.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;};
  m=Assembly.LoadFile(Path.Combine(target,"FaceFgrClient.exe")).ManifestModule;
  Call(0x060008B9);Set(0x04000369,sandbox);Call(0x06000AF2);Call(0x06000AF1);
  Set(0x0400051C,args.Length>3?args[3]:"V4YNE");
  result["password"]=Get(0x04000375);result["iv"]=Get(0x04000376);
  result["input"]=Path.GetFullPath(args[1]);result["sandbox"]=sandbox;
  if(args.Length>2 && args[2]=="trace") {TraceEquality();tracing=true;}
  try { result["accepted"]=Call(0x06000AF9,Path.GetFullPath(args[1])); }
  catch(Exception ex){while(ex.InnerException!=null) ex=ex.InnerException; result["exception"]=ex.ToString();result["accepted"]=false;}
  tracing=false; result["string_equality"]=comparisons;result["string_indexof"]=indexes;
  result["cache_exists"]=File.Exists(Path.Combine(sandbox,"licenseface.enc"));
  result["mode"]=Get(0x040004C7);result["dbid"]=Get(0x040004C9);result["info1"]=Get(0x040004D1);
  Console.WriteLine(new JavaScriptSerializer().Serialize(result)); return 0;
 }
}
