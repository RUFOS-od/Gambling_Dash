# Usage: .\push_photos.ps1 -Vague 1
# Pushes new field photos for a given wave (1, 2, 3...).

param(
    [Parameter(Mandatory=$true)]
    [int]$Vague
)

$repoRoot = "C:\OPINION WAY PROJECT\PROJET 2026\Nos AO\AO Betclic"
$photoDir = "$repoRoot\dashboard_v2\assets\field_photos\Vague_$Vague"

if (-not (Test-Path $photoDir)) {
    Write-Host "Le dossier $photoDir n'existe pas." -ForegroundColor Red
    exit 1
}

$count = (Get-ChildItem $photoDir -File -Include *.jpg,*.jpeg,*.png,*.webp).Count
Write-Host "Photos trouvees dans Vague_$Vague : $count" -ForegroundColor Cyan

if ($count -eq 0) {
    Write-Host "Aucune photo. Depose-les d'abord dans $photoDir" -ForegroundColor Yellow
    exit 0
}

Set-Location $repoRoot
git add "dashboard_v2/assets/field_photos/Vague_$Vague/"
git commit -m "Add V$Vague field photos ($count photos)"
git push

Write-Host "Push termine. Streamlit Cloud redeploiera dans 2-3 min." -ForegroundColor Green
