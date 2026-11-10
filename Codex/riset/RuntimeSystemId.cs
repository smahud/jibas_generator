using System;
using System.IO;
using System.Reflection;
using System.Text;

// Runs the ORIGINAL FaceServer.exe SystemId generator (0x0600059B) in this process.
// Read-only WMI queries; does not touch installed files (license cache path set to sandbox).
public static class RuntimeSystemId {
    static Module module;
    static void Set(int token, object value) { module.ResolveField(token).SetValue(null, value); }
    static object Get(int token) { return module.ResolveField(token).GetValue(null); }

    static int Main(string[] args) {
        string sandbox = args.Length > 0 ? args[0] : Path.Combine(Path.GetTempPath(), "opencode", "runtime_sysid");
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
            Set(0x04000395, sandbox);
            // initialize crypto/config classes so static initializers have their dirs set
            Call(0x060006C5);
            Call(0x060006C4);
            string systemId;
            try {
                systemId = (string)module.ResolveMethod(0x0600059B).Invoke(null, null);
                Console.WriteLine("SystemId(0x0600059B): [" + systemId + "]");
            } catch (Exception ex) {
                while (ex.InnerException != null) ex = ex.InnerException;
                Console.Error.WriteLine("59B error: " + ex);
                return 1;
            }
            // also run the two raw hardware readers to compare WMI behavior of original code
            try { Console.WriteLine("diskpath(0x06000599): [" + module.ResolveMethod(0x06000599).Invoke(null, null) + "]"); }
            catch (Exception ex) { while (ex.InnerException != null) ex = ex.InnerException; Console.WriteLine("diskpath(0x06000599) error: " + ex.Message + " :: " + ex); }
            try { Console.WriteLine("csp(0x0600059A): [" + module.ResolveMethod(0x0600059A).Invoke(null, null) + "]"); }
            catch (Exception ex) { while (ex.InnerException != null) ex = ex.InnerException; Console.WriteLine("csp(0x0600059A) error: " + ex.Message + " :: " + ex); }
            Console.WriteLine("DB id field: [" + Get(0x040004DB) + "]  sysid field: [" + Get(0x040004E7) + "]");
            return 0;
        } catch (Exception ex) { while (ex.InnerException != null) ex = ex.InnerException; Console.Error.WriteLine(ex); return 1; }
    }

    static void Call(int token) { module.ResolveMethod(token).Invoke(null, null); }
}
