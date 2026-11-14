$ErrorActionPreference = 'Stop'
$lavaRoot = $PSScriptRoot
if (Test-Path -LiteralPath "$lavaRoot\.venv\Scripts\python.exe") {
    & "$lavaRoot\.venv\Scripts\python.exe" "$lavaRoot\start.py"
} elseif (Test-Path -LiteralPath "$lavaRoot\.venv-linux\bin\python") {
    $lavaLinuxRoot = '/mnt/' + $lavaRoot.Substring(0,1).ToLower() + $lavaRoot.Substring(2).Replace('\','/')
    & wsl.exe --cd $lavaLinuxRoot -e .venv-linux/bin/python start.py
} else {
    Write-Error 'Create the isolated environment first using the README setup steps.'
}
