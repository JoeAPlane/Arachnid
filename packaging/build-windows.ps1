[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Python,
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\build\win-x64')
)

$ErrorActionPreference = 'Stop'
$interpreter = (Resolve-Path -LiteralPath $Python).Path
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$output = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
$bundle = Join-Path $output 'Arachnid'
$originalPath = $env:Path

Push-Location -LiteralPath $project
try {
    $version = & $interpreter -c "import platform, sys; from arachnid import __version__; assert sys.platform == 'win32' and platform.machine().upper() == 'AMD64' and sys.version_info[:2] == (3, 12); print(__version__)"
    if ($LASTEXITCODE -ne 0) { throw 'The release build requires Windows x64 and Python 3.12.' }

    $archiveName = "Arachnid-$version-win-x64.zip"
    $archive = Join-Path $output $archiveName
    if ((Test-Path -LiteralPath $bundle) -or (Test-Path -LiteralPath $archive)) {
        throw "A build already exists in $output. Choose a fresh output directory."
    }
    New-Item -ItemType Directory -Path $output -Force | Out-Null
    $scratch = Join-Path $output 'pyinstaller'
    New-Item -ItemType Directory -Path $scratch -Force | Out-Null
    $assets = Join-Path $project 'arachnid\assets'

    $buildArgs = @(
        '--onedir', '--windowed', '--noupx', '--name', 'Arachnid',
        '--paths', $project, '--workpath', $scratch, '--specpath', $scratch, '--distpath', $output,
        '--icon', (Join-Path $assets 'arachnid.ico'),
        '--version-file', (Join-Path $PSScriptRoot 'windows-version.txt'),
        '--add-data', ('{0}:arachnid/assets' -f $assets),
        (Join-Path $PSScriptRoot 'windows_entry.py')
    )
    # Keep unrelated DLLs from other development tools out of dependency resolution.
    $env:Path = "$(Join-Path $env:SystemRoot 'System32');$env:SystemRoot;$(Split-Path $interpreter -Parent)"
    & $interpreter -I -m PyInstaller @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }

    # The QGraphicsView uses a QWidget raster viewport and creates no GL context.
    $softwareRenderer = Join-Path $bundle '_internal\PySide6\opengl32sw.dll'
    if (Test-Path -LiteralPath $softwareRenderer) {
        Remove-Item -LiteralPath $softwareRenderer
    }

    # Qt 6.10.2's Windows build imports the operating system's ICU entry points.
    $runtime = Join-Path $bundle '_internal'
    foreach ($file in (Get-ChildItem -LiteralPath $runtime -File | Where-Object Name -Match '^icu(?:uc|in|dt\d+)\.dll$')) {
        Remove-Item -LiteralPath $file.FullName
    }

    $licenses = Join-Path $bundle 'LICENSES'
    New-Item -ItemType Directory -Path $licenses | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'licenses\Qt') -Destination $licenses -Recurse
    $pythonLicense = & $interpreter -c "import sys; from pathlib import Path; print(Path(sys.base_prefix) / 'LICENSE.txt')"
    $pyInstallerLicense = & $interpreter -c "from importlib.metadata import distribution; d = distribution('pyinstaller'); print(next(d.locate_file(p) for p in d.files if p.name == 'COPYING.txt'))"
    if ($LASTEXITCODE -ne 0) { throw 'Could not locate the PyInstaller license.' }
    Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $licenses 'Python-LICENSE.txt')
    Copy-Item -LiteralPath $pyInstallerLicense -Destination (Join-Path $licenses 'PyInstaller-LICENSE.txt')
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'THIRD_PARTY_NOTICES.txt') -Destination $bundle
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'WINDOWS_README.txt') -Destination (Join-Path $bundle 'README.txt')

    Compress-Archive -LiteralPath $bundle -DestinationPath $archive -CompressionLevel Optimal
    $hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath "$archive.sha256" -Value "$hash  $archiveName" -Encoding ascii
    Get-Item -LiteralPath $archive
}
finally {
    $env:Path = $originalPath
    Pop-Location
}
