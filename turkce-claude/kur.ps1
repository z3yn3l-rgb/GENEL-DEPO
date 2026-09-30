# Claude Code'u Türkçe konuşacak şekilde ayarlar (Windows PowerShell).
# Kullanım: .\kur.ps1            -> Türkçe'yi açar
#           .\kur.ps1 kaldir     -> Türkçe ayarını kaldırır
param([string]$Islem = "kur")

$dizin = Join-Path $env:USERPROFILE ".claude"
$dosya = Join-Path $dizin "settings.json"
New-Item -ItemType Directory -Force -Path $dizin | Out-Null
if (-not (Test-Path $dosya)) { Set-Content -Path $dosya -Value "{}" -Encoding UTF8 }

Copy-Item $dosya "$dosya.yedek" -Force
$ayar = Get-Content $dosya -Raw -Encoding UTF8 | ConvertFrom-Json

if ($Islem -eq "kaldir") {
    $ayar.PSObject.Properties.Remove("language")
    Write-Host "Türkçe ayarı kaldırıldı."
} else {
    $ayar | Add-Member -NotePropertyName language -NotePropertyValue "turkish" -Force
    Write-Host "Türkçe ayarı eklendi."
}

$ayar | ConvertTo-Json -Depth 20 | Set-Content -Path $dosya -Encoding UTF8
Write-Host "Ayar dosyası: $dosya (yedek: settings.json.yedek)"
Write-Host "Claude Code'u yeniden başlatın."
