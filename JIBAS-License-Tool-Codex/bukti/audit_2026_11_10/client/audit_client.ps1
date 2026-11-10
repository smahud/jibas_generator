$ErrorActionPreference = 'Stop'
$auditRoot = $PSScriptRoot
$packageRoot = [IO.Path]::GetFullPath((Join-Path $auditRoot '..\..\..'))
$oldEvidence = Join-Path $packageRoot 'bukti\client_import'
$installed = 'C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10\FaceFgrClient.exe'
$copied = 'C:\YIM\JIBAS Generator\JIBAS Face & Fingerprint Client 16.10\FaceFgrClient.exe'
$source = Join-Path $oldEvidence 'ClientImportVerify.cs'
$compiled = Join-Path $auditRoot 'ClientImportVerify.exe'
$hashes = @{}
foreach ($path in @($installed, $copied, $source, (Join-Path $oldEvidence 'matrix_results.json'), (Join-Path $oldEvidence 'run_client_matrix.py'))) {
    $hashes[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
if ($hashes[$installed] -ne $hashes[$copied]) { throw 'Target copy differs from installed executable' }
& 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /r:System.Web.Extensions.dll "/out:$compiled" $source
if ($LASTEXITCODE -ne 0) { throw 'Harness compilation failed' }
$inputPath = Join-Path $oldEvidence 'inputs\missing_header.lic'
$hashes[$inputPath] = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$hashes[$compiled] = (Get-FileHash -LiteralPath $compiled -Algorithm SHA256).Hash.ToLowerInvariant()
$sandbox = Join-Path $auditRoot ('negative_header_' + [guid]::NewGuid().ToString('N'))
$raw = & $compiled $sandbox V4YNE $inputPath
if ($LASTEXITCODE -ne 0) { throw 'Harness failed' }
$replay = $raw | ConvertFrom-Json
$attempt = $replay.attempts[0]
if ($attempt.accepted -or $attempt.cache_exists -or $attempt.exception -ne 'System.Exception: File terpilih bukan lisensi JIBAS Presensi Wajah') {
    throw 'Unexpected negative-header result'
}
$matrix = Get-Content -LiteralPath (Join-Path $oldEvidence 'matrix_results.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$negativeBytes = [IO.File]::ReadAllText($inputPath)
$checks = @{}
foreach ($name in @('v4yne_new', 'wrong_header', 'lowercase_header')) {
    $fullText = [IO.File]::ReadAllText((Join-Path $oldEvidence ('inputs\' + $name + '.lic')))
    $checks[$name + '_payload_identical_to_headerless'] = ($fullText.Substring($fullText.IndexOf("`n") + 1) -ceq $negativeBytes)
}
$after = (Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash.ToLowerInvariant()
$result = [ordered]@{
    recorded_at_utc = [DateTime]::UtcNow.ToString('o')
    scope = 'Fresh negative importer replay; existing positive matrix reviewed, not rerun'
    hashes = $hashes
    current_installed_binary_unchanged = ($after -eq $hashes[$installed])
    historical_scenario_count = $matrix.Count
    historical_attempt_count = @($matrix | ForEach-Object { $_.attempts }).Count
    preserved_payload_checks = $checks
    negative_replay = $replay
}
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $auditRoot 'verification.json') -Encoding UTF8
[pscustomobject]$result | Select-Object recorded_at_utc,scope,current_installed_binary_unchanged,historical_scenario_count,historical_attempt_count,preserved_payload_checks | ConvertTo-Json -Depth 5
