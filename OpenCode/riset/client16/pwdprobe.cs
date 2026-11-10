// Decode FaceFgrClient config DBPASSWORD via the client's own method 0x06000A46.
// Also dumps the PasswordDeriveBytes password holder (0x040008B6) and the 13-byte
// salt binder (0x0400092B), and the raw decrypt helper 0x06000A45/'s internals
// cannot be called directly - we call the real string method end-to-end.
// Usage: PwdProbe.exe <sandboxDir> <encValue> [moreValues...]
using System;
using System.IO;
using System.Reflection;

public static class PwdProbe {
    static string sandbox;

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
        AppDomain.CurrentDomain.AssemblyResolve += ResolveDep;
        Assembly asm = Assembly.LoadFrom(Path.Combine(sandbox, "FaceFgrClient.exe"));
        Module module = asm.ManifestModule;

        MethodInfo decode = (MethodInfo)module.ResolveMethod(0x06000A46);

        // holder + salt
        try {
            FieldInfo salt = module.ResolveField(0x0400092B);
            byte[] sb = (byte[])salt.GetValue(null);
            Console.Write("SALT 0x0400092B len " + sb.Length + " hex: ");
            foreach (byte b in sb) Console.Write(b.ToString("X2") + " ");
            Console.WriteLine();
        } catch (Exception ex) { Console.WriteLine("SALT read failed: " + Shown(ex)); }
        try {
            FieldInfo pwd = module.ResolveField(0x040008B6);
            object v = pwd.GetValue(null);
            Console.WriteLine("PWDHOLDER 0x040008B6 = '" + (v == null ? "<null>" : v.ToString()) + "'");
        } catch (Exception ex) { Console.WriteLine("PWDHOLDER read failed: " + Shown(ex)); }

        for (int i = 1; i < args.Length; i++) {
            try {
                object r = decode.Invoke(null, new object[] { args[i] });
                Console.WriteLine("DECODE '" + args[i] + "' -> '" + (r == null ? "<null>" : r.ToString()) + "'");
            } catch (Exception ex) {
                Console.WriteLine("DECODE '" + args[i] + "' FAILED: " + Shown(ex));
            }
        }
        return 0;
    }
}
