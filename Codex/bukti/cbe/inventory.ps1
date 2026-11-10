. "$PSScriptRoot\cbe_il.ps1"
foreach($targetType in $asmInspect.GetTypes()){
 foreach($targetMethod in $targetType.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,Instance,DeclaredOnly')){
  '{0:X8} {1}::{2}' -f $targetMethod.MetadataToken,$targetType.FullName,$targetMethod.ToString()
 }
}
