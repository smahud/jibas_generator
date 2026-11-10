using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using System.Security.Cryptography;
using System.Data;
public static class CbeImportProbe {
 static Module m;
 static string targetDir=@"C:\Program Files\YIM\JIBAS CBE Server 26.5";
 static void Set(int token,object value){m.ResolveField(token).SetValue(null,value);}
 static object Get(int token){return m.ResolveField(token).GetValue(null);}
 static object Call(int token,params object[] args){return m.ResolveMethod(token).Invoke(null,args);}
 public static int Main(string[] args) {
  try {
   string sandbox=Path.GetFullPath(args[0]);
   if(sandbox.StartsWith(targetDir,StringComparison.OrdinalIgnoreCase))throw new Exception("Sandbox must not be inside live installation");
   Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
   AppDomain.CurrentDomain.AssemblyResolve += delegate(object s,ResolveEventArgs e){string p=Path.Combine(targetDir,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;};
   Assembly a=Assembly.LoadFile(Path.Combine(targetDir,"CbeServer.exe"));m=a.ManifestModule;
   Set(0x040005D2,sandbox);Call(0x060005B7);Call(0x060005B9);Call(0x060005B8);
   Set(0x040003F3,args[1]);
   int importer=Convert.ToInt32(args[2],16);
   var attempts=new List<Dictionary<string,object>>();
   for(int i=3;i<args.Length;i++){
    var r=new Dictionary<string,object>{{"input",Path.GetFullPath(args[i])},{"before_client",Get(0x040003F6)},{"before_sequence",Get(0x040003FF)}};
    try{r["accepted"]=Call(importer,Path.GetFullPath(args[i]));}catch(Exception e){while(e.InnerException!=null)e=e.InnerException;r["accepted"]=false;r["exception"]=e.GetType().FullName+": "+e.Message;}
    r["after_client"]=Get(0x040003F6);r["after_sequence"]=Get(0x040003FF);r["after_database_id"]=Get(0x040003F8);r["after_seri"]=Get(0x040003F9);r["after_info1"]=Get(0x04000400);r["capacity"]=Get(0x040003FD);r["transformed_capacity"]=Get(0x040003FE);
    string cache=Path.Combine(sandbox,"license.enc");r["cache_exists"]=File.Exists(cache);
    if(File.Exists(cache)){
     r["cache_sha256"]=BitConverter.ToString(SHA256.Create().ComputeHash(File.ReadAllBytes(cache))).Replace("-","").ToLower();
     Call(0x060005B8);r["cache_loader_returned"]=Call(0x060005BE);
     DataTable table=(DataTable)Get(0x040002DE);var names=new List<string>();foreach(DataColumn col in table.Columns)names.Add(col.ColumnName);r["cache_columns"]=names;
     r["reloaded_client"]=Get(0x040003F6);r["reloaded_sequence"]=Get(0x040003FF);r["reloaded_capacity"]=Get(0x040003FD);r["reloaded_transformed_capacity"]=Get(0x040003FE);
    }
    attempts.Add(r);
   }
   var all=new Dictionary<string,object>{{"artifact_sha256",BitConverter.ToString(SHA256.Create().ComputeHash(File.ReadAllBytes(Path.Combine(targetDir,"CbeServer.exe")))).Replace("-","").ToLower()},
    {"mvid",m.ModuleVersionId.ToString()},{"current_database_id",args[1]},{"importer_token",args[2]},
    {"authority","controlled replay: current database-ID holder supplied; unmodified target importer and cache-loader methods"},
    {"scope","Target Main/UI/full runtime not executed; cache files written only under caller-provided sandbox"},{"attempts",attempts}};
   Console.WriteLine(new JavaScriptSerializer().Serialize(all));return 0;
  }catch(Exception e){while(e.InnerException!=null)e=e.InnerException;Console.Error.WriteLine(e);return 1;}
 }
}
