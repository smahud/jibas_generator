param()
$ErrorActionPreference = 'Stop'
$toolRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$matrixRoot = Join-Path $toolRoot 'bukti\server_matrix'
$expectedHash = '8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364'
$expectedMvid = '9e7e3122-c165-4ca3-3e9c-234edb96bf24'
$summary = Get-Content -LiteralPath (Join-Path $matrixRoot 'matrix_summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$records = @()
$runtimeTotal = 0
foreach ($scenario in $summary.scenarios) {
    $path = Join-Path $matrixRoot ($scenario.name + '.json')
    $record = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    $errors = @()
    if ($record.artifact_sha256 -ne $expectedHash) { $errors += 'artifact_identity' }
    if ($record.mvid -ne $expectedMvid) { $errors += 'mvid_identity' }
    if ($record.scenario -ne $scenario.name) { $errors += 'scenario_name' }
    if ($record.candidate_import -cne $scenario.importer) { $errors += 'summary_importer' }
    if (-not $record.assertions_passed -or -not $scenario.passed) { $errors += 'recorded_failure' }
    if ($record.candidate_import -is [bool] -and $record.candidate_import) {
        if (-not $record.cache_written) { $errors += 'accepted_without_cache' }
        $caseNames = @($record.runtime_cases | ForEach-Object { $_.name })
        $expectationNames = @($record.runtime_expectations.PSObject.Properties.Name)
        if (@(Compare-Object $caseNames $expectationNames).Count -ne 0) { $errors += 'runtime_case_names' }
        foreach ($case in $record.runtime_cases) {
            $runtimeTotal++
            if ($case.accepted -cne $record.runtime_expectations.($case.name)) { $errors += ('runtime_' + $case.name) }
        }
        if ($scenario.name -like '*_system_mismatch') {
            $observed = @($record.runtime_cases | Where-Object name -eq 'actual_injected_environment')
            if ($observed.Count -ne 1 -or $observed[0].accepted) { $errors += 'system_mismatch_runtime' }
        }
    } else {
        if ($record.before_sequence -cne $record.after_sequence) { $errors += 'rejection_changed_sequence' }
        if ($record.before_client -cne $record.after_client) { $errors += 'rejection_changed_client' }
        if ($record.expected_error_substring -and -not ([string]$record.candidate_import).Contains($record.expected_error_substring)) { $errors += 'rejection_message' }
    }
    $records += [ordered]@{ scenario=$scenario.name; consistent=($errors.Count -eq 0); errors=$errors; evidence_sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$idPath = Join-Path $toolRoot 'bukti\id_audit\isolated_db_matrix.json'
$ids = Get-Content -LiteralPath $idPath -Raw -Encoding UTF8 | ConvertFrom-Json
$dbChecks = @($ids.cases | ForEach-Object { [ordered]@{ fixture=$_.fixture_id; consistent=($_.original.original_AC3 -ceq $_.python -and $_.python -ceq $_.fixture_id.ToUpperInvariant()) } })
$hashChecks = @($ids.system_hash_vectors | ForEach-Object {
    $md5 = [System.Security.Cryptography.MD5]::Create()
    try { $digest = [BitConverter]::ToString($md5.ComputeHash([System.Text.Encoding]::ASCII.GetBytes($_.input))).Replace('-','').ToLowerInvariant() } finally { $md5.Dispose() }
    $id = -join @(5,17,30,24,3 | ForEach-Object { $digest[$_] })
    [ordered]@{ consistent=($digest -ceq $_.digest -and $id.ToUpperInvariant() -ceq $_.system_id) }
})
$beforeJson = ConvertTo-Json -InputObject $ids.live_routines_before -Compress
$afterJson = ConvertTo-Json -InputObject $ids.live_routines_after -Compress
$installed = 'C:\Program Files\YIM\JIBAS Face Server 16.5\FaceServer.exe'
$result = [pscustomobject][ordered]@{
    audit_kind='Read-only consistency audit of historical artifacts; no new target execution or DB access';
    current_binary_matches=((Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $expectedHash);
    scenario_count=$records.Count; runtime_case_count=$runtimeTotal;
    reported_total_matches=($summary.total -eq $records.Count);
    all_scenarios_consistent=(@($records | Where-Object { -not $_.consistent }).Count -eq 0);
    scenarios=$records; db_fixture_checks=$dbChecks; hardware_digest_checks=$hashChecks;
    all_id_checks_consistent=(@($dbChecks + $hashChecks | Where-Object { -not $_.consistent }).Count -eq 0);
    stored_live_routine_snapshots_equal=($beforeJson -ceq $afterJson);
    id_evidence_sha256=(Get-FileHash -LiteralPath $idPath -Algorithm SHA256).Hash.ToLowerInvariant();
    boundary='Internal consistency does not authenticate historical logs or prove official issuance, GUI activation, network behavior, or alternate physical hardware.'
}
$output = Join-Path $PSScriptRoot 'saved_evidence_audit.json'
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $output -Encoding UTF8
$result | Select-Object audit_kind,current_binary_matches,scenario_count,runtime_case_count,all_scenarios_consistent,all_id_checks_consistent,stored_live_routine_snapshots_equal | ConvertTo-Json
if (-not $result.all_scenarios_consistent -or -not $result.current_binary_matches -or -not $result.reported_total_matches -or -not $result.all_id_checks_consistent -or -not $result.stored_live_routine_snapshots_equal) { exit 1 }
