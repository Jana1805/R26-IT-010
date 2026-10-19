<#
.SYNOPSIS
  Viva-morning preflight for the XAI component (madushani_xai).

.DESCRIPTION
  1. Starts the whole system with start-all.py in a new window, unless the
     XAI backend is already answering (then it reuses the running system).
  2. Waits until the servers answer.
  3. Checks every XAI endpoint, every v2 figure, the three XAI pages, Swagger,
     the BI dashboard and API, and the BI -> XAI "LIME" deep link for 2025-01-25.
  4. Prints PASS / FAIL per check and a summary. Exit code = number of FAILs.

  Read-only: it only sends GET requests.

.PARAMETER NoStart
  Never start the system; only check what is already running.

.PARAMETER StopAfter
  Stop the system this script started (the start-all.py window) after checking.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File madushani_xai\viva\preflight.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File madushani_xai\viva\preflight.ps1 -NoStart
#>
param(
    [switch]$NoStart,
    [switch]$StopAfter,
    [int]$StartupTimeoutSec = 120
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$XaiApi = 'http://127.0.0.1:8000'
$XaiUi = 'http://localhost:5173'
$BiApi = 'http://127.0.0.1:8001'
$BiUi = 'http://localhost:3000'
$Date = '2025-01-25'

$results = New-Object System.Collections.Generic.List[object]

function Get-Http([string]$Url) {
    # Returns @{ Status; ContentType; Content } without throwing on 4xx/5xx.
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 60
        return @{ Status = [int]$r.StatusCode; ContentType = [string]$r.Headers['Content-Type']; Content = $r.Content }
    } catch [System.Net.WebException] {
        $resp = $_.Exception.Response
        if ($resp) { return @{ Status = [int]$resp.StatusCode; ContentType = ''; Content = '' } }
        return @{ Status = 0; ContentType = ''; Content = $_.Exception.Message }
    }
}

function Add-Check([string]$Name, [scriptblock]$Test) {
    try {
        $detail = & $Test
        $results.Add([pscustomobject]@{ Result = 'PASS'; Check = $Name; Detail = [string]$detail })
    } catch {
        $results.Add([pscustomobject]@{ Result = 'FAIL'; Check = $Name; Detail = $_.Exception.Message })
    }
}

function Assert-Status($resp, [int]$Expected = 200) {
    if ($resp.Status -ne $Expected) { throw "HTTP $($resp.Status) (expected $Expected)" }
}

function Wait-Url([string]$Url, [int]$TimeoutSec) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Get-Http $Url).Status -eq 200) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

# ---- 1. Start the system if needed --------------------------------------------
$launcher = $null
$alreadyUp = (Get-Http "$XaiApi/").Status -eq 200
if ($alreadyUp) {
    Write-Host "System already running - reusing it (not starting a second copy)." -ForegroundColor Cyan
} elseif ($NoStart) {
    Write-Host "-NoStart given and the XAI backend is not answering; checks will fail." -ForegroundColor Yellow
} else {
    Write-Host "Starting the system: python start-all.py (new window) ..." -ForegroundColor Cyan
    $launcher = Start-Process -FilePath 'python' -ArgumentList 'start-all.py' -WorkingDirectory $Root -PassThru
}

Write-Host "Waiting for servers (up to $StartupTimeoutSec s) ..."
foreach ($u in @("$XaiApi/", $XaiUi, "$BiApi/api/dashboard-summary", $BiUi)) {
    if (-not (Wait-Url $u $StartupTimeoutSec)) { Write-Host "  not answering: $u" -ForegroundColor Yellow }
}

# ---- 2. XAI backend -----------------------------------------------------------
Add-Check 'XAI API root (8000)' { $r = Get-Http "$XaiApi/"; Assert-Status $r; 'running' }

Add-Check 'GET /api/temporal-drift' {
    $r = Get-Http "$XaiApi/api/temporal-drift"; Assert-Status $r
    $j = $r.Content | ConvertFrom-Json
    if (-not $j.model_comparison) { throw 'model_comparison missing' }
    "years $($j.years -join ',')"
}

Add-Check 'GET /api/anomaly-diagnosis' {
    $r = Get-Http "$XaiApi/api/anomaly-diagnosis"; Assert-Status $r
    $j = $r.Content | ConvertFrom-Json
    if ($j.instances.Count -ne 15) { throw "expected 15 instances, got $($j.instances.Count)" }
    $peak = $j.instances | Where-Object { $_.demand_level -eq 'peak' } | Select-Object -First 1
    $t = ($peak.contributions | Where-Object { $_.feature -eq 'Temperature' }).weight
    if ($t -le 0) { throw "peak Temperature weight is $t (sign bug back?)" }
    "15 instances; peak Temperature weight +$t"
}

Add-Check "GET /api/explain-date?date=$Date (live LIME)" {
    $a = Get-Http "$XaiApi/api/explain-date?date=$Date"; Assert-Status $a
    $b = Get-Http "$XaiApi/api/explain-date?date=$Date"
    $ja = $a.Content | ConvertFrom-Json
    $t = $ja.contributions | Where-Object { $_.feature -eq 'Temperature' }
    if ($t.weight -le 0) { throw "Temperature weight $($t.weight) should be positive for a peak day" }
    if ($a.Content -ne $b.Content) { throw 'two calls gave different answers (randomness back?)' }
    "$($t.rule): +$($t.weight) kW, R2 $($ja.lime_r2), deterministic"
}

