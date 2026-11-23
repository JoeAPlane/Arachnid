# Arachnid 1.1.0

A portable desktop companion for Windows 11 x64. A six-legged robot wanders, rests, watches the cursor, climbs and perches on windows, and explores the sides and ceiling of the desktop. Version 1.1 smooths gait, corners, perching, and idle movement and adds flick-to-throw with landing recovery.

## Run Arachnid on Windows

Use Windows 11 x64 and Microsoft’s latest supported x64 Visual C++ v14 Redistributable. Install it from Microsoft if it is missing. Extract the entire ZIP before running the executable. [Microsoft Visual C++ downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)

Quit any earlier preview, then extract `Arachnid-1.1.0-win-x64.zip` to its own folder. Open the extracted **Arachnid** folder and double-click **Arachnid.exe**. Keep the adjacent `_internal` folder in place. The package includes Python, the Qt libraries, and the servo sound. Your existing Windows preferences carry over. Launching the same settings profile again reopens the running companion.

The executable is unsigned, so Windows SmartScreen may show a warning. Verify
the SHA-256 against the release's matching checksum file before launching.
A verified clean Windows 11 installation remains untested.

On startup, Arachnid pulls open a rift with its front legs and walks out. Blackout Red is the default for a fresh profile. Your saved finish carries over.

## Set up a fresh checkout

Use 64-bit Python 3.12 on Windows 11. Run these commands from the project folder in PowerShell. If you need Python, get it from the official download page. [Python for Windows](https://www.python.org/downloads/windows/)

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m arachnid
```

- **Hover** over the character to highlight the body outline.
- **Left-click** the character to pet it. The scorpion crouches and wags its tail, with a small heart above it. **Drag** it with the left button to pick it up. It trails the cursor, kicks its legs briefly, pouts, and settles when released.
- Choose **Rest** in the right-click menu to make it sleep until you choose **Wake Up**. The same control also wakes it from a natural rest. Manual Pause continues to control movement separately.
- **Right-click** the body for **Pause**, **Resume**, **Settings**, or **Quit Arachnid**. You can also press Ctrl+C in the launch terminal.
- **Right-click the Arachnid icon in the Windows system tray** to access the same controls, plus **Show/Hide Arachnid**. Left-click the tray icon to bring Arachnid back after hiding it or closing its window. Look under the taskbar's hidden-icons arrow if the icon is in overflow. You can wake the robot, open Settings, or quit while the robot is hidden.
- Launch with `--paused` to start with autonomous activity suspended, `--speed 180` to change its walking speed, or `--watch-windows` to print window detections and bounds changes to the terminal. Combine flags as needed.
- Use `--settings-file PATH` for a separate INI profile. Without this flag, both the source and packaged app use your Windows user settings. Run from source to see the console output of `--watch-windows`.

To reopen after a full **Quit**, right-click **Arachnid.exe** in its permanent folder and choose **Show more options** → **Pin to taskbar**.

## Customize Arachnid

Open **Settings** and preview **Graphite**, **Foundry**, or **Glacier** using the **Finish** selector. The **Click light pulse** and **Click sound** controls work independently. The light pulse starts enabled, and the short servo sound starts muted. **Save** applies the choices and remembers them in your Windows user profile.

Enable **Curl up while sleeping** in Settings to tuck the legs and wrap the tail when you choose **Rest**. **Wake Up** uncurls the scorpion.

Use the **Size** slider to preview sizes from 70% to 150%. **Save** applies your chosen size on the desktop.

## Throwing

Hold the left button over Arachnid and move it normally to pick it up.
Release while flicking quickly to throw it, or slow down before releasing
for a normal drop. You can grab it again during flight. After landing, it
settles and returns to roaming unless you paused autonomous movement.
In **Settings**, turn off **Enable Throwing** to use normal drops every time.
The choice is saved with the rest of your preferences.

The throw can bounce gently off the current display's work-area boundaries.
Application windows remain climbable after recovery. Arachnid keeps a short
cursor history in memory only during a grab and clears it when the grab ends.

## View and finish options

Enable **Bird’s-eye view** in Settings to see the robot from above and let it walk in any direction across the current display. The default side view keeps window climbing and perching available.

Choose **Blackout Red** for charcoal armor with red optics or **Industrial Yellow** for weathered yellow plating, exposed wiring, and a segmented cyan visor.

For upside-down crawling, use the side view and drop Arachnid just below the active window with roughly 130 logical pixels of clearance below its bottom edge. It hooks its feet onto the underside, turns at the ends, and detaches if the edge no longer fits.

You can also drop it beside the lower half of either side. With clearance below, it walks down, rounds the corner, and continues underneath. A higher drop leads toward the top. During pickup, the chassis sags and tilts with sideways motion before the legs kick. On release, the legs extend and the chassis rebounds. In bird’s-eye view the robot shortens its stride through sharp turns.

## Try window navigation

1. Focus a normal, unmaximized window and leave room above and on either side of it. A window near the middle of the screen works well.
2. Drag Arachnid so its feet sit on the top edge, or drop its body about half a body length outside one side. Move the cursor away to let it start walking or climbing. It can also start climbing when it walks up to a reachable side on its own.
3. Move or resize the window while Arachnid is attached. It follows the window while the edge is reachable. Minimizing, closing, or switching away from that window returns the robot to desktop movement.

Arachnid hides and suspends its behavior for fullscreen apps, then restores your last Show/Hide choice when you return to the desktop. Ordinary maximized windows with a title bar keep it visible. Version 0.7.2 was checked with a live VALORANT lobby and a separate Direct3D 9 fullscreen fixture on one 1920 × 1080 display. Physical mixed-DPI testing and system sleep/resume remain open.

## Privacy

Arachnid reads the cursor position and foreground window geometry, window handle, and process ID to react, climb and hide over fullscreen apps. Throwing keeps at most a short history of pointer positions in memory during a grab. The history is cleared when the grab ends. It keeps preferences in your Windows user profile or in the INI file you specify with `--settings-file`. Relaunching uses a same-user local Windows pipe. Arachnid has no telemetry or outbound internet connections. The optional `--watch-windows` flag logs window handles, process IDs, and bounds locally. Review that output before sharing it.

## License

The original Arachnid code and assets are under the [MIT License](LICENSE). Bundled components have their own licenses. [Third-party notices](packaging/THIRD_PARTY_NOTICES.txt)

## Development

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m pytest -q
```

The native desktop test is opt-in because it briefly moves the actual mouse pointer. Its setup and the remaining desktop checks are in the [test report](TEST_REPORT.md). See the [architecture](ARCHITECTURE.md), [technical decisions](DECISIONS.md), and [project plan](PROJECT_PLAN.md) for implementation context.

## Build the Windows package

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

## Preview physical desktop edges

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
