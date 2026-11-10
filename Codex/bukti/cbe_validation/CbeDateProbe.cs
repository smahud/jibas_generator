using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using System.Security.Cryptography;
public static class CbeDateProbe {
 public static int Main(string[] args) {
  try {
   string dir=@"C:\Program Files\YIM\JIBAS CBE Server 26.5";
   AppDomain.CurrentDomain.AssemblyResolve += delegate(object s, ResolveEventArgs e) {
    string p=Path.Combine(dir,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;
   };
   Assembly a=Assembly.LoadFile(Path.Combine(dir,"CbeServer.exe"));Module m=a.ManifestModule;
   string[] samples={"2026-11-10T12:00:00","2028-12-31T23:59:00","2029-01-01T23:59:00","2030-12-31T23:59:00","3000-01-01T00:00:00","4084-01-01T00:00:00","4085-01-01T00:00:00","9999-12-31T23:59:00"};
   var rows=new List<Dictionary<string,object>>();
   foreach(string stamp in samples) {
    DateTime d=DateTime.Parse(stamp,System.Globalization.CultureInfo.InvariantCulture);
    object value=m.ResolveMethod(0x06000E0A).Invoke(null,new object[]{d});
    rows.Add(new Dictionary<string,object>{{"stamp",stamp},{"original_minute",value}});
   }
   var result=new Dictionary<string,object>{{"method","0x06000E0A"},{"mvid",m.ModuleVersionId.ToString()},
    {"artifact_sha256",BitConverter.ToString(SHA256.Create().ComputeHash(File.ReadAllBytes(Path.Combine(dir,"CbeServer.exe")))).Replace("-","").ToLower()},
    {"samples",rows},{"scope","pure date method invocation only, no Main, database, network, or live writes"}};
   Console.WriteLine(new JavaScriptSerializer().Serialize(result));return 0;
  }catch(Exception e){while(e.InnerException!=null)e=e.InnerException;Console.Error.WriteLine(e);return 1;}
 }
}
