using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
public static class CbeCapacityProbe {
 public static int Main(string[] args) {
  try{
   string dir=@"C:\Program Files\YIM\JIBAS CBE Server 26.5";
   AppDomain.CurrentDomain.AssemblyResolve+=delegate(object s,ResolveEventArgs e){string p=Path.Combine(dir,new AssemblyName(e.Name).Name+".dll");return File.Exists(p)?Assembly.LoadFrom(p):null;};
   Module m=Assembly.LoadFile(Path.Combine(dir,"CbeServer.exe")).ManifestModule;
   m.ResolveField(0x040005D2).SetValue(null,Path.Combine(Path.GetTempPath(),"codex-cbe-capacity"));
   m.ResolveMethod(0x060005B7).Invoke(null,null);m.ResolveMethod(0x060005B9).Invoke(null,null);
   int[] values={-2147483648,-1,0,1,2,10,19,20,21,25,49,50,51,99,100,101,199,200,201,249,250,251,499,500,501,999,1000,1001,10000,2147483647};
   var rows=new List<Dictionary<string,object>>();
   foreach(int value in values){var row=new Dictionary<string,object>{{"input",value}};try{row["output"]=m.ResolveMethod(0x060005BF).Invoke(null,new object[]{value});}catch(Exception e){while(e.InnerException!=null)e=e.InnerException;row["exception"]=e.GetType().Name+": "+e.Message;}rows.Add(row);}
   Func<int,int> compute=delegate(int value){return (int)m.ResolveMethod(0x060005BF).Invoke(null,new object[]{value});};
   var boundaries=new List<Dictionary<string,object>>();
   int start=0, output=compute(0), final=compute(Int32.MaxValue);
   while(output!=final){int lo=start+1,hi=Int32.MaxValue;while(lo<hi){int mid=lo+(int)(((long)hi-lo)/2);if(compute(mid)==output)lo=mid+1;else hi=mid;}int next=lo;boundaries.Add(new Dictionary<string,object>{{"start",start},{"end",next-1},{"output",output},{"next_boundary",next},{"output_at_next_boundary",compute(next)}});start=next;output=compute(start);}
   boundaries.Add(new Dictionary<string,object>{{"start",start},{"end",Int32.MaxValue},{"output",output}});
   Console.WriteLine(new JavaScriptSerializer().Serialize(new Dictionary<string,object>{{"method","0x060005BF"},{"mvid",m.ModuleVersionId.ToString()},{"samples",rows},{"candidate_segments_monotone_boundary_search",boundaries},{"limitations","Segment search assumes monotonicity; exact sampled outputs and transition edges are original-method observations."},{"scope","original capacity transform only; no target Main or DB/network setup"}}));return 0;
  }catch(Exception e){while(e.InnerException!=null)e=e.InnerException;Console.Error.WriteLine(e);return 1;}
 }
}
