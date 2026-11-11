using System;
using System.IO;
using System.Data;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
public static class SjsFormatProbe {
 static Module m;
 static object Call(int t,params object[] a){return m.ResolveMethod(t).Invoke(null,a);}
 public static int Main(string[] args){string target=args[0];string sandbox=Path.Combine(Path.GetTempPath(),"codex-sjs",Guid.NewGuid().ToString("N"));Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
 AppDomain.CurrentDomain.AssemblyResolve+=(s,e)=>{string p=Path.Combine(target,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;};var r=new Dictionary<string,object>();
 try{m=Assembly.LoadFile(Path.Combine(target,"JsSync.exe")).ManifestModule;m.ResolveField(0x040003CA).SetValue(null,sandbox);r["warm_path"]=Call(0x06000EB2);Call(0x06000EB4);Call(0x06000EB3);
 r["password_b64"]=Convert.ToBase64String(System.Text.Encoding.ASCII.GetBytes((string)m.ResolveField(0x040003C8).GetValue(null)));r["iv_b64"]=Convert.ToBase64String(System.Text.Encoding.ASCII.GetBytes((string)m.ResolveField(0x040003C9).GetValue(null)));
 DataTable t=(DataTable)Call(0x06000EB0);r["table"]=t.TableName;var cols=new List<object>();foreach(DataColumn c in t.Columns)cols.Add(new {name=c.ColumnName,type=c.DataType.FullName});r["columns"]=cols;using(var sw=new StringWriter()){t.WriteXml(sw,XmlWriteMode.WriteSchema);r["schema_xml"]=sw.ToString();}
 r["temporary_file_count"]=Directory.GetFiles(sandbox).Length;
 }catch(Exception e){while(e.InnerException!=null)e=e.InnerException;r["error"]=e.GetType().Name+": "+e.Message;}
 Console.WriteLine(new JavaScriptSerializer().Serialize(r));return r.ContainsKey("error")?1:0;}
}
