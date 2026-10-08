# Gera o exe (se faltar) e cria atalho na pasta Inicializar (abre na bandeja junto com o Windows).
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = "$dir\Lembreme.exe"
if (-not (Test-Path $exe)) { & "$dir\build.ps1" }

$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Lembreme.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $exe
$s.Arguments = "--oculto"
$s.WorkingDirectory = $dir
$s.IconLocation = "$exe,0"
$s.Description = "Lembreme"
$s.Save()
Write-Host "Atalho criado: $lnk"

Start-Process $exe -WorkingDirectory $dir
