$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$localNodeDirectory = Join-Path $repositoryRoot '.runtime/toolchains/node-v24.22.2-win-x64'
if (-not (Test-Path -LiteralPath (Join-Path $localNodeDirectory 'node.exe'))) {
    throw 'Run ./scripts/setup_node.ps1 once to install the verified repository-local Node24 toolchain.'
}
$previousPath = $env:Path
try {
    $env:Path = "$localNodeDirectory;$previousPath"
    & pnpm @args
    $result = $LASTEXITCODE
} finally {
    $env:Path = $previousPath
}
exit $result
