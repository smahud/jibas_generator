. "$PSScriptRoot\cbe_il.ps1"
foreach($targetType in $asmInspect.GetTypes()){
 foreach($targetMethod in $targetType.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,Instance,DeclaredOnly')){
  try {
   $instructions=@(Get-ILInstructions $targetMethod)
   $hits=@($instructions | Where-Object { $_.Operand -match 'System.Data.DataTable|System.Data.DataColumn|ReadXml|WriteXml|AES|Rijndael|MD5|PhysicalMedia' })
   foreach($hit in $hits){ '{0:X8} {1}::{2} IL{3:X4} {4}' -f $targetMethod.MetadataToken,$targetType.FullName,$targetMethod.ToString(),$hit.Offset,$hit.Operand }
  }catch{}
 }
}
