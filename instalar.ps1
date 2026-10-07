# Instala dependências e cria atalho na pasta Inicializar (abre na bandeja junto com o Windows).
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = (Get-Command pythonw).Source
pip install -q -r "$dir\requirements.txt"

$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Lembreme.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $pythonw
$s.Arguments = "`"$dir\lembreme.pyw`" --oculto"
$s.WorkingDirectory = $dir
$s.IconLocation = "$dir\assets\lembreme.ico"
$s.Description = "Lembreme"
$s.Save()
Write-Host "Atalho criado: $lnk"

Start-Process $pythonw -ArgumentList "`"$dir\lembreme.pyw`"" -WorkingDirectory $dir
