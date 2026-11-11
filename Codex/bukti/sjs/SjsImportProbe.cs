// Runs only the statically reviewed local importer/crypto methods, never Main.
// All writes are redirected to a fresh temporary directory. No hooks or patches.
using System;
using System.IO;
using System.Data;
using System.Reflection;
using System.Security.Cryptography;
using System.Collections.Generic;
using System.Web.Script.Serialization;
public static class SjsImportProbe {
 static Module m;
 static object Call(int t,params object[] a){return m.ResolveMethod(t).Invoke(null,a);}
 static void Set(int t,object v){m.ResolveField(t).SetValue(null,v);}
 static object Get(int t){return m.ResolveField(t).GetValue(null);}
 static string Hash(string p){using(var s=File.OpenRead(p))using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
 public static int Main(string[] args){string target=Path.GetFullPath(args[0]);string sandbox=Path.Combine(Path.GetTempPath(),"codex-sjs-import",Guid.NewGuid().ToString("N"));Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
 AppDomain.CurrentDomain.AssemblyResolve+=(s,e)=>{string p=Path.Combine(target,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;};var r=new Dictionary<string,object>();r["sandbox"]=sandbox;r["scope"]="original local importer with supplied in-memory database id/time";
 try{string exe=Path.Combine(target,"JsSync.exe");m=Assembly.LoadFile(exe).ManifestModule;r["sha256"]=Hash(exe);r["mvid"]=m.ModuleVersionId.ToString();
 if((string)r["sha256"]!="6078efda305e292dabc2bd371c78f870fade17eff98f0c141e5aa565cb25c838")throw new Exception("Unexpected target build");
 Set(0x040003CA,sandbox);Call(0x06000EB2);Call(0x06000EB4);Call(0x06000EB3);
 if(args[1]=="token") {string plain="[123,100,12,3,7,9,500,600,20,30,-1,0,2,4,456]";var tuple=(Tuple<string,string>)Call(0x06000FFF,plain,17,90000);r["fixture_kind"]="synthetic statistics through original pure token encoder";r["token"]=tuple.Item1+tuple.Item2;r["plain"]=plain;r["decoded_original"]=Call(0x06000FFE,tuple.Item2,int.Parse(tuple.Item1)-17);}
 else {Set(0x040007D6,args[2]);Set(0x040007D7,DateTime.Parse("2026-11-11T12:00:00"));
 if(args.Length>4&&args[4]!="-"){Call(0x06000EBA,Path.GetFullPath(args[4]));r["previous_imported"]=true;}
 try{r["accepted"]=Call(0x06000EBA,Path.GetFullPath(args[3]));}catch(Exception e){while(e.InnerException!=null)e=e.InnerException;r["accepted"]=false;r["rejection"]=e.Message;}
 string cache=Path.Combine(sandbox,"license.enc");r["cache_exists"]=File.Exists(cache);if(File.Exists(cache)){r["cache_sha256"]=Hash(cache);DataTable t=(DataTable)Call(0x06000EB0);r["rows"]=t.Rows.Count;var row=new Dictionary<string,object>();if(t.Rows.Count>0)foreach(DataColumn c in t.Columns)row[c.ColumnName]=Convert.ToString(t.Rows[0][c]);r["fields"]=row;}
 r["temporary_files"]=Directory.GetFiles(sandbox).Length;}
 }catch(Exception e){while(e.InnerException!=null)e=e.InnerException;r["error"]=e.GetType().Name+": "+e.Message;}
 Console.WriteLine(new JavaScriptSerializer().Serialize(r));return r.ContainsKey("error")?1:0;}
}
