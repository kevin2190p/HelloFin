<#
.SYNOPSIS
    Fakeout Multi-Cloud Dual-LLM Test Harness
.DESCRIPTION
    Sends a battery of scam/clean messages to the running backend and
    pretty-prints the AWS Bedrock vs Alibaba DashScope verdict so you
    can demonstrate multi-cloud cross-validation to the FINHACK judges.

.USAGE
    Make sure the backend is running on http://localhost:8000, then:
        .\test_multicloud.ps1
    Or against a different host:
        .\test_multicloud.ps1 -BaseUrl http://localhost:8000
#>

param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"

# Force UTF-8 so Mandarin payloads survive the round-trip
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding         = [System.Text.Encoding]::UTF8

$cases = @(
    @{
        Title    = "1. English authority-impersonation scam (expect AWS Bedrock to fire)"
        Expected = "HIGH RISK"
        Message  = "This is PDRM. Your account is under investigation for money laundering. Transfer to safe account now or arrest warrant will be issued. Do not hang up."
    },
    @{
        Title    = "2. Mandarin Macau-style scam (expect Alibaba Qwen to fire)"
        Expected = "HIGH RISK"
        Message  = "我是警察,你的银行账户涉及洗钱案件,请立刻把钱转到安全账户,不要告诉任何人,否则马上抓你"
    },
    @{
        Title    = "3. Bahasa Malaysia urgency scam (cross-cloud agreement test)"
        Expected = "HIGH RISK"
        Message  = "Ini Bank Negara. Akaun anda akan dibekukan. Sila berikan OTP sekarang untuk pengesahan, jangan beritahu sesiapa."
    },
    @{
        Title    = "4. Ambiguous family request (expect disagreement / escalation)"
        Expected = "MEDIUM"
        Message  = "Hi, this is your nephew. My phone is rosak, can you transfer RM2000 to this new account? Emergency, please don't tell mum."
    },
    @{
        Title    = "5. Clean legitimate message (expect SAFE)"
        Expected = "SAFE"
        Message  = "Hi mum, just confirming dinner at 7pm tonight at the usual restaurant. See you soon!"
    }
)

function Invoke-Scan {
    param([string]$Message)
    $body = @{ message = $Message } | ConvertTo-Json -Compress
    try {
        return Invoke-RestMethod `
            -Uri "$BaseUrl/risk/scan" `
            -Method POST `
            -ContentType "application/json; charset=utf-8" `
            -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    } catch {
        Write-Host "  REQUEST FAILED: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Fakeout Multi-Cloud Dual-LLM Verification" -ForegroundColor Cyan
Write-Host "  Target: $BaseUrl" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Health check first
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -TimeoutSec 5
    Write-Host "Backend health: OK" -ForegroundColor Green
} catch {
    Write-Host "Backend not reachable at $BaseUrl. Start it first." -ForegroundColor Red
    exit 1
}

$summary = @()

foreach ($case in $cases) {
    Write-Host ""
    Write-Host $case.Title -ForegroundColor Yellow
    Write-Host ("  Expected: {0}" -f $case.Expected) -ForegroundColor DarkGray
    Write-Host ("  Message : {0}" -f $case.Message) -ForegroundColor DarkGray

    $resp = Invoke-Scan -Message $case.Message
    if ($null -eq $resp) { continue }

    $score   = $resp.riskScore
    $status  = $resp.status
    $reasons = ($resp.reasons | Select-Object -First 6) -join ", "

    $color = "Green"
    if ($score -ge 70)      { $color = "Red" }
    elseif ($score -ge 40)  { $color = "Yellow" }

    Write-Host ("  Result  : Score={0}  Status={1}" -f $score, $status) -ForegroundColor $color
    if ($reasons) {
        Write-Host ("  Reasons : {0}" -f $reasons) -ForegroundColor Gray
    }

    $summary += [pscustomobject]@{
        Test     = $case.Title.Substring(0, [Math]::Min(40, $case.Title.Length))
        Score    = $score
        Status   = $status
        Expected = $case.Expected
    }
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
$summary | Format-Table -AutoSize

Write-Host ""
Write-Host "Look in the backend logs for these structured events to" -ForegroundColor DarkCyan
Write-Host "prove BOTH clouds are doing real work:" -ForegroundColor DarkCyan
Write-Host "  - bedrock_analysis_done    (AWS)"   -ForegroundColor DarkCyan
Write-Host "  - dashscope_analysis_done  (Alibaba)" -ForegroundColor DarkCyan
Write-Host "  - multicloud_consensus     (fusion)" -ForegroundColor DarkCyan
Write-Host "  - cloud_disagreement_escalation     (case 4 should trigger)" -ForegroundColor DarkCyan
Write-Host ""
