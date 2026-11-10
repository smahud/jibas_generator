using System;
using System.IO;
using System.Data;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
public static class SchoolPayFormatProbe {
 static Module m;
 static object Call(int t,params object[] a){return m.ResolveMethod(t).Invoke(null,a);}
 static object Get(int t){return m.ResolveField(t).GetValue(null);}
 static string Shown(Exception e){while(e.InnerException!=null)e=e.InnerException;return e.GetType().Name+": "+e.Message;}
 public static int Main(string[] args){
  string target=@"C:\Program Files (x86)\YIM\JIBAS SchoolPay Secure Server 10.5";
  string sandbox=Path.Combine(Path.GetTempPath(),"codex-schoolpay",Guid.NewGuid().ToString("N"));
  Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
  AppDomain.CurrentDomain.AssemblyResolve+=delegate(object s,ResolveEventArgs e){string p=Path.Combine(target,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;};
  var result=new Dictionary<string,object>();
  try {
   m=Assembly.LoadFile(Path.Combine(target,"SPayServer.exe")).ManifestModule;
   m.ResolveField(0x0400036F).SetValue(null,sandbox);
   result["warm_path"]=Call(0x0600074F);
   Call(0x06000751);Call(0x06000750);
   result["password"]=Get(0x04000359);result["iv"]=Get(0x0400035A);
   var table=(DataTable)Get(0x04000381);
   var columns=new List<Dictionary<string,object>>();
   foreach(DataColumn c in table.Columns)columns.Add(new Dictionary<string,object>{{"name",c.ColumnName},{"type",c.DataType.FullName}});
   result["table"]=table.TableName;result["columns"]=columns;
   using(var writer=new StringWriter()){table.WriteXml(writer,XmlWriteMode.WriteSchema);result["schema_xml"]=writer.ToString();}
   if(args.Length>0){
    string raw=File.ReadAllLines(args[0])[0];
    result["installed_xml"] = Call(0x0600066E,raw,Get(0x04000359),Get(0x0400035A));
   }
  }catch(Exception e){result["error"]=Shown(e);}
  result["sandbox"]=sandbox;Console.WriteLine(new JavaScriptSerializer().Serialize(result));return result.ContainsKey("error")?1:0;
 }
}
