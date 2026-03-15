$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $root "desktop\src"
$entryPoint = Join-Path $sourceRoot "pressure_console\__main__.py"
$distRoot = Join-Path $root "dist"
$buildRoot = Join-Path $root "build"
$specRoot = Join-Path $root ".build\pyinstaller"
$zipPath = Join-Path $distRoot "PressureControlConsole-windows.zip"

New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $specRoot | Out-Null

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name PressureControlConsole `
  --paths $sourceRoot `
  --collect-all pyqtgraph `
  --add-data "$root\firmware;firmware" `
  --add-data "$root\README.md;." `
  --distpath $distRoot `
  --workpath $buildRoot `
  --specpath $specRoot `
  $entryPoint

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Compress-Archive -Path (Join-Path $distRoot "PressureControlConsole") -DestinationPath $zipPath
Write-Output "Created $zipPath"

