using System;
using System.IO;
using System.Reflection;

// Runs the ORIGINAL FaceServer.exe DatabaseId getter (0x06000AC3) against the live MySQL
// on localhost to prove how the Database ID is computed by the application itself.
public static class RuntimeDbId {
    static Module module;

    static int Main(string[] args) {
        string sandbox = Path.Combine(Path.GetTempPath(), "opencode", "runtime_dbid");
        Directory.CreateDirectory(sandbox);
        Environment.CurrentDirectory = sandbox;
        string targetDir = @"C:\Program Files\YIM\JIBAS Face Server 16.5";
        try {
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object s, ResolveEventArgs ev) {
                string p = Path.Combine(targetDir, new AssemblyName(ev.Name).Name + ".dll");
                return File.Exists(p) ? Assembly.LoadFrom(p) : null;
            };
            Assembly asm = Assembly.LoadFile(Path.Combine(targetDir, "FaceServer.exe"));
            module = asm.ManifestModule;
            // Load MySql.Data from the app directory (version pinned by FaceServer).
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object s2, ResolveEventArgs ev2) {
                string q = Path.Combine(targetDir, new AssemblyName(ev2.Name).Name + ".dll");
                return File.Exists(q) ? Assembly.LoadFrom(q) : null;
            };
            Assembly mysqlAsm = Assembly.LoadFrom(Path.Combine(targetDir, "MySql.Data.dll"));
            Type connType = mysqlAsm.GetType("MySql.Data.MySqlClient.MySqlConnection");
            object conn = Activator.CreateInstance(connType, "server=127.0.0.1;port=3434;user id=root;password=kebersamaan;persistsecurityinfo=false;charset=utf8mb4");
            object open = connType.GetMethod("Open").Invoke(conn, null);
            string dbid = (string)module.ResolveMethod(0x06000AC3).Invoke(null, new object[] { conn });
            Console.WriteLine("Original AC3 DatabaseId: [" + dbid + "]");
            object close = connType.GetMethod("Close").Invoke(conn, null);
            return 0;
        } catch (Exception ex) {
            while (ex.InnerException != null) ex = ex.InnerException;
            Console.Error.WriteLine("AC3 error: " + ex);
            return 1;
        }
    }
}
