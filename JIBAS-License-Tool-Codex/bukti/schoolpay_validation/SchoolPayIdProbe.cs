using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
public static class SchoolPayIdProbe {
  static string dir = @"C:\Program Files (x86)\YIM\JIBAS SchoolPay Secure Server 10.5";
  public static int Main(string[] args) {
    try {
      AppDomain.CurrentDomain.AssemblyResolve += delegate(object s, ResolveEventArgs e) {
        string p=Path.Combine(dir,new AssemblyName(e.Name).Name+".dll");
        return File.Exists(p)?Assembly.LoadFrom(p):null;
      };
      Assembly a=Assembly.LoadFile(Path.Combine(dir,"SPayServer.exe"));
      Module m=a.ManifestModule;
      var result=new Dictionary<string,object>();
      if(args[0]=="strings") {
        var decode=(Func<int,string>)Delegate.CreateDelegate(typeof(Func<int,string>), (MethodInfo)m.ResolveMethod(0x06000063));
        foreach(string arg in args[1].Split(',')) { int value=int.Parse(arg); try { result[arg]=decode(value); } catch(Exception ex) {result[arg]="ERROR:"+ex.Message;} }
      } else if(args[0]=="call") {
        int token=Convert.ToInt32(args[1],16); object value=m.ResolveMethod(token).Invoke(null,null); result["value"]=value;
      } else if(args[0]=="dates") {
        foreach(string stamp in args[1].Split(',')) {
          DateTime dt=DateTime.Parse(stamp,System.Globalization.CultureInfo.InvariantCulture);
          result[stamp]=m.ResolveMethod(0x06000708).Invoke(null,new object[]{dt});
        }
      } else if(args[0]=="hardware") {
        string disk=(string)m.ResolveMethod(0x06000943).Invoke(null,null);
        string uuid=(string)m.ResolveMethod(0x06000944).Invoke(null,null);
        result["disk_serial_raw"]=disk; result["uuid"]=uuid;
        result["original_system_id"]=m.ResolveMethod(0x06000945).Invoke(null,null);
        result["original_md5"]=m.ResolveMethod(0x06000989).Invoke(null,new object[]{disk+uuid});
      } else if(args[0]=="db") {
        Assembly mysql=Assembly.LoadFrom(Path.Combine(dir,"MySql.Data.dll"));
        Type t=mysql.GetType("MySql.Data.MySqlClient.MySqlConnection");
        object conn=Activator.CreateInstance(t,"server=127.0.0.1;port="+args[1]+";user id=root;password="+Environment.GetEnvironmentVariable("ID_AUDIT_MYSQL_PASSWORD")+";charset=utf8mb4");
        t.GetMethod("Open").Invoke(conn,null);
        result["value"]=m.ResolveMethod(0x06000824).Invoke(null,new object[]{conn});
        t.GetMethod("Close").Invoke(conn,null);
      }
      Console.WriteLine(new JavaScriptSerializer().Serialize(result)); return 0;
    } catch(Exception ex) {
      while(ex.InnerException!=null)ex=ex.InnerException;
      Console.Error.WriteLine(ex); return 1;
    }
  }
}
