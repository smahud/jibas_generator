using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using System.Security.Cryptography;
public static class SchoolPayImportProbe {
  static Module m;
  static string dir = @"C:\Program Files (x86)\YIM\JIBAS SchoolPay Secure Server 10.5";
  static void Set(int token,object value){m.ResolveField(token).SetValue(null,value);}
  static object Get(int token){return m.ResolveField(token).GetValue(null);}
  static object Call(int token,params object[] args){return m.ResolveMethod(token).Invoke(null,args);}
  public static int Main(string[] args) {
    try {
      string sandbox=Path.GetFullPath(args[0]); Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
      AppDomain.CurrentDomain.AssemblyResolve += delegate(object s, ResolveEventArgs e) { string p=Path.Combine(dir,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null; };
      Assembly a=Assembly.LoadFile(Path.Combine(dir,"SPayServer.exe"));m=a.ManifestModule;
      Set(0x0400036F,sandbox);Call(0x0600074F);Call(0x06000751);Call(0x06000750);
      Set(0x0400052D,args[1]);Set(0x04000524,args[2]);
      var attempts=new List<Dictionary<string,object>>();
      int importer=Convert.ToInt32(args[3],16);
      for(int i=4;i<args.Length;i++) {
        var r=new Dictionary<string,object>();r["input"]=args[i];r["before_client"]=Get(0x04000519);r["before_sequence"]=Get(0x04000521);
        try {r["accepted"]=Call(importer,Path.GetFullPath(args[i]));}catch(Exception ex){while(ex.InnerException!=null)ex=ex.InnerException;r["accepted"]=false;r["exception"]=ex.GetType().FullName+": "+ex.Message;}
        r["after_client"]=Get(0x04000519);r["after_sequence"]=Get(0x04000521);r["after_dbid"]=Get(0x0400051B);r["after_systemid"]=Get(0x0400051C);r["max_vendor"]=Get(0x04000520);
        r["cache_exists"]=File.Exists(Path.Combine(sandbox,"license.enc"));
        if((bool)r["cache_exists"])r["cache_loader_returned"]=Call(0x06000756);
        attempts.Add(r);
      }
      var all=new Dictionary<string,object>();all["artifact_sha256"]=BitConverter.ToString(SHA256.Create().ComputeHash(File.ReadAllBytes(Path.Combine(dir,"SPayServer.exe")))).Replace("-","").ToLower();all["mvid"]=m.ModuleVersionId.ToString();all["authority"]="controlled replay: current ID holders supplied; original methods unmodified, no Main/UI/network";all["importer_token"]=args[3];all["current_database_id"]=args[1];all["current_system_id"]=args[2];all["attempts"]=attempts;
      Console.WriteLine(new JavaScriptSerializer().Serialize(all));return 0;
    }catch(Exception ex){while(ex.InnerException!=null)ex=ex.InnerException;Console.Error.WriteLine(ex);return 1;}
  }
}