Add-Check 'GET /api/explain-date (future date -> 404)' {
    $r = Get-Http "$XaiApi/api/explain-date?date=2026-10-20"; Assert-Status $r 404; '404 as expected'
}

foreach ($ep in @('model-comparison', 'xai-comparison', 'temporal-drift')) {
    Add-Check "GET /api/v2/$ep" {
        $r = Get-Http "$XaiApi/api/v2/$ep"; Assert-Status $r
        $null = $r.Content | ConvertFrom-Json
        "$([math]::Round($r.Content.Length / 1KB)) KB JSON"
    }.GetNewClosure()
}

Add-Check 'v2 ground truth: SHAP r vs true effect' {
    $j = (Get-Http "$XaiApi/api/v2/xai-comparison").Content | ConvertFrom-Json
    $rv = [double]$j.ground_truth.shap_temperature_vs_truth_pearson_r
    if ($rv -lt 0.999) { throw "r = $rv" }
    "r = $([math]::Round($rv, 5))"
}

$figures = @('model_comparison_rmse_mape', 'shap_beeswarm', 'shap_bar', 'shap_dependence_temperature',
             'lime_example_peak', 'lime_example_low', 'lime_stability_box', 'shap_vs_lime_table', 'temporal_drift_v2')
foreach ($f in $figures) {
    Add-Check "figure $f.png" {
        $r = Get-Http "$XaiApi/api/figures/$f.png"; Assert-Status $r
        if ($r.ContentType -notlike 'image/png*') { throw "content-type $($r.ContentType)" }
        'image/png'
    }.GetNewClosure()
}

Add-Check 'Swagger /docs' { $r = Get-Http "$XaiApi/docs"; Assert-Status $r; 'reachable' }

# ---- 3. XAI frontend (Vite, proxies /api to 8000) -------------------------------
foreach ($p in @('/temporal-drift', '/anomaly-diagnosis', '/model-xai-comparison')) {
    Add-Check "XAI page $p" { $r = Get-Http "$XaiUi$p"; Assert-Status $r; 'served' }.GetNewClosure()
}
Add-Check 'XAI proxy /api via 5173' {
    $r = Get-Http "$XaiUi/api/v2/xai-comparison"; Assert-Status $r; 'proxy OK'
}

# ---- 4. Behaviour Intelligence + deep link ------------------------------------
Add-Check 'BI dashboard page (3000)' { $r = Get-Http $BiUi; Assert-Status $r; 'served' }

Add-Check "BI API lists $Date as an abnormal day" {
    $r = Get-Http "$BiApi/api/dashboard-summary"; Assert-Status $r
    $j = $r.Content | ConvertFrom-Json
    $row = $j.data.recent_abnormal_days | Where-Object { $_.date -eq $Date }
    if (-not $row) { throw "$Date not in recent_abnormal_days" }
    "peak $($row.peak_demand) kW, risk $($row.behavior_risk_level)"
}

Add-Check 'BI LIME button targets the XAI page' {
    $src = Get-Content -Raw (Join-Path $Root 'behaviour-intelligence\frontend\src\App.jsx')
    if ($src -notmatch "MADHUSHANI_LIME_URL = 'http://localhost:5173/anomaly-diagnosis'") { throw 'LIME URL constant changed' }
    if ($src -notmatch 'source=bi&date=') { throw 'source=bi&date= link missing' }
    "opens $XaiUi/anomaly-diagnosis?source=bi&date=$Date"
}

Add-Check "Deep link page ?source=bi&date=$Date" {
    $r = Get-Http "$XaiUi/anomaly-diagnosis?source=bi&date=$Date"; Assert-Status $r; 'served'
}

# ---- 5. Other components (informational) -------------------------------------
foreach ($pair in @(@('forecast backend (8002)', 'http://127.0.0.1:8002/'), @('nn backend (8003)', 'http://127.0.0.1:8003/'))) {
    Add-Check $pair[0] { $r = Get-Http $pair[1]; if ($r.Status -eq 0) { throw 'not answering' }; "HTTP $($r.Status)" }.GetNewClosure()
}

# ---- Report ---------------------------------------------------------------------
Write-Host ''
foreach ($res in $results) {
    $color = if ($res.Result -eq 'PASS') { 'Green' } else { 'Red' }
    Write-Host ('[{0}] ' -f $res.Result) -ForegroundColor $color -NoNewline
    Write-Host ('{0,-48} {1}' -f $res.Check, $res.Detail)
}
$fails = @($results | Where-Object { $_.Result -eq 'FAIL' }).Count
Write-Host ''
if ($fails -eq 0) {
    Write-Host "ALL $($results.Count) CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host "$fails of $($results.Count) CHECKS FAILED - use viva\screenshots\ as backup" -ForegroundColor Red
}

if ($StopAfter -and $launcher) {
    Write-Host 'Stopping the system started by this script ...'
    & taskkill /F /T /PID $launcher.Id | Out-Null
} elseif ($launcher) {
    Write-Host "System left running. Stop it with Ctrl+C in the start-all.py window."
}
exit $fails
