# Usage: .\push_data.ps1 [-Message "ton message custom"]
# Pushes any pending changes (data + code) to GitHub -> triggers Streamlit Cloud redeploy.

param(
    [string]$Message = ""
)

$repoRoot = "C:\OPINION WAY PROJECT\PROJET 2026\Nos AO\AO Betclic"
Set-Location $repoRoot

# Show what will be pushed
Write-Host "`n=== Fichiers a pusher ===" -ForegroundColor Cyan
git status --short

# If no changes, exit
$changes = git status --short
if (-not $changes) {
    Write-Host "`nRien a pusher, working tree clean." -ForegroundColor Yellow
    exit 0
}

# Build a smart commit message if none provided
if (-not $Message) {
    $dataFiles = git diff --name-only HEAD | Select-String -Pattern "Bases_Betclic|\.xlsx$"
    if ($dataFiles) {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
        $Message = "Update data ($stamp)"
    } else {
        $Message = "Update " + (Get-Date -Format "yyyy-MM-dd HH:mm")
    }
}

Write-Host "`nMessage de commit : $Message" -ForegroundColor Cyan
Write-Host "Confirmer ? (Y/N par defaut Y)" -ForegroundColor Yellow
$confirm = Read-Host
if ($confirm -and $confirm.ToUpper() -ne "Y") {
    Write-Host "Annule." -ForegroundColor Red
    exit 0
}

# Stage, commit, push
git add -A
git commit -m $Message
$pushResult = git push origin main 2>&1
Write-Host $pushResult

Write-Host "`nPush termine. Streamlit Cloud redeploiera dans 2-3 min." -ForegroundColor Green
Write-Host "URL : https://betclic-brand-pulse.streamlit.app" -ForegroundColor Green
