// VM string oracle for FaceFgrClient 16.10.
// Strategy: warm the one-time decoder init by first invoking a REAL client
// method (0x060008B9, the FACE cache-path getter) in this process, so the
// worker's GetCallingAssembly/StackTrace init runs with legit frames. Then
// invoke the worker 0x06000349(Int32, Boolean) directly for arbitrary ints.
//
// Usage:
//   VmOracle.exe <sandboxDir> warm <int1> <int2> ...   (warm via 0x060008B9, then decode ints via worker+wrapper)
//   VmOracle.exe <sandboxDir> cold <int1> <int2> ...   (decode ints via worker WITHOUT warm-up)
using System;
using System.IO;
using System.Reflection;

public static class VmOracle {
    static string sandbox;
    static Module module;

    static Assembly ResolveDep(object s, ResolveEventArgs ev) {
        string p = Path.Combine(sandbox, new AssemblyName(ev.Name).Name + ".dll");
        if (!File.Exists(p)) return null;
        return Assembly.LoadFrom(p);
    }

    static MethodBase M(int token) { return module.ResolveMethod(token); }

    static string Shown(Exception ex) {
        while (ex.InnerException != null && ex.InnerException.Message != null) ex = ex.InnerException;
        return ex.GetType().Name + ": " + ex.Message;
    }

    static string Decode(MethodInfo worker, int i, bool flag) {
        try {
            object r = worker.Invoke(null, new object[] { i, flag });
            return (string)r;
        } catch (Exception ex) { return "<ERR " + Shown(ex) + ">"; }
    }

    static int Main(string[] args) {
        sandbox = Path.GetFullPath(args[0]);
        string mode = args[1];
        AppDomain.CurrentDomain.AssemblyResolve += ResolveDep;
        Assembly asm = Assembly.LoadFrom(Path.Combine(sandbox, "FaceFgrClient.exe"));
        module = asm.ManifestModule;

        // worker + wrapper
        MethodInfo worker = (MethodInfo)M(0x06000349);
        MethodInfo wrapper = (MethodInfo)M(0x06000348);

        if (mode == "warm") {
            MethodInfo pathGet = (MethodInfo)M(0x060008B9);
            try {
                object path = pathGet.Invoke(null, null);
                Console.WriteLine("WARM 0x060008B9 -> " + path);
            } catch (Exception ex) { Console.WriteLine("WARM FAILED: " + Shown(ex)); }
        }

        int[] ints = new int[args.Length - 2];
        for (int i = 0; i < ints.Length; i++) ints[i] = Convert.ToInt32(args[i + 2]);

        foreach (int i in ints) {
            string wf = Decode(worker, i, false);
            string wt = Decode(worker, i, true);
            string wr = null;
            try {
                object r = wrapper.Invoke(null, new object[] { i });
                wr = (string)r;
            } catch (Exception ex) { wr = "<ERR " + Shown(ex) + ">"; }
            Console.WriteLine("INT " + i.ToString() + "  w(false)=" + Show(wf) + "  w(true)=" + Show(wt) + "  wrap=" + Show(wr));
        }
        return 0;
    }

    static string Show(string s) {
        if (s == null) return "<null>";
        return "'" + s.Replace("\r", "\\r").Replace("\n", "\\n").Replace("\t", "\\t") + "'";
    }
}
