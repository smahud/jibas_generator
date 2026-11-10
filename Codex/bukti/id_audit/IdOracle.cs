using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Data.Common;
using System.Web.Script.Serialization;

// Read-only original-method oracle. DB writes, if any, come from AC3's own
// bootstrap branch and are used ONLY on the isolated localhost:3435 instance.
public static class IdOracle {
  static Module mod;
  static object Call(int token, params object[] values) {
    return mod.ResolveMethod(token).Invoke(null, values);
  }
  public static int Main(string[] args) {
    string dir = @"C:\Program Files\YIM\JIBAS Face Server 16.5";
    string sandbox = Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"sandbox");
    Directory.CreateDirectory(sandbox); Environment.CurrentDirectory=sandbox;
    AppDomain.CurrentDomain.AssemblyResolve += delegate(object s, ResolveEventArgs ev) {
      string p=Path.Combine(dir,new AssemblyName(ev.Name).Name+".dll");
      return File.Exists(p) ? Assembly.LoadFrom(p) : null;
    };
    try {
      mod=Assembly.LoadFile(Path.Combine(dir,"FaceServer.exe")).ManifestModule;
      var result=new Dictionary<string,object>();
      result["mvid"]=mod.ModuleVersionId.ToString();
      if(args.Length>0 && args[0]=="db") {
        int port=args.Length>1 ? Int32.Parse(args[1]) : 3434;
        string pass=Environment.GetEnvironmentVariable("ID_AUDIT_MYSQL_PASSWORD");
        if(pass==null) throw new InvalidOperationException("ID_AUDIT_MYSQL_PASSWORD belum tersedia.");
        var mysql=Assembly.LoadFrom(Path.Combine(dir,"MySql.Data.dll"));
        var ct=mysql.GetType("MySql.Data.MySqlClient.MySqlConnection");
        var builder=new DbConnectionStringBuilder();
        builder.ConnectionString="server=127.0.0.1;port="+port+";user id=root;persistsecurityinfo=false;charset=utf8mb4";
        builder["password"]=pass;
        object conn=Activator.CreateInstance(ct,builder.ConnectionString);
        ct.GetMethod("Open").Invoke(conn,null);
        result["port"]=port;
        result["original_AC3"]=Call(0x06000AC3,conn);
        ct.GetMethod("Close").Invoke(conn,null);
      } else {
        string disk=(string)Call(0x06000599), uuid=(string)Call(0x0600059A);
        result["disk_raw"]=disk; result["disk_raw_length"]=disk.Length;
        result["uuid"]=uuid; result["original_59B"]=Call(0x0600059B);
        result["raw_digest_849"]=Call(0x06000849,disk+uuid);
        result["trimmed_digest_849"]=Call(0x06000849,disk.TrimEnd()+uuid);
        var vectors=new List<object>();
        foreach(string str in new string[]{"", "A", "A ", " ABC ", "A\u00e9\U0001f600B", disk+uuid}) {
          string digest=(string)Call(0x06000849,str);
          string id="";foreach(int i in new int[]{5,17,30,24,3}) id+=digest.Substring(i,1);
          vectors.Add(new {input=str,digest=digest,system_id=id.ToUpper()});
        }
        result["vectors"]=vectors;
        var decoder=(Func<int,string>)Delegate.CreateDelegate(typeof(Func<int,string>),(MethodInfo)mod.ResolveMethod(0x060004B5));
        var strings=new Dictionary<string,string>();
        foreach(int n in new int[]{-1509740398,-1509739175,-1509739774,-1509750397,-1509749895,-1509750011,-1509739459}) strings[n.ToString()]=decoder(n);
        result["decoded_strings"]=strings;
      }
      Console.WriteLine(new JavaScriptSerializer().Serialize(result));
      return 0;
    } catch(Exception ex) {
      while(ex.InnerException!=null) ex=ex.InnerException;
      Console.Error.WriteLine(ex);return 1;
    }
  }
}
