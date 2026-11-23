# Arachnid 1.1.0 — Movement & Interaction Update

Arachnid is a free, open-source mechanical scorpion companion for Windows.
The six-legged side-profile robot roams your desktop, follows the cursor,
lets you pet it, climbs windows, and can rest or sleep. The tray controls and
original finishes carry over from 1.0.0.

- **Desktop-edge climbing.** Arachnid occasionally climbs a clear side of the
  active screen, rounds an upper corner, and traverses the top upside down.
- **Smoother movement.** Walking, stopping, perching, and turning have smoother
  transitions. The six legs plant more steadily, and the tail follows the chassis.
- **Flick-to-throw.** Grab with the left button and release during a quick flick.
  Arachnid flies, absorbs the landing, and resumes roaming. Slow releases still
  put it down gently. Disable **Enable Throwing** in **Settings** if you prefer.

## Install

Use Windows 11 x64 and the latest supported **Microsoft Visual C++ v14 x64
Redistributable**. Download the matching ZIP and checksum, verify the SHA-256,
and extract the entire archive. Open `Arachnid.exe` with the adjacent
`_internal` folder in place. Quit any previous Arachnid instance before launching.
Existing settings carry over. [Microsoft Visual C++ download](https://aka.ms/vc14/vc_redist.x64.exe)

```powershell
Get-FileHash .\Arachnid-1.1.0-win-x64.zip -Algorithm SHA256
Get-Content .\Arachnid-1.1.0-win-x64.zip.sha256
```

The executable is unsigned and may trigger a Windows SmartScreen warning.
A verified clean Windows 11 x64 installation remains untested. Physical
desktop-edge routes stay on one display.

## License and corresponding source

Arachnid uses the [MIT License](LICENSE). The ZIP contains
`THIRD_PARTY_NOTICES.txt` and the individual license texts.
[Third-party notices](packaging/THIRD_PARTY_NOTICES.txt)

The shared libraries are Qt 6.11.3 and PySide6 Essentials/Shiboken6 6.11.3.
The matching source archives are available from Qt at no charge.

- [Qt Base 6.11.3](https://download.qt.io/official_releases/qt/6.11/6.11.3/submodules/qtbase-everywhere-src-6.11.3.tar.xz)
- [Qt Image Formats 6.11.3](https://download.qt.io/official_releases/qt/6.11/6.11.3/submodules/qtimageformats-everywhere-src-6.11.3.tar.xz)
- [PySide6 and Shiboken6 6.11.3](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.3-src/pyside-setup-everywhere-src-6.11.3.tar.xz)

Local builds are saved in a subfolder of `Documents\ARACHNID`. Use the
[build instructions](README.md#build-the-windows-package) to reproduce the
portable package from the exact release source.
