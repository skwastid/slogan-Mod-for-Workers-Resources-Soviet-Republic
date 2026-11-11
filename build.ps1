$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m PyInstaller --noconfirm SloganGenerator.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
Copy-Item -LiteralPath README.md, README.en.md, THIRD_PARTY_NOTICES.md -Destination dist/SloganGenerator
Compress-Archive -LiteralPath dist/SloganGenerator -DestinationPath dist/SloganGenerator-v0.3-windows-x64.zip -Force
Write-Host 'Built dist/SloganGenerator-v0.3-windows-x64.zip'
