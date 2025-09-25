# Usage: pwsh scripts/make-release-zip.ps1
$ErrorActionPreference = 'Stop'
if (-not (Test-Path dist)) { throw "dist folder not found. Build the exe first." }
$exe = Get-ChildItem dist -Filter *.exe | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $exe) { throw "No exe found in dist." }
$zip = "Excel_Report_Sorter-${($exe.BaseName)}.zip"
Remove-Item -Force $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $exe.FullName -DestinationPath $zip -Force
Write-Host "Wrote $zip"
