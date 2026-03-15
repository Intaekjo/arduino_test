$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "desktop\src"
python -m pressure_console

