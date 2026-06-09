# Desktop shortcut with Oxco icon (ASCII only - safe for Windows PowerShell encoding).
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ico = Join-Path $root "assets\oxco_icon.ico"
if (-not (Test-Path $ico)) {
    Push-Location $root
    try {
        $embedded = python -c "from oxco_icon_embed import materialize_icon_ico; print(materialize_icon_ico())" 2>$null
        if ($embedded -and (Test-Path $embedded)) {
            $ico = $embedded
        }
    } finally {
        Pop-Location
    }
}

$shortcutArgs = $null
$exePath = Join-Path $root "dist\Oxco\Oxco.exe"
if (Test-Path $exePath) {
    $target = $exePath
} elseif (Get-Command pythonw -ErrorAction SilentlyContinue) {
    $target = (Get-Command pythonw).Source
    $shortcutArgs = "`"$root\oxco_gui.py`""
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $target = (Get-Command python).Source
    $shortcutArgs = "`"$root\oxco_gui.py`""
} else {
    Write-Host "Python nicht gefunden."
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "Oxco.lnk"
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($lnk)
$sc.TargetPath = $target
if ($shortcutArgs) {
    $sc.Arguments = $shortcutArgs
}
$sc.WorkingDirectory = $root
if (Test-Path $ico) {
    $sc.IconLocation = "$ico,0"
}
$sc.Description = "Oxco - Compare, Bitrate, Autotagger"
$sc.Save()
Write-Host "Verknuepfung erstellt: $lnk"
