# Usage: pwsh scripts/make-source-zip.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Resolve-Path "$root\..")

$zip = "Excel_Report_Sorter-src.zip"
# Clean any previous artifact
Remove-Item -Force $zip -ErrorAction SilentlyContinue

# Build a file list excluding junk (works even without git)
$include = @('app.py','sorter.py','launch_gui.py','requirements.txt','README.md','copilot.md','tests')
$files = @()
foreach ($p in $include) {
  if (Test-Path $p) { $files += Get-Item $p -ErrorAction SilentlyContinue }
}
Compress-Archive -Path $files -DestinationPath $zip -Force
Write-Host "Wrote $zip"
