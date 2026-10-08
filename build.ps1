# Gera Lembreme.exe na pasta do projeto.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $dir
pip install -q -r requirements.txt pyinstaller
pyinstaller --noconfirm --onefile --windowed --name Lembreme `
  --icon assets\lembreme.ico --add-data "assets;assets" `
  --hidden-import pystray._win32 --hidden-import babel.numbers --collect-data babel `
  lembreme.pyw
Copy-Item dist\Lembreme.exe .\Lembreme.exe -Force
Pop-Location
