// Reflection-only IL reader; never executes target methods.
using System;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
using System.Collections.Generic;
public static class SjsStaticProbe {
 static Module module; static Dictionary<ushort,OpCode> ops=new Dictionary<ushort,OpCode>();
 static IEnumerable<MethodBase> Methods(Assembly a){foreach(Type t in a.GetTypes()){foreach(var m in t.GetMethods((BindingFlags)62))yield return m;foreach(var m in t.GetConstructors((BindingFlags)62))yield return m;}}
 public static int Main(string[] args){string dir=Path.GetDirectoryName(args[0]);AppDomain.CurrentDomain.ReflectionOnlyAssemblyResolve+=(s,e)=>{string p=Path.Combine(dir,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.ReflectionOnlyLoadFrom(p):Assembly.ReflectionOnlyLoad(e.Name);};
 foreach(var f in typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static)){var op=(OpCode)f.GetValue(null);ops[unchecked((ushort)op.Value)]=op;}
 var a=Assembly.ReflectionOnlyLoadFrom(args[0]);module=a.ManifestModule;var seen=new HashSet<int>();var counts=new Dictionary<int,int>();
 foreach(var m in Methods(a)){if(!seen.Add(m.MetadataToken))continue;var body=m.GetMethodBody();if(body==null)continue;bool selected=args.Length<2||args[1]=="all"||Array.IndexOf(args,"0x"+m.MetadataToken.ToString("X8"))>=0;
 if(selected)Console.WriteLine("METHOD 0x"+m.MetadataToken.ToString("X8")+" "+m.DeclaringType.FullName+"::"+m.ToString());byte[] il=body.GetILAsByteArray();int p=0;
 while(p<il.Length){int at=p;ushort v=il[p++];if(v==254)v=(ushort)(65024+il[p++]);var o=ops[v];int n=0;string value="";switch(o.OperandType){case OperandType.InlineNone:break;case OperandType.ShortInlineI:case OperandType.ShortInlineBrTarget:case OperandType.ShortInlineVar:n=1;value=il[p].ToString();break;case OperandType.InlineVar:n=2;value=BitConverter.ToUInt16(il,p).ToString();break;case OperandType.InlineI8:case OperandType.InlineR:n=8;value=BitConverter.ToInt64(il,p).ToString();break;case OperandType.InlineSwitch:n=4+4*BitConverter.ToInt32(il,p);break;default:n=4;int z=BitConverter.ToInt32(il,p);value=z.ToString();if(o.OperandType==OperandType.InlineString)value="\""+module.ResolveString(z)+"\"";else if(o.OperandType==OperandType.InlineMethod||o.OperandType==OperandType.InlineField||o.OperandType==OperandType.InlineType||o.OperandType==OperandType.InlineTok){try{var member=module.ResolveMember(z);value="0x"+z.ToString("X8")+" "+member.DeclaringType+"::"+member;}catch{value="0x"+z.ToString("X8");}if(o==OpCodes.Call||o==OpCodes.Callvirt){if(!counts.ContainsKey(z))counts[z]=0;counts[z]++;}}break;}p+=n;if(selected)Console.WriteLine(at.ToString("X4")+": "+o.Name+" "+value);}
 }
 foreach(var kv in counts){if(kv.Value<50)continue;try{Console.WriteLine("FREQUENT 0x"+kv.Key.ToString("X8")+" "+kv.Value+" "+module.ResolveMethod(kv.Key));}catch{}}
 return 0;}
}
