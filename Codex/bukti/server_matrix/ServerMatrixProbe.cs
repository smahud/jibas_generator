using System;
using System.IO;
using System.Reflection;
using System.Data;
using System.Collections.Generic;
using System.Web.Script.Serialization;

// Controlled replay: target bytes unmodified, environment fields injected.
// No Main/UI/database/network execution. Writes only unique temporary sandbox.
public static class ServerMatrixProbe {
    static Module m;
    static object Call(int t, params object[] a) { return m.ResolveMethod(t).Invoke(null,a); }
    static void Set(int t, object v) { m.ResolveField(t).SetValue(null,v); }
    static object Get(int t) { return m.ResolveField(t).GetValue(null); }
    static object Import(string p) {
        try { return Call(0x060006CC,Path.GetFullPath(p)); }
        catch(Exception e) { while(e.InnerException!=null)e=e.InnerException; return e.GetType().Name+": "+e.Message; }
    }
    static Dictionary<string,object> Check(string name,string db,string sys,int count,DateTime now,string client) {
        Set(0x040004D6,false);Set(0x040004DF,false);Set(0x040004E0,true);
        Set(0x040004D7,count);Set(0x040004DB,db);Set(0x040004E7,sys);
        Set(0x040004DC,(long)Call(0x0600066B,now));Set(0x040004EE,client);Set(0x040004DA,false);
        Set(0x0400033D,0);Set(0x04000343,true);Set(0x040004D8,"");Set(0x040004D9,-999);
        Call(0x06000913,new object[]{null});
        return new Dictionary<string,object>{{"name",name},{"dbid",db},{"system_id",sys},{"face_count",count},{"simulated_time",now.ToString("s")},{"accepted",Call(0x0600090D)},{"status_code",Get(0x040004D9)},{"status_text",Get(0x040004D8)}};
    }
    public static int Main(string[] args) {
        var result=new Dictionary<string,object>();
        string sandbox=Path.Combine(Path.GetTempPath(),"codex-server-matrix",Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(sandbox);Environment.CurrentDirectory=sandbox;
        try {
            string dir=@"C:\Program Files\YIM\JIBAS Face Server 16.5";
            AppDomain.CurrentDomain.AssemblyResolve+=delegate(object s,ResolveEventArgs e){ string p=Path.Combine(dir,new AssemblyName(e.Name).Name+".dll"); return File.Exists(p)?Assembly.LoadFrom(p):null;};
            var asm=Assembly.LoadFile(Path.Combine(dir,"FaceServer.exe"));m=asm.ManifestModule;
            result["mvid"]=m.ModuleVersionId.ToString();
            result["artifact_sha256"]=BitConverter.ToString(System.Security.Cryptography.SHA256.Create().ComputeHash(File.ReadAllBytes(asm.Location))).Replace("-","").ToLowerInvariant();
            Set(0x04000395,sandbox);Call(0x060006C5);Call(0x060006C4);
            var tables=new List<Dictionary<string,object>>();
            foreach(var f in m.ResolveMethod(0x060006C4).DeclaringType.GetFields(BindingFlags.Static|BindingFlags.NonPublic|BindingFlags.Public)) {
                if(f.FieldType!=typeof(DataTable))continue;
                var table=f.GetValue(null) as DataTable;if(table==null)continue;
                var columns=new List<Dictionary<string,object>>();
                foreach(DataColumn c in table.Columns)columns.Add(new Dictionary<string,object>{{"name",c.ColumnName},{"type",c.DataType.FullName}});
                tables.Add(new Dictionary<string,object>{{"field_token",String.Format("0x{0:x8}",f.MetadataToken)},{"name",table.TableName},{"columns",columns}});
            }
            result["original_tables"]=tables;
            Set(0x040004DB,args[1]);Set(0x040004E7,args[2]);
            if(args.Length>3) result["previous_import"]=Import(args[3]);
            result["before_sequence"]=Get(0x040004F7);result["before_client"]=Get(0x040004EE);
            result["candidate_import"]=Import(args[0]);
            result["after_sequence"]=Get(0x040004F7);result["after_client"]=Get(0x040004EE);
            result["after_dbid"]=Get(0x040004F0);result["after_info1"]=Get(0x040004F8);
            result["cache_written"]=File.Exists(Path.Combine(sandbox,"license.enc"));
            if(Object.Equals(result["candidate_import"],true)) {
                string licDb=Convert.ToString(Get(0x040004F0)),licSys=Convert.ToString(Get(0x040004F8)),client=Convert.ToString(Get(0x040004EE));
                int cap=(int)Get(0x040004F5);DateTime exp=(DateTime)Get(0x040004F3);
                var cases=new List<Dictionary<string,object>>();DateTime now=new DateTime(2026,11,10,12,0,0);
                cases.Add(Check("actual_injected_environment",args[1],args[2],0,now,client));
                cases.Add(Check("matching_license_environment",licDb,licSys,0,now,client));
                cases.Add(Check("wrong_database",licDb=="ZZZZZ"?"ABCDE":"ZZZZZ",licSys,0,now,client));
                cases.Add(Check("wrong_system",licDb,licSys=="FFFFF"?"123AB":"FFFFF",0,now,client));
                cases.Add(Check("legacy_day_after_expiry",licDb,licSys,0,exp.AddDays(1),client));
                cases.Add(Check("expired",licDb,licSys,0,exp.AddYears(1),client));
                cases.Add(Check("at_capacity",licDb,licSys,cap,now,client));
                cases.Add(Check("over_capacity",licDb,licSys,cap+1,now,client));
                cases.Add(Check("trial",licDb,licSys,0,now,"TRIAL"));
                result["runtime_cases"]=cases;
            }
            result["sandbox"]=sandbox;
            result["boundary"]="Controlled original-method replay; IDs/count/time injected; database/network/main/UI not run; not production activation.";
            Console.WriteLine(new JavaScriptSerializer().Serialize(result));return 0;
        }catch(Exception e){while(e.InnerException!=null)e=e.InnerException;Console.Error.WriteLine(e);return 1;}
    }
}
