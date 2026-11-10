// Calls the original unmodified client UI importer in an isolated output directory.
// No hooks/patches, no database connection, no modifications to installed files.
// Identity is injected into runtime holder 0x0400051C as controlled replay.
// Usage: ClientImportVerify.exe <sandbox> <database-id> <lic> [renewal-lic ...]
using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
public static class ClientImportVerify {
 static Module m;
 static object Call(int t,params object[] a){return m.ResolveMethod(t).Invoke(null,a);}
 static object Get(int t){return m.ResolveField(t).GetValue(null);}
 static void Set(int t,object o){m.ResolveField(t).SetValue(null,o);}
 public static int Main(string[] args){
  string target=@"C:\YIM\JIBAS Generator\JIBAS Face & Fingerprint Client 16.10";
  string sandbox=Path.GetFullPath(args[0]); Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
  AppDomain.CurrentDomain.AssemblyResolve+=delegate(object s,ResolveEventArgs ev){string p=Path.Combine(target,new AssemblyName(ev.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;};
  m=Assembly.LoadFile(Path.Combine(target,"FaceFgrClient.exe")).ManifestModule;
  Call(0x060008B9);Set(0x04000369,sandbox);Call(0x06000AF2);Call(0x06000AF1);Set(0x0400051C,args[1]);
  var rows=new List<object>();
  for(int i=2;i<args.Length;i++){
   var r=new Dictionary<string,object>();r["input"]=Path.GetFullPath(args[i]);r["current_database_id"]=Get(0x0400051C);r["before_sequence"]=Get(0x040004D0);r["before_client_id"]=Get(0x040004C7);
   try{r["accepted"]=Call(0x06000AF9,Path.GetFullPath(args[i]));}catch(Exception e){while(e.InnerException!=null)e=e.InnerException;r["accepted"]=false;r["exception"]=e.GetType().FullName+": "+e.Message;}
   r["cache_exists"]=File.Exists(Path.Combine(sandbox,"licenseface.enc"));r["after_sequence"]=Get(0x040004D0);r["after_client_id"]=Get(0x040004C7);r["after_database_id"]=Get(0x040004C9);r["after_info1"]=Get(0x040004D1);
   try{r["cache_validator_returned"]=Call(0x06000AF7);}catch(Exception e){while(e.InnerException!=null)e=e.InnerException;r["cache_validator_exception"]=e.Message;}
   rows.Add(r);
  }
  var result=new Dictionary<string,object>();result["target_sha256"]=BitConverter.ToString(System.Security.Cryptography.SHA256.Create().ComputeHash(File.ReadAllBytes(Path.Combine(target,"FaceFgrClient.exe")))).Replace("-","").ToLowerInvariant();result["mvid"]=m.ModuleVersionId.ToString();result["authority"]="controlled-replay: runtime identity holder supplied; original importer and validator unmodified";result["sandbox"]=sandbox;result["attempts"]=rows;
  Console.WriteLine(new JavaScriptSerializer().Serialize(result));return 0;
 }
}
