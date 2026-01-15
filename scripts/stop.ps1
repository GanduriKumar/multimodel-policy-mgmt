$ErrorActionPreference = 'Continue'

# Kill anything on the dev ports (simple and small like your sample)
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue | Stop-Process -Force }
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue | Stop-Process -Force }

# Also close the PowerShell windows started by start.ps1 (by their window titles)
$psWindows = @()
$psWindows += Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -match 'Policy Backend|Policy Frontend' }
$psWindows += Get-Process -Name pwsh -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -match 'Policy Backend|Policy Frontend' }
if ($psWindows) {
	$psWindows | Stop-Process -Force -ErrorAction SilentlyContinue
	Write-Host "Closed backend/frontend PowerShell windows"
} else {
	Write-Host "No backend/frontend PowerShell windows found"
}

Write-Host "Stopped services on ports 8000 and 5173"