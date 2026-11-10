
$asmPath = 'C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10\FaceFgrClient.exe'
[System.AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve({
 param($sender, $eventArgs)
 $localAssemblyName = ([Reflection.AssemblyName]$eventArgs.Name).Name + '.dll'
 $localAssemblyPath = Join-Path (Split-Path $asmPath) $localAssemblyName
 if (Test-Path -LiteralPath $localAssemblyPath) { return [Reflection.Assembly]::ReflectionOnlyLoadFrom($localAssemblyPath) }
 return [Reflection.Assembly]::ReflectionOnlyLoad($eventArgs.Name)
})
$asmInspect = [Reflection.Assembly]::ReflectionOnlyLoadFrom($asmPath)
$modInspect = $asmInspect.ManifestModule
$opCodes = @{}
[Reflection.Emit.OpCodes].GetFields([Reflection.BindingFlags]'Public,Static') | ForEach-Object {
 $opValue = $_.GetValue($null)
 $opCodes[[int]$opValue.Value -band 65535] = $opValue
}
function Get-ILInstructions($methodInspect) {
 $bodyInspect = $methodInspect.GetMethodBody()
 if ($null -eq $bodyInspect) { return }
 $ilBytes = $bodyInspect.GetILAsByteArray()
 $ilPosition = 0
 while ($ilPosition -lt $ilBytes.Length) {
  $ilOffset = $ilPosition
  $opCodeValue = [int]$ilBytes[$ilPosition++]
  if ($opCodeValue -eq 254) { $opCodeValue = 65024 + [int]$ilBytes[$ilPosition++] }
  $opInspect = $opCodes[$opCodeValue]
  if ($null -eq $opInspect) { throw "Unknown opcode $opCodeValue" }
  $operandInspect = $null
  $operandToken = $null
  switch ($opInspect.OperandType.ToString()) {
   InlineNone {}
   ShortInlineI { $operandInspect = [int][sbyte]::Parse($ilBytes[$ilPosition].ToString('X2'),[Globalization.NumberStyles]::HexNumber); $ilPosition++ }
   InlineI { $operandInspect = [BitConverter]::ToInt32($ilBytes,$ilPosition); $ilPosition += 4 }
   InlineI8 { $operandInspect = [BitConverter]::ToInt64($ilBytes,$ilPosition); $ilPosition += 8 }
   ShortInlineR { $operandInspect = [BitConverter]::ToSingle($ilBytes,$ilPosition); $ilPosition += 4 }
   InlineR { $operandInspect = [BitConverter]::ToDouble($ilBytes,$ilPosition); $ilPosition += 8 }
   ShortInlineVar { $operandInspect = [int]$ilBytes[$ilPosition]; $ilPosition++ }
   InlineVar { $operandInspect = [BitConverter]::ToUInt16($ilBytes,$ilPosition); $ilPosition += 2 }
   ShortInlineBrTarget { $operandInspect = $ilPosition + 1 + [int][sbyte]::Parse($ilBytes[$ilPosition].ToString('X2'),[Globalization.NumberStyles]::HexNumber); $ilPosition++ }
   InlineBrTarget { $operandInspect = $ilPosition + 4 + [BitConverter]::ToInt32($ilBytes,$ilPosition); $ilPosition += 4 }
   InlineSwitch { $switchCount = [BitConverter]::ToInt32($ilBytes,$ilPosition); $ilPosition += 4; $switchBase = $ilPosition + 4 * $switchCount; $operandInspect = @(for ($switchIndex=0;$switchIndex -lt $switchCount;$switchIndex++) { $switchBase + [BitConverter]::ToInt32($ilBytes,$ilPosition); $ilPosition += 4 }) -join ',' }
   default {
    $operandToken = [BitConverter]::ToInt32($ilBytes,$ilPosition)
    $ilPosition += 4
    try {
     if ($opInspect.OperandType.ToString() -eq 'InlineString') { $operandInspect = '"' + $modInspect.ResolveString($operandToken) + '"' }
     elseif ($opInspect.OperandType.ToString() -eq 'InlineSig') { $operandInspect = 'signature' }
     else { $memberInspect = $modInspect.ResolveMember($operandToken); $operandInspect = $memberInspect.DeclaringType.FullName + '::' + $memberInspect.ToString() }
    } catch { $operandInspect = 'unresolved' }
   }
  }
  [pscustomobject]@{Offset=$ilOffset; Op=$opInspect.Name; Operand=$operandInspect; Token=$operandToken}
 }
}
function Show-IL($methodToken) {
 $methodInspect = $modInspect.ResolveMethod($methodToken)
 'METHOD 0x{0:X8} {1}::{2}' -f $methodToken,$methodInspect.DeclaringType.FullName,$methodInspect.ToString()
 Get-ILInstructions $methodInspect | ForEach-Object { '{0:X4}: {1,-12} {2} {3}' -f $_.Offset,$_.Op,$_.Operand,$(if ($null -ne $_.Token) { '0x{0:X8}' -f $_.Token }) }
}


