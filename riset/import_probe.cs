using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;

// Combined provenance proof harness for the OpenCode license tool.
// Fills 0x040004DB with the ORIGINAL DatabaseId getter (0x06000AC3) driving the
// live MySQL, fills 0x040004E7 with the ORIGINAL SystemId generator (0x0600059B),
// then runs the ORIGINAL license importer (0x060006CC) against a candidate file.
// Usage: ImportProbe.exe <label> <licensePath>
public static class ImportProbe {
    static Module module;
    static void Set(int token, object value) { module.ResolveField(token).SetValue(null, value); }
    static object Get(int token) { return module.ResolveField(token).GetValue(null); }
    static object Call(int token) { return module.ResolveMethod(token).Invoke(null, null); }

    static int Main(string[] args) {
        string label = args[0];
        string sandbox = Path.Combine(Path.GetTempPath(), "opencode", "import_" + label);
        Directory.CreateDirectory(sandbox);
        Environment.CurrentDirectory = sandbox;
        string targetDir = @"C:\Program Files\YIM\JIBAS Face Server 16.5";
        var result = new Dictionary<string, object>();
        var finalException = new List<string>();
        try {
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object s, ResolveEventArgs ev) {
                string p = Path.Combine(targetDir, new AssemblyName(ev.Name).Name + ".dll");
                return File.Exists(p) ? Assembly.LoadFrom(p) : null;
            };
            Assembly asm = Assembly.LoadFile(Path.Combine(targetDir, "FaceServer.exe"));
            module = asm.ManifestModule;
            Set(0x04000395, sandbox);
            Call(0x060006C5); Call(0x060006C4);

            // original SystemId (WMI) -> runtime field 0x040004E7
            string sysid = (string)module.ResolveMethod(0x0600059B).Invoke(null, null);
            Set(0x040004E7, sysid);
            result["original_system_id"] = sysid;

            // original DatabaseId (live MySQL splang procedures) -> 0x040004DB
            Assembly mysqlAsm = Assembly.LoadFrom(Path.Combine(targetDir, "MySql.Data.dll"));
            Type connType = mysqlAsm.GetType("MySql.Data.MySqlClient.MySqlConnection");
            object conn = Activator.CreateInstance(connType,
                "server=127.0.0.1;port=3434;user id=root;password=kebersamaan;persistsecurityinfo=false;charset=utf8mb4");
            connType.GetMethod("Open").Invoke(conn, null);
            string dbid = (string)module.ResolveMethod(0x06000AC3).Invoke(null, new object[] { conn });
            Set(0x040004DB, dbid);
            connType.GetMethod("Close").Invoke(conn, null);
            result["original_database_id"] = dbid;

            string cache = Path.Combine(sandbox, "license.enc");
            result["cache_before"] = File.Exists(cache);
            result["before_client"] = Convert.ToString(Get(0x040004EE));
            result["before_sequence"] = Get(0x040004F7);

            bool accepted = false;
            try {
                accepted = (bool)module.ResolveMethod(0x060006CC).Invoke(null,
                    new object[] { Path.GetFullPath(args[1]) });
            } catch (Exception ex) {
                while (ex.InnerException != null) ex = ex.InnerException;
                finalException.Add(ex.GetType().FullName + ": " + ex.Message);
            }
            result["importer_returned"] = accepted;
            result["exception"] = finalException;
            result["cache_after"] = File.Exists(cache);
            result["license_enc_sha256"] = File.Exists(cache)
                ? Convert.ToBase64String(System.Security.Cryptography.SHA256.Create()
                    .ComputeHash(File.ReadAllBytes(cache))) : null;
            result["after_client"] = Convert.ToString(Get(0x040004EE));
            result["after_klienid"] = Convert.ToString(Get(0x040004EE));
            result["after_dbid_field"] = Convert.ToString(Get(0x040004F0));
            result["after_info1"] = Convert.ToString(Get(0x040004F8));
            result["after_maxclient"] = Convert.ToString(Get(0x040004F5));
            result["after_limitdate"] = Convert.ToString(Get(0x040004F3));
            result["after_licenselimit"] = Convert.ToString(Get(0x040004F2));
            result["after_sequence"] = Get(0x040004F7);
        } catch (Exception ex) {
            while (ex.InnerException != null) ex = ex.InnerException;
            result["error"] = ex.GetType().FullName + ": " + ex.Message;
        }
        result["label"] = label;
        string json = new JavaScriptSerializer().Serialize(result);
        File.WriteAllText(Path.Combine(sandbox, "import_result.json"), json, new System.Text.UTF8Encoding(false));
        Console.WriteLine(json);
        return 0;
    }
}
