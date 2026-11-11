// Runs only format/path/cache/import methods in a fresh temporary sandbox.
// Does not execute target Main, construct UI, or call database routines.
using System;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
using System.Data;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using System.Web.Script.Serialization;
public static class FingerProbe {
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
  MethodInfo hook=typeof(FingerProbe).GetMethod("EqualTrace",BindingFlags.Static|BindingFlags.NonPublic);
  RuntimeHelpers.PrepareMethod(original.MethodHandle);RuntimeHelpers.PrepareMethod(hook.MethodHandle);
  IntPtr p=original.MethodHandle.GetFunctionPointer(),h=hook.MethodHandle.GetFunctionPointer();
  byte* pcode=(byte*)p.ToPointer();if(pcode[0]==0xE9)p=new IntPtr(p.ToInt64()+5+*((int*)(pcode+1)));
  uint old;VirtualProtect(p,(UIntPtr)12,0x40,out old);byte* b=(byte*)p.ToPointer();
  b[0]=0x48;b[1]=0xB8;*((long*)(b+2))=h.ToInt64();b[10]=0xFF;b[11]=0xE0;
  uint ignored;VirtualProtect(p,(UIntPtr)12,old,out ignored);
  }
  MethodInfo indexOriginal=typeof(string).GetMethod("IndexOf",new Type[]{typeof(string)});
  MethodInfo indexHook=typeof(FingerProbe).GetMethod("IndexTrace",BindingFlags.Static|BindingFlags.NonPublic);
  RuntimeHelpers.PrepareMethod(indexOriginal.MethodHandle);RuntimeHelpers.PrepareMethod(indexHook.MethodHandle);
  IntPtr ip=indexOriginal.MethodHandle.GetFunctionPointer(),ih=indexHook.MethodHandle.GetFunctionPointer();byte* ic=(byte*)ip.ToPointer();if(ic[0]==0xE9)ip=new IntPtr(ip.ToInt64()+5+*((int*)(ic+1)));
  uint io;VirtualProtect(ip,(UIntPtr)12,0x40,out io);byte* ib=(byte*)ip.ToPointer();ib[0]=0x48;ib[1]=0xB8;*((long*)(ib+2))=ih.ToInt64();ib[10]=0xFF;ib[11]=0xE0;uint ii;VirtualProtect(ip,(UIntPtr)12,io,out ii);
 }
 static Module m; static object Call(int t,params object[] a){return m.ResolveMethod(t).Invoke(null,a);}
 static object Get(int t){return m.ResolveField(t).GetValue(null);}
 static void Set(int t,object a){m.ResolveField(t).SetValue(null,a);}
 static string Err(Exception e){while(e.InnerException!=null)e=e.InnerException;return e.ToString();}
 public static int Main(string[] args){
  bool manager=args[0]=="manager";
  string source=manager?@"C:\Program Files\YIM\JIBAS Face & Fingerprint Manager 16.5":@"C:\Program Files (x86)\YIM\JIBAS Fingerprint Client 14.0";
  string name=manager?"FaceFingerManager.exe":"Yim.Jibas.Sat.Fgr.Client.exe";
  string sandbox=Path.Combine(Path.GetTempPath(),"codex-fingerprint",Guid.NewGuid().ToString("N"));
  Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
  File.Copy(Path.Combine(source,name),Path.Combine(sandbox,name));
  AppDomain.CurrentDomain.AssemblyResolve+=delegate(object s,ResolveEventArgs e){string p=Path.Combine(source,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;};
  var r=new Dictionary<string,object>{{"target",name},{"sandbox",sandbox},{"scope","Original path/init/schema/import methods only. No Main, UI, database, or network methods invoked."}};
  try{
   m=Assembly.LoadFile(Path.Combine(sandbox,name)).ManifestModule;r["mvid"]=m.ModuleVersionId.ToString();
   int path=manager?0x06000B59:0x060006F8, init=manager?0x06000B5B:0x060006FA, schema=manager?0x06000B5A:0x060006F9;
   Set(manager?0x04000505:0x0400042E,sandbox);r["warm_path"]=Call(path);
   Set(manager?0x04000505:0x0400042E,sandbox);Call(init);Call(schema);
   r["password"]=Get(manager?0x040004DE:0x04000424);r["iv"]=Get(manager?0x040004DF:0x04000425);
   DataTable table=(DataTable)Get(manager?0x04000A56:0x040003AA);
   using(var w=new StringWriter()){table.WriteXml(w,XmlWriteMode.WriteSchema);r["schema_xml"]=w.ToString();}
   if(args[1]=="strings"){
    int decoder=manager?0x06000033:0x060000E7;
    var vals=new Dictionary<int,string>();
    var ops=new Dictionary<ushort,OpCode>();foreach(var f in typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static)){OpCode o=(OpCode)f.GetValue(null);ops[unchecked((ushort)o.Value)]=o;}
    foreach(var type in m.Assembly.GetTypes())foreach(var method in type.GetMethods(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static|BindingFlags.Instance|BindingFlags.DeclaredOnly)){
     MethodBody body;try{body=method.GetMethodBody();}catch{continue;}if(body==null)continue;
     byte[] il=body.GetILAsByteArray();int p=0,last=0;bool prev=false;
     while(p<il.Length){ushort v=il[p++];if(v==254)v=(ushort)(65024+il[p++]);OpCode op=ops[v];int skip=0,value=0;
      switch(op.OperandType){case OperandType.InlineNone:break;case OperandType.ShortInlineI:case OperandType.ShortInlineVar:case OperandType.ShortInlineBrTarget:skip=1;value=(sbyte)il[p];break;case OperandType.InlineVar:skip=2;break;case OperandType.InlineI8:case OperandType.InlineR:skip=8;break;case OperandType.InlineSwitch:skip=4+4*BitConverter.ToInt32(il,p);break;default:skip=4;value=BitConverter.ToInt32(il,p);break;}
      if((op==OpCodes.Call||op==OpCodes.Callvirt)&&value==decoder&&prev&&!vals.ContainsKey(last))try{vals[last]=(string)Call(decoder,last);}catch(Exception ex){vals[last]="ERROR "+Err(ex);}
      prev=op==OpCodes.Ldc_I4||op==OpCodes.Ldc_I4_S;last=value;p+=skip;
     }
    }
    using(var w=new StreamWriter(args[2]))foreach(var kv in vals)w.WriteLine(kv.Key+"\t"+kv.Value.Replace("\r","\\r").Replace("\n","\\n"));r["decoded_strings"]=vals.Count;
   } else if(args[1]=="import"){
    TraceEquality();
    int importer=manager?0x06000B60:0x060006FF;
    var attempts=new List<Dictionary<string,object>>();
    for(int i=2;i<args.Length;i++){
     var q=new Dictionary<string,object>{{"input",Path.GetFullPath(args[i])}};
     try{tracing=true;q["result"]=Call(importer,Path.GetFullPath(args[i]));}catch(Exception e){q["exception"]=Err(e);}
     tracing=false;q["comparisons"]=comparisons.ToArray();q["indexes"]=indexes.ToArray();comparisons.Clear();indexes.Clear();q["rows"]=table.Rows.Count;using(var w=new StringWriter()){table.WriteXml(w,XmlWriteMode.WriteSchema);q["xml"]=w.ToString();}
     q["cache_exists"]=File.Exists(Path.Combine(sandbox,"license.enc"));attempts.Add(q);
    }r["attempts"]=attempts;
   } else if(args[1]=="validate"){
    if(args.Length>2){File.Copy(args[2],Path.Combine(sandbox,"license.enc"));r["loaded"]=Call(manager?0x06000B5F:0x060006FE);}
    var checks=new List<Dictionary<string,object>>();for(int i=3;i<args.Length;i++){
     var q=new Dictionary<string,object>{{"serial",args[i]}};try{q["result"]=Call(manager?0x06000B61:0x06000700,args[i]);}catch(Exception e){q["exception"]=Err(e);}checks.Add(q);
    }r["checks"]=checks;
   }
  }catch(Exception e){r["error"]=Err(e);}Console.WriteLine(new JavaScriptSerializer{MaxJsonLength=16777216}.Serialize(r));return r.ContainsKey("error")?1:0;
 }
}

