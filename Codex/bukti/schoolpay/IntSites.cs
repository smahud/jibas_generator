// Extract every <int constant> immediately followed by call 0x06000063 (string decode)
// in SPayServer.exe. Output: distinct ints, one per line, sorted.
// Usage: IntSites.exe <dir> <fileName> <outFile>
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;

public static class IntSites {
    static string dir;
    static Module module;
    static Dictionary<int, OpCode> ops = new Dictionary<int, OpCode>();
    static SortedSet<int> ints = new SortedSet<int>();
    static Dictionary<int, List<string>> perMethod = new Dictionary<int, List<string>>();

    static IEnumerable<MethodBase> AllMethods(Assembly asm) {
        Type[] types;
        try { types = asm.GetTypes(); } catch (ReflectionTypeLoadException ex) { types = ex.Types; }
        BindingFlags f = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static
            | BindingFlags.Instance | BindingFlags.DeclaredOnly;
        foreach (Type t in types) {
            if (t == null) continue;
            MethodInfo[] ms = null;
            try { ms = t.GetMethods(f); } catch { }
            if (ms != null) foreach (MethodInfo m in ms) if (!m.IsAbstract) yield return m;
            ConstructorInfo[] cs = null;
            try { cs = t.GetConstructors(f); } catch { }
            if (cs != null) foreach (ConstructorInfo c in cs) yield return c;
        }
    }

    static int Main(string[] args) {
        FieldInfo[] fields = typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static);
        foreach (FieldInfo fi in fields) {
            OpCode o = (OpCode)fi.GetValue(null);
            ops[unchecked((ushort)o.Value)] = o;
        }
        dir = args[0];
        string fileName = args[1];
        string outFile = args[2];
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object s, ResolveEventArgs ev) {
            string p = Path.Combine(dir, new AssemblyName(ev.Name).Name + ".dll");
            return File.Exists(p) ? Assembly.LoadFrom(p) : null;
        };
        Assembly asm = Assembly.LoadFrom(Path.Combine(dir, fileName));
        module = asm.ManifestModule;
        int decoder = 0x06000063;

        foreach (MethodBase m in AllMethods(asm)) {
            int token = m.MetadataToken;
            if ((token & 0xFF000000) != 0x06000000) continue;
            MethodBody b;
            try { b = m.GetMethodBody(); } catch { continue; }
            if (b == null) continue;
            byte[] il;
            try { il = b.GetILAsByteArray(); } catch { continue; }
            int p = 0;
            OpCode prevOp = OpCodes.Nop;
            int prevInt = 0;
            while (p < il.Length) {
                int code = il[p++];
                if (code == 0xFE && p < il.Length) code = 0xFE00 | il[p++];
                OpCode op;
                if (!ops.TryGetValue(unchecked((ushort)code), out op)) break;
                int skip;
                int constVal = 0;
                switch (op.OperandType) {
                    case OperandType.InlineNone: skip = 0; break;
                    case OperandType.ShortInlineI:
                        skip = 1;
                        if (op == OpCodes.Ldc_I4_S) constVal = (sbyte)il[p];
                        break;
                    case OperandType.ShortInlineBrTarget: skip = 1; break;
                    case OperandType.ShortInlineVar: skip = 1; break;
                    case OperandType.InlineVar: skip = 2; break;
                    case OperandType.InlineI8: case OperandType.InlineR: skip = 8; break;
                    case OperandType.InlineSwitch: { int n = BitConverter.ToInt32(il, p); skip = 4 + 4 * n; break; }
                    case OperandType.InlineI: skip = 4; constVal = BitConverter.ToInt32(il, p); break;
                    default: skip = 4; constVal = BitConverter.ToInt32(il, p); break;
                }
                if (op == OpCodes.Ldc_I4) constVal = BitConverter.ToInt32(il, p);
                if (op == OpCodes.Ldc_I4_M1 || op == OpCodes.Ldc_I4_0 || op == OpCodes.Ldc_I4_1
                    || op == OpCodes.Ldc_I4_2 || op == OpCodes.Ldc_I4_3 || op == OpCodes.Ldc_I4_4
                    || op == OpCodes.Ldc_I4_5 || op == OpCodes.Ldc_I4_6 || op == OpCodes.Ldc_I4_7
                    || op == OpCodes.Ldc_I4_8) {
                    constVal = (op == OpCodes.Ldc_I4_M1) ? -1 : (int)((ushort)op.Value - (ushort)OpCodes.Ldc_I4_0.Value);
                }
                bool isCall = (op == OpCodes.Call || op == OpCodes.Callvirt);
                int callee = 0;
                if (isCall) callee = BitConverter.ToInt32(il, p);
                p += skip;
                if (isCall && callee == decoder && (prevOp == OpCodes.Ldc_I4 || prevOp == OpCodes.Ldc_I4_S)) {
                    if (ints.Add(prevInt)) {
                        List<string> l;
                        if (!perMethod.TryGetValue(prevInt, out l)) { l = new List<string>(); perMethod[prevInt] = l; }
                        l.Add("0x" + token.ToString("X8"));
                    }
                }
                prevOp = op;
                prevInt = constVal;
            }
        }
        using (StreamWriter w = new StreamWriter(outFile)) {
            foreach (int i in ints) {
                w.Write(i.ToString());
                foreach (string meth in perMethod[i]) w.Write("\t" + meth);
                w.WriteLine();
            }
        }
        Console.WriteLine("distinct decoder ints: " + ints.Count + " -> " + outFile);
        return 0;
    }
}


