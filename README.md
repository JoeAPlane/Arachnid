# Arachnid

A free, open-source robot scorpion that wanders, climbs, and keeps you company on your Windows desktop.

<p align="center">
  <img src="assets/Arachnid-1.1.0-hero.gif" alt="A red and black robot scorpion walks left, climbs the desktop edge, and rounds the corner to crawl upside down." width="520">
</p>

## [⬇ Download for Windows (1.1.0)](https://github.com/JoeAPlane/Arachnid/releases/download/v1.1.0/Arachnid-1.1.0-win-x64.zip)

Windows 11 x64 · [Latest stable release and checksum](https://github.com/JoeAPlane/Arachnid/releases/latest)

- Watch six mechanical legs carry Arachnid around your desktop.
- See it climb windows and crawl upside down along the top of your screen.
- Pet it with a click, pick it up, or flick it and watch it land.
- Choose a finish and size, switch to a bird’s-eye view, or let it curl up to sleep.

## How to install

1. Download the Windows ZIP above. Install the [Microsoft Visual C++ v14 x64 Redistributable](https://aka.ms/vc14/vc_redist.x64.exe) if it isn’t already installed.
2. Right-click the ZIP, choose **Extract All**, and open the extracted **Arachnid** folder.
3. Double-click **Arachnid.exe**. Leave the **_internal** folder alongside it.

Windows SmartScreen may warn you because the executable is unsigned. The [release notes](RELEASE.md#verify-the-download) explain how to check the download. Testing on a verified clean Windows 11 installation is still pending.

## Meet your companion

- **Pet or pick up:** Left-click to pet. Hold and drag to pick it up. Release while flicking to throw it, or slow down before letting go to put it down gently.
- **Rest or customize:** Right-click Arachnid for **Rest**, **Wake Up**, **Pause**, and **Settings**. Settings include finishes, size, curl-up sleep, and a switch to disable throwing.
- **Find it again:** Use the Arachnid icon by the Windows clock to show, hide, or quit the app. If you don’t see it, check the taskbar’s hidden-icons arrow. Arachnid hides automatically over fullscreen apps.
- **Try window climbing:** Drop Arachnid near the top or side of an unmaximized window with space around it. In side view it can also walk along the underside when there’s enough room below.

## Privacy and license

Arachnid uses your cursor position and foreground window information to react and navigate. It stores your preferences locally. During a grab it keeps a short cursor history in memory and clears it when you release. Arachnid has no telemetry or outbound internet connections.

Arachnid is available under the [MIT License](LICENSE). Bundled libraries have separate [third-party notices](packaging/THIRD_PARTY_NOTICES.txt). See the [1.1.0 release notes](RELEASE.md) for compatibility details, the Qt security assessment, and matching source downloads.

## Development

<details>
<summary>Run from source, test, and build</summary>

### Run from source

Use 64-bit Python 3.12 on Windows 11. Run these commands from the project folder in PowerShell. If you need Python, get it from the official download page. [Python for Windows](https://www.python.org/downloads/windows/)

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m arachnid
```

### Run tests

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m pytest -q
```

The native desktop test is opt-in because it briefly moves the actual mouse pointer. Its setup and the remaining desktop checks are in the [test report](TEST_REPORT.md). See the [architecture](ARCHITECTURE.md), [technical decisions](DECISIONS.md), and [project plan](PROJECT_PLAN.md) for implementation context.

### Launch options

Use `--paused` to suspend autonomous movement at startup, `--speed 180` to change walking speed, or `--watch-windows` to print window detections from a source launch. These diagnostics include window handles, process IDs, and bounds. Review the output before sharing it. Use `--settings-file PATH` for a separate INI profile.

### Build the Windows package

For a release build, download and extract the pinned Astral CPython
3.12.16 Windows x64 archive. Verify its SHA-256 against the release entry.
In the commands below, set the interpreter path to the extracted
`python\python.exe`. [Astral runtime release](https://github.com/astral-sh/python-build-standalone/releases/tag/20261110) · [Exact archive](https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.12.16%2B20261110-x86_64-pc-windows-msvc-install_only.tar.gz)

```powershell
& 'PATH-TO-EXTRACTED-RUNTIME\python\python.exe' -m venv .build-venv
& .\.build-venv\Scripts\python.exe -m pip install -r requirements-build.txt
& .\packaging\build-windows.ps1 -Python .\.build-venv\Scripts\python.exe
```

The script puts the portable app folder, ZIP, SHA-256 checksum, and PyInstaller files under `Documents\ARACHNID\<version>`. For another build of the same version, pass `-OutputDirectory` with a fresh subfolder of `Documents\ARACHNID`. The script refuses a destination containing a previous build.

### Preview physical desktop edges

Use the normal side view. Run:

```powershell
& .\.venv\Scripts\python.exe -m arachnid --desktop-edge-preview --settings-file phase72-preview.ini
```

Right-click Arachnid and open **Desktop Edge Preview**. **Climb Left Edge**
and **Climb Right Edge** start at the corresponding lower boundary.
**Preview Upper Corner** starts near the upper-left turn, so you can watch
Arachnid go onto the ceiling and down the opposite edge sooner.
**Reverse Direction** reverses an attached crawl and **Detach** returns it
to the desktop. Use **Pause** or **Rest** to stop while attached. Dragging
releases the edge immediately.

Without the preview flag, Arachnid still roams normally and occasionally
explores the active screen's edges. A taskbar on an edge blocks that physical
surface. On a display with a top taskbar, Arachnid can climb a free side and
retrace its route. Desktop edges use Qt logical pixels. Routes stay on one
display and reset if its geometry or scaling changes.

</details>
