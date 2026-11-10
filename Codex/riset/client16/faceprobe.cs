// Empirical probe of the FACE cache validator (0x06000AF7) at runtime.
// 1) Loads FaceFgrClient.exe from SANDBOX dir; sets base-path holder 0x04000369 to <base>.
// 2) Warms the VM string decoder once via real method 0x060008B9 (fresh decode cache OK).
// 3) Re-sets base holder to <base>.
// 4) Invokes validator 0x06000AF7 and prints the boolean/exception + global mode 0x040004C7.
// 5) Optionally sets the FACE pwd/IV holder pair 0x04000375/76 via reflection first.
// Also prints ExceptionHandlingClauses for key methods.
//
// Usage:
//   FaceProbe.exe <sandboxDir> <baseDir> plain
//   FaceProbe.exe <sandboxDir> <baseDir> profile <pwd> <iv>
using System;
using System.IO;
using System.Reflection;

public static class FaceProbe {
    static string sandbox;
    static Module module;

    static Assembly ResolveDep(object s, ResolveEventArgs ev) {
        string p = Path.Combine(sandbox, new AssemblyName(ev.Name).Name + ".dll");
        if (!File.Exists(p)) return null;
        return Assembly.LoadFrom(p);
    }

    static void ShowHolders() {
        Console.WriteLine("  FGR pwd 0x04000366 = '" + GetStaticString(0x04000366) + "'");
        Console.WriteLine("  FGR iv  0x04000367 = '" + GetStaticString(0x04000367) + "'");
        Console.WriteLine("  FACE pwd 0x04000375 = '" + GetStaticString(0x04000375) + "'");
        Console.WriteLine("  FACE iv  0x04000376 = '" + GetStaticString(0x04000376) + "'");
    }

    static string Shown(Exception ex) {
        while (ex.InnerException != null && ex.InnerException.Message != null) ex = ex.InnerException;
        return ex.GetType().Name + ": " + ex.Message;
    }

    static void SetStaticField(int token, object value) {
        FieldInfo f = module.ResolveField(token);
        f.SetValue(null, value);
    }

    static string GetStaticString(int token) {
        object v = module.ResolveField(token).GetValue(null);
        return v == null ? "<null>" : v.ToString();
    }

