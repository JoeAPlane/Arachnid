# Arachnid 1.1.0 — Movement & Interaction Update

Arachnid is a free, open-source robot scorpion for your Windows desktop. It roams, climbs windows, reacts when you pet it, and can curl up to sleep.

## Download for Windows

**[Download Arachnid 1.1.0 for Windows x64](https://github.com/JoeAPlane/Arachnid/releases/download/v1.1.0/Arachnid-1.1.0-win-x64.zip)** · [SHA-256 checksum](https://github.com/JoeAPlane/Arachnid/releases/download/v1.1.0/Arachnid-1.1.0-win-x64.zip.sha256)

1. On Windows 11 x64, install the [Microsoft Visual C++ v14 x64 Redistributable](https://aka.ms/vc14/vc_redist.x64.exe) if it isn’t already installed.
2. Quit any running copy of Arachnid and choose **Extract All** on the downloaded ZIP.
3. Open **Arachnid.exe** in the extracted **Arachnid** folder. Keep the **_internal** folder next to it. Your settings carry over.

**Windows SmartScreen may show a warning** because the executable is unsigned. Testing on a verified clean Windows 11 x64 installation is still pending.

## What’s new in 1.1.0

- **Screen-edge climbing.** Arachnid can climb a clear side of the screen, round a corner, and crawl upside down along the top. Each route stays on one display.
- **Smoother animation.** Walking, stopping, turning, and perching flow together more naturally.
- **Flick to throw.** Pick it up with the left mouse button and let go during a quick flick. It lands, recovers, and goes back to roaming. Slow releases put it down gently. You can turn throwing off in **Settings**.

## Verify the download

Save the ZIP and its checksum file to the same folder. In PowerShell, open that folder and run these commands. The hash from the first command should match the hash shown by the second.

```powershell
Get-FileHash .\Arachnid-1.1.0-win-x64.zip -Algorithm SHA256
Get-Content .\Arachnid-1.1.0-win-x64.zip.sha256
```

## Qt Network security assessment

The package contains Qt Network 6.11.3, which remains affected by
[CVE-2026-116337](https://www.qt.io/blog/security-issue-cve-2026-116337?hsLang=en).
The two Qt 6.11 patches limit the HTTP response status line and header block
in Qt's HTTP client. Arachnid's only Qt Network calls use `QLocalServer` and
`QLocalSocket` for single-instance detection. The Windows pipe is restricted
to the same user and its name is derived from the profile. A connection
signals the existing window to reopen. Arachnid closes the connection
without reading or interpreting its contents. The app creates no HTTP
client, fetches no URLs, and has no route from application input to the
affected HTTP parser.

A patched compatible Windows x64 PySide6 wheel was unavailable when assessed.
The bundled library still contains the affected code. Reassess this finding
if Arachnid adds HTTP functionality, and update Qt when a compatible patched
wheel becomes available.

## License and corresponding source

Arachnid uses the [MIT License](https://github.com/JoeAPlane/Arachnid/blob/v1.1.0/LICENSE). The ZIP contains
`THIRD_PARTY_NOTICES.txt` and the individual license texts.
[Third-party notices](https://github.com/JoeAPlane/Arachnid/blob/v1.1.0/packaging/THIRD_PARTY_NOTICES.txt)

The shared libraries are Qt 6.11.3 and PySide6 Essentials/Shiboken6 6.11.3.
The matching source archives are available from Qt at no charge.

- [Qt Base 6.11.3](https://download.qt.io/official_releases/qt/6.11/6.11.3/submodules/qtbase-everywhere-src-6.11.3.tar.xz)
- [Qt Image Formats 6.11.3](https://download.qt.io/official_releases/qt/6.11/6.11.3/submodules/qtimageformats-everywhere-src-6.11.3.tar.xz)
- [PySide6 and Shiboken6 6.11.3](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.3-src/pyside-setup-everywhere-src-6.11.3.tar.xz)

Local builds are saved in a subfolder of `Documents\ARACHNID`. Use the
[build instructions](https://github.com/JoeAPlane/Arachnid/blob/v1.1.0/README.md#build-the-windows-package) to reproduce the
portable package from the exact release source.
