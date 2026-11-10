// End-to-end non-UI license probe for FaceFgrClient 16.10:
// 1) FACE loader chain (AF2 fills FACE pwd/iv, AF3 loader+validator)
// 2) Registration predicate 0x0600052D(s1,s2,s3,s4, ref msg) against real MySQL
// 3) Enrollment-limit load 0x0600082D (reads jbssat.fcface count when license bool true)
// Prints every relevant holder afterward. NO UI forms shown.
//
// Usage: DbProbe.exe <sandboxDir> <baseDir> [server port user password]
using System;
using System.IO;
using System.Reflection;
using System.Runtime.Serialization;
using System.Windows.Forms;

public static class DbProbe {
    static string sandbox;
    static Module module;

    static Assembly ResolveDep(object s, ResolveEventArgs ev) {
        string p = Path.Combine(sandbox, new AssemblyName(ev.Name).Name + ".dll");
        if (!File.Exists(p)) return null;
        return Assembly.LoadFrom(p);
    }

    static string Shown(Exception ex) {
        while (ex.InnerException != null && ex.InnerException.Message != null) ex = ex.InnerException;
        return ex.GetType().Name + ": " + ex.Message;
    }

    static string S(int token) {
        object v = module.ResolveField(token).GetValue(null);
        return v == null ? "<null>" : v.ToString();
    }

    static int Main(string[] args) {
        sandbox = Path.GetFullPath(args[0]);
        string baseDir = Path.GetFullPath(args[1]);
        bool hasCreds = args.Length >= 6;
        AppDomain.CurrentDomain.AssemblyResolve += ResolveDep;
        Assembly asm = Assembly.LoadFrom(Path.Combine(sandbox, "FaceFgrClient.exe"));
        module = asm.ManifestModule;

        module.ResolveField(0x04000369).SetValue(null, baseDir);
        try {
            ((MethodInfo)module.ResolveMethod(0x060008B9)).Invoke(null, null);
        } catch (Exception ex) { Console.WriteLine("warm FAILED: " + Shown(ex)); }
        module.ResolveField(0x04000369).SetValue(null, baseDir);

        // 1) FACE loader chain
        try { ((MethodInfo)module.ResolveMethod(0x06000AF2)).Invoke(null, null); }
        catch (Exception ex) { Console.WriteLine("AF2 threw: " + Shown(ex)); }
        try { ((MethodInfo)module.ResolveMethod(0x06000AF3)).Invoke(null, null); }
        catch (Exception ex) { Console.WriteLine("AF3 threw: " + Shown(ex)); }
        object vres = null;
        try { vres = ((MethodInfo)module.ResolveMethod(0x06000AF7)).Invoke(null, null); }
        catch (Exception ex) { Console.WriteLine("validator threw: " + Shown(ex)); }
        Console.WriteLine("FACE validator = " + vres);
        Console.WriteLine("mode  0x040004C7 = '" + S(0x040004C7) + "'");
        Console.WriteLine("klien 0x040004C8 = '" + S(0x040004C8) + "'");
        Console.WriteLine("dbid  0x040004C9 = '" + S(0x040004C9) + "'");

        // 2) registration predicate (read-only SELECT NOW + information_schema COUNT)
        if (hasCreds) {
            Type predType = module.ResolveMethod(0x0600052D).DeclaringType;
            object inst = null;
            try { inst = FormatterServices.GetUninitializedObject(predType); }
            catch (Exception ex) { Console.WriteLine("instance create failed: " + Shown(ex)); }
            if (inst != null) {
                try {
                    FieldInfo cu = null;
                    foreach (FieldInfo f in predType.GetFields(BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public)) {
                        if (f.MetadataToken == 0x04000231) { cu = f; break; }
                    }
                    if (cu != null) {
                        object dummy = null;
                        try { dummy = Activator.CreateInstance(cu.FieldType); }
                        catch { dummy = FormatterServices.GetUninitializedObject(cu.FieldType); }
                        cu.SetValue(inst, dummy);
                    }
                    object[] pa = { args[2], args[3], args[4], args[5], "" };
                    object ok = ((MethodInfo)module.ResolveMethod(0x0600052D)).Invoke(inst, pa);
                    Console.WriteLine("PREDICATE result = " + ok);
                    Console.WriteLine("PREDICATE msg = '" + pa[4] + "'");
                    Console.WriteLine("holder msg 0x0400051C = '" + S(0x0400051C) + "'");
                    Console.WriteLine("holder ticks 0x0400051D = " + S(0x0400051D));
                    Console.WriteLine("holder Date 0x0400051E = " + S(0x0400051E));
                    // simulate auto-register success: license bool true
                    module.ResolveField(0x04000378).SetValue(null, true);
                    Console.WriteLine("license bool 0x04000378 set true");
                } catch (Exception ex) { Console.WriteLine("PREDICATE threw: " + Shown(ex)); }
            }
        }

        // 3) enrollment limit loader
        try {
            ((MethodInfo)module.ResolveMethod(0x0600082D)).Invoke(null, null);
        } catch (Exception ex) { Console.WriteLine("limit loader threw: " + Shown(ex)); }
        object b4 = module.ResolveField(0x040004B4).GetValue(null);
        object b5 = module.ResolveField(0x040004B5).GetValue(null);
        Console.WriteLine("limit bool 0x040004B4 = " + b4 + "  count 0x040004B5 = " + b5);
        return 0;
    }
}