    static int Main(string[] args) {
        sandbox = Path.GetFullPath(args[0]);
        string baseDir = Path.GetFullPath(args[1]);
        string op = args[2];
        AppDomain.CurrentDomain.AssemblyResolve += ResolveDep;
        Assembly asm = Assembly.LoadFrom(Path.Combine(sandbox, "FaceFgrClient.exe"));
        module = asm.ManifestModule;

        SetStaticField(0x04000369, baseDir);
        Console.WriteLine("base holder -> " + GetStaticString(0x04000369));

        try {
            MethodInfo fgrGetter = (MethodInfo)module.ResolveMethod(0x060008B9);
            object r = fgrGetter.Invoke(null, null);
            Console.WriteLine("warm ok -> " + r);
        } catch (Exception ex) { Console.WriteLine("warm FAILED: " + Shown(ex)); }

        SetStaticField(0x04000369, baseDir);
        Console.WriteLine("base holder re-set -> " + GetStaticString(0x04000369));

        if (op == "profile" && args.Length >= 5) {
            SetStaticField(0x04000375, args[3]);
            SetStaticField(0x04000376, args[4]);
            Console.WriteLine("FACE holders set: pwd='" + args[3] + "' iv='" + args[4] + "'");
        }

        if (op == "fgr") {
            Console.WriteLine("holders BEFORE fgr chain:");
            ShowHolders();
            try {
                MethodInfo bc = (MethodInfo)module.ResolveMethod(0x060008BC);
                bc.Invoke(null, null);
                Console.WriteLine("BC (fgr dynamic pre-init) ok");
            } catch (Exception ex) { Console.WriteLine("BC threw: " + Shown(ex)); }
            Console.WriteLine("holders AFTER BC:");
            ShowHolders();
            try {
                MethodInfo bd = (MethodInfo)module.ResolveMethod(0x060008BD);
                bd.Invoke(null, null);
                Console.WriteLine("BD (fgr loader) ok");
            } catch (Exception ex) { Console.WriteLine("BD threw: " + Shown(ex)); }
            Console.WriteLine("holders AFTER BD:");
            ShowHolders();
            try {
                MethodInfo fval = (MethodInfo)module.ResolveMethod(0x060008C0);
                object r = fval.Invoke(null, null);
                Console.WriteLine("FGR VALIDATOR = " + (bool)r);
            } catch (Exception ex) { Console.WriteLine("FGR VALIDATOR threw: " + Shown(ex)); }
            Console.WriteLine("mode 0x040004C7 = '" + GetStaticString(0x040004C7) + "'");
            return 0;
        }

        if (op == "loader") {
            Console.WriteLine("holders BEFORE loader run:");
            ShowHolders();
            try {
                MethodInfo af2 = (MethodInfo)module.ResolveMethod(0x06000AF2);
                af2.Invoke(null, null);
                Console.WriteLine("AF2 (dynamic pre-init) ok");
            } catch (Exception ex) { Console.WriteLine("AF2 threw: " + Shown(ex)); }
            Console.WriteLine("holders AFTER AF2:");
            ShowHolders();
            try {
                MethodInfo af3 = (MethodInfo)module.ResolveMethod(0x06000AF3);
                af3.Invoke(null, null);
                Console.WriteLine("AF3 (face loader) ok");
            } catch (Exception ex) { Console.WriteLine("AF3 threw: " + Shown(ex)); }
            Console.WriteLine("holders AFTER AF3:");
            ShowHolders();
            try {
                MethodInfo validator2 = (MethodInfo)module.ResolveMethod(0x06000AF7);
                object r = validator2.Invoke(null, null);
                Console.WriteLine("VALIDATOR AFTER LOADER = " + (bool)r);
            } catch (Exception ex) { Console.WriteLine("VALIDATOR threw: " + Shown(ex)); }
            Console.WriteLine("mode 0x040004C7 = '" + GetStaticString(0x040004C7) + "'");
            Console.WriteLine("klien 0x040004C8 = '" + GetStaticString(0x040004C8) + "'");
            Console.WriteLine("dbid  0x040004C9 = '" + GetStaticString(0x040004C9) + "'");
            return 0;
        }

        string facePath = Path.Combine(baseDir, "licenseface.enc");
        Console.WriteLine("cache exists: " + File.Exists(facePath) + "  len " + (File.Exists(facePath) ? new FileInfo(facePath).Length.ToString() : "-"));

        MethodInfo validator = (MethodInfo)module.ResolveMethod(0x06000AF7);
        bool result = false;
        try {
            object r = validator.Invoke(null, null);
            result = (bool)r;
            Console.WriteLine("VALIDATOR RESULT = " + result);
        } catch (Exception ex) {
            Console.WriteLine("VALIDATOR THREW (outer): " + Shown(ex));
        }

        Console.WriteLine("mode 0x040004C7 = '" + GetStaticString(0x040004C7) + "'");
        Console.WriteLine("klien 0x040004C8 = '" + GetStaticString(0x040004C8) + "'");
        Console.WriteLine("dbid  0x040004C9 = '" + GetStaticString(0x040004C9) + "'");
        Console.WriteLine("seri  0x040004CA = '" + GetStaticString(0x040004CA) + "'");
        Console.WriteLine("limit 0x040004CB = '" + GetStaticString(0x040004CB) + "'");
        object dt = module.ResolveField(0x040004CC).GetValue(null);
        Console.WriteLine("expiry 0x040004CC = " + (dt == null ? "<null>" : dt.ToString()));
        object mc = module.ResolveField(0x040004CE).GetValue(null);
        Console.WriteLine("maxclient 0x040004CE = " + (mc == null ? "<null>" : mc.ToString()));
        object seq = module.ResolveField(0x040004D0).GetValue(null);
        Console.WriteLine("sequence 0x040004D0 = " + (seq == null ? "<null>" : seq.ToString()));
        Console.WriteLine("info1 0x040004D1 = '" + GetStaticString(0x040004D1) + "'");

        // EH clauses of the validator + FGR validator + loaders for forensics
        foreach (int tok in new int[] { 0x06000AF7, 0x06000ADB, 0x06000ADC }) {
            try {
                MethodBase mb = module.ResolveMethod(tok);
                MethodBody body = mb.GetMethodBody();
                if (body == null) continue;
                var clauses = body.ExceptionHandlingClauses;
                Console.WriteLine("EH 0x" + tok.ToString("X8") + ": " + clauses.Count + " clauses");
                foreach (System.Reflection.ExceptionHandlingClause c in clauses) {
                    Console.WriteLine("    Flags=" + c.Flags + " TryOff=" + c.TryOffset + " TryLen=" + c.TryLength
                        + " HandlerOff=" + c.HandlerOffset + " HandlerLen=" + c.HandlerLength
                        + " CatchTok=0x" + c.CatchType.MetadataToken.ToString("X8") + " FilterOff=" + c.FilterOffset);
                }
            } catch (Exception ex) { Console.WriteLine("EH 0x" + tok.ToString("X8") + " err: " + Shown(ex)); }
        }
        return 0;
    }
}
