$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$nodeVersion = 'v24.22.2'
$archiveName = "node-$nodeVersion-win-x64.zip"
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$toolchainRoot = Join-Path $repositoryRoot '.runtime/toolchains'
New-Item -ItemType Directory -Path $toolchainRoot -Force | Out-Null
$archivePath = Join-Path $toolchainRoot $archiveName
$checksums = (Invoke-WebRequest -Uri "https://nodejs.org/dist/$nodeVersion/SHASUMS256.txt" -TimeoutSec 60).Content
$checksumLine = ($checksums -split "`n" | Where-Object { $_.Trim().EndsWith("  $archiveName") })
if (-not $checksumLine) { throw 'Official archive checksum was not found.' }
$expectedHash = ($checksumLine.Trim() -split '\s+')[0]
if (-not (Test-Path -LiteralPath $archivePath)) {
    Invoke-WebRequest -Uri "https://nodejs.org/dist/$nodeVersion/$archiveName" -OutFile $archivePath -TimeoutSec 120
}
$actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
if ($actualHash -ne $expectedHash) { throw 'Node archive SHA256 does not match official checksum.' }
$executable = Join-Path $toolchainRoot "node-$nodeVersion-win-x64/node.exe"
if (-not (Test-Path -LiteralPath $executable)) {
    Expand-Archive -LiteralPath $archivePath -DestinationPath $toolchainRoot
}
& $executable --version
Write-Output "Verified local Node archive SHA256: $actualHash"
Write-Output 'Global Node/PATH configuration was not changed. Use scripts/web.ps1.'
