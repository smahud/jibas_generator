// VM string oracle v2 - batch decoding from an ints file.
// Usage:
//   VmOracle2.exe <sandboxDir> file <intsFile> <outFile> [warm]
// Steps: optionally warm decoder init via real method 0x060008B9, then decode
// every int with worker 0x06000349(i, true) + wrapper 0x06000348(i), TSV out.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;

public static class VmOracle2 {
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

    static int Main(string[] args) {
        sandbox = Path.GetFullPath(args[0]);
        string mode = args[1];
        string inFile = args[2];
        string outFile = args[3];
        bool warm = args.Length > 4 && args[4] == "warm";
        AppDomain.CurrentDomain.AssemblyResolve += ResolveDep;
        Assembly asm = Assembly.LoadFrom(Path.Combine(sandbox, "FaceFgrClient.exe"));
        module = asm.ManifestModule;
        MethodInfo worker = (MethodInfo)module.ResolveMethod(0x06000349);
        MethodInfo wrapper = (MethodInfo)module.ResolveMethod(0x06000348);

        string warmNote = "cold";
        if (warm) {
            try {
                MethodInfo pathGet = (MethodInfo)module.ResolveMethod(0x060008B9);
                object r = pathGet.Invoke(null, null);
                warmNote = "warm ok: " + (string)r;
            } catch (Exception ex) { warmNote = "warm FAILED: " + Shown(ex); }
        }

        var ints = new List<int>();
        foreach (string line in File.ReadAllLines(inFile)) {
            string s = line.Trim();
            if (s.Length == 0) continue;
            s = s.Split('\t')[0].Trim();
            if (s.Length == 0) continue;
            int v;
            if (!int.TryParse(s, out v)) continue;
            ints.Add(v);
        }

        using (StreamWriter w = new StreamWriter(outFile)) {
            w.WriteLine("# oracle=" + warmNote);
            foreach (int i in ints) {
                string a = null, b = null;
                try { a = (string)wrapper.Invoke(null, new object[] { i }); } catch (Exception ex) { a = "<ERR " + Shown(ex) + ">"; }
                if (a != null && a.StartsWith("<ERR")) {
                    try { b = (string)worker.Invoke(null, new object[] { i, false }); } catch (Exception ex) { b = "<ERR " + Shown(ex) + ">"; }
                }
                string val = (b != null) ? b : a;
                w.WriteLine(i + "\t" + (val == null ? "<null>" : val.Replace("\r", "\\r").Replace("\n", "\\n")));
            }
        }
        Console.WriteLine("decoded " + ints.Count + " ints -> " + outFile);
        return 0;
    }
}
