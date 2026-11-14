$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
# Use a clean venv with pip wheels. Conda's MKL runtime can exceed the portable size budget.
python -m PyInstaller --noconfirm SloganGenerator.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
Copy-Item -LiteralPath README.md, README.zh-CN.md -Destination dist/SloganGenerator
Copy-Item -LiteralPath docs -Destination dist/SloganGenerator -Recurse -Force
$portableBytes = (Get-ChildItem dist/SloganGenerator -Recurse -File | Measure-Object Length -Sum).Sum
if ($portableBytes -ge 400000000) { throw "Portable folder exceeds 400 MB: $portableBytes bytes" }
Compress-Archive -LiteralPath dist/SloganGenerator -DestinationPath dist/SloganGenerator-v1.0.1-windows-x64.zip -Force
Write-Host "Built v1.0.1; extracted folder: $portableBytes bytes"
