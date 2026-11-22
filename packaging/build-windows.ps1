[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Python,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$interpreter = (Resolve-Path -LiteralPath $Python).Path
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$output = if ($OutputDirectory) {
    $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
}
$originalPath = $env:Path
$originalPyInstallerCache = $env:PYINSTALLER_CONFIG_DIR

Push-Location -LiteralPath $project
try {
    $version = & $interpreter -B -c "import platform, sys; from arachnid import __version__; assert sys.platform == 'win32' and platform.machine().upper() == 'AMD64' and sys.version_info[:2] == (3, 12); print(__version__)"
    if ($LASTEXITCODE -ne 0) { throw 'The release build requires Windows x64 and Python 3.12.' }

    $documents = [Environment]::GetFolderPath('MyDocuments')
    if (-not $documents) { throw 'Windows could not locate your Documents folder.' }
    $outputRoot = Join-Path $documents 'ARACHNID'
    if (-not $output) { $output = Join-Path $outputRoot $version }
    $output = [IO.Path]::GetFullPath($output)
    if (-not $output.StartsWith("$outputRoot\", [StringComparison]::OrdinalIgnoreCase) -or
        $output.TrimEnd('\') -eq $outputRoot) {
        throw 'Build output must be in a subfolder of Documents\ARACHNID.'
    }

    $bundle = Join-Path $output 'Arachnid'
    $archiveName = "Arachnid-$version-win-x64.zip"
    $archive = Join-Path $output $archiveName
    $scratch = Join-Path $output 'pyinstaller'
    $existing = @($bundle, $archive, "$archive.sha256", $scratch) | Where-Object { Test-Path -LiteralPath $_ }
    if ($existing) {
        throw "A build already exists in $output. Choose a fresh output directory."
    }
    New-Item -ItemType Directory -Path $output -Force | Out-Null
    New-Item -ItemType Directory -Path $scratch -Force | Out-Null
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $scratch 'cache'
    $assets = Join-Path $project 'arachnid\assets'

    $buildArgs = @(
        '--onedir', '--windowed', '--noupx', '--name', 'Arachnid',
        '--paths', $project, '--workpath', $scratch, '--specpath', $scratch, '--distpath', $output,
        '--icon', (Join-Path $assets 'arachnid.ico'),
        '--version-file', (Join-Path $PSScriptRoot 'windows-version.txt'),
        '--add-data', ('{0}:arachnid/assets' -f $assets),
        '--exclude-module', 'PySide6.QtSvg',
        '--exclude-module', '_hashlib',
        '--exclude-module', '_ssl',
        '--hidden-import', '_sha2',
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

    # Qt's Windows build imports the operating system's ICU entry points.
    $runtime = Join-Path $bundle '_internal'
    # Arachnid draws its own raster graphics and only uses a same-user local pipe.
    # Qt's automatic plugin collection also includes optional SVG and TLS backends.
    $unusedPlugins = @(
        'PySide6\plugins\imageformats\qsvg.dll',
        'PySide6\plugins\iconengines\qsvgicon.dll',
        'PySide6\plugins\tls\qopensslbackend.dll',
        'PySide6\plugins\tls\qschannelbackend.dll',
        'PySide6\plugins\tls\qcertonlybackend.dll',
        'PySide6\Qt6Svg.dll'
    )
    foreach ($name in $unusedPlugins) {
        $file = Join-Path $runtime $name
        if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file }
    }
    # Distribute the app separately from Microsoft's redistributable. The
    # supported host installs and services the runtime through Microsoft's installer.
    $excludedLibraries = '^(libcrypto.*|libssl.*|msvcp140.*|vcruntime140.*|Qt6Svg.*|q(svg|svgicon|opensslbackend))\.dll$'
    Get-ChildItem -LiteralPath $runtime -Recurse -File |
        Where-Object Name -Match $excludedLibraries |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName }
    $forbidden = Get-ChildItem -LiteralPath $runtime -Recurse -File |
        Where-Object Name -Match $excludedLibraries
    if ($forbidden) { throw "Unexpected library in the release: $($forbidden.Name -join ', ')." }
    foreach ($file in (Get-ChildItem -LiteralPath $runtime -File | Where-Object Name -Match '^icu(?:uc|in|dt\d+)\.dll$')) {
        Remove-Item -LiteralPath $file.FullName
    }

    # The notices cover the traceable Astral Windows x64 build, including its libffi fork.
    $runtimeHashes = @{
        'python312.dll' = '659761ee44cb66968b7ef15570a021beed8181c11e9c81dec53e4851a58f549f'
        'libffi-8.dll' = '0f6efcceab5949720114ab45511c7226dc02303b57d223968b0ad5310f96d41f'
    }
    foreach ($component in $runtimeHashes.GetEnumerator()) {
        $binary = Join-Path $runtime $component.Key
        if (-not (Test-Path -LiteralPath $binary -PathType Leaf) -or
            (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash -ne $component.Value) {
            throw "Unexpected $($component.Key). Use the pinned runtime described in README.md."
        }
    }

    $licenses = Join-Path $bundle 'LICENSES'
    New-Item -ItemType Directory -Path $licenses | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'licenses\Qt'), (Join-Path $PSScriptRoot 'licenses\Python') -Destination $licenses -Recurse
    $pythonLicense = & $interpreter -c "import sys; from pathlib import Path; print(Path(sys.base_prefix) / 'LICENSE.txt')"
    $pyInstallerLicense = & $interpreter -c "from importlib.metadata import distribution; d = distribution('pyinstaller'); print(next(d.locate_file(p) for p in d.files if p.name == 'COPYING.txt'))"
    if ($LASTEXITCODE -ne 0) { throw 'Could not locate the PyInstaller license.' }
    Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $licenses 'Python-LICENSE.txt')
    Copy-Item -LiteralPath $pyInstallerLicense -Destination (Join-Path $licenses 'PyInstaller-LICENSE.txt')
    Copy-Item -LiteralPath (Join-Path $project 'LICENSE') -Destination (Join-Path $licenses 'Arachnid-MIT.txt')
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'THIRD_PARTY_NOTICES.txt') -Destination $bundle
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'WINDOWS_README.txt') -Destination (Join-Path $bundle 'README.txt')

    Compress-Archive -LiteralPath $bundle -DestinationPath $archive -CompressionLevel Optimal
    $hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath "$archive.sha256" -Value "$hash  $archiveName" -Encoding ascii
    Get-Item -LiteralPath $archive
}
finally {
    $env:Path = $originalPath
    $env:PYINSTALLER_CONFIG_DIR = $originalPyInstallerCache
    Pop-Location
}
