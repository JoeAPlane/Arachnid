# Technical decisions

## Use Qt's layered window for both rendering and hit testing

A small `QGraphicsView` with a translucent, frameless top-level window limits the area we draw and keeps the placeholder easy to replace. Qt's Windows implementation sends per-pixel alpha to the OS. Windows' layered-window hit test can pass clicks through zero-alpha pixels and keep the visible body interactive. [Qt widget translucency](https://doc.qt.io/qt-6/qwidget.html#creating-translucent-windows) · [Qt 6.10.2 Windows backing store](https://github.com/qt/qtbase/blob/v6.10.2/src/plugins/platforms/windows/qwindowsbackingstore.cpp) · [Microsoft layered windows](https://learn.microsoft.com/windows/win32/winmsg/window-features#layered-windows)

## Use a small pinned Python environment

Python 3.12 x64 and PySide6 Essentials provide Qt Core, GUI, and Widgets, including Graphics View. The runtime installs only Essentials and its required Shiboken wheel. Pytest and its dependencies are separate. [Qt for Python package details](https://doc.qt.io/qtforpython-6/package_details.html) · [PySide6 Essentials 6.10.2](https://pypi.org/project/PySide6-Essentials/6.10.2/)

## Separate window detection from animation timing

A 16 ms Qt timer advances the visible overlay according to elapsed time. The window scan runs at 500 ms because Phase 0 needs to observe bounds changes, with no dependency on individual animation updates. The scanner uses `EnumWindows` and prefers DWM's visible frame bounds, with a `GetWindowRect` fallback. The app reads desktop window metadata and logs only window handles, process IDs, and bounds when requested. [Microsoft EnumWindows](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-enumwindows) · [Microsoft DWM attributes](https://learn.microsoft.com/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute)

## Reference projects

- PixelPaws separates its native window integration and simulation in a C#/WPF codebase. Its source and architecture were reviewed for the Windows APIs it uses. Its MIT notice applies to the reference project. [PixelPaws repository](https://github.com/jordansbc/pixelpaws) · [Win32 implementation](https://github.com/jordansbc/pixelpaws/blob/main/src/DesktopPet/Native/Win32.cs)
- Clawd documents using physical pixels across mixed-DPI monitors. Its README identifies original character artwork and describes the project as provided as-is. [Clawd implementation notes and license statement](https://github.com/Hert4/clawd-window#license)
- Capri demonstrates relevant desktop interactions. Its repository applies the PolyForm Noncommercial license and requires credit for reuse. [Capri license](https://github.com/lachydotmcg/capri-desktop/blob/main/README.md#licence)

ARACHNID's Phase 0 code and placeholder are original. The three projects were research references.

## Animate the Phase 1 prototype with drawn parts

The renderer draws the body, tail segments, and individual leg links in Qt Graphics View. The gait derives the knee position from the hip and foot positions so changing the stride preserves link lengths. Motion supplies distance and facing to the renderer. This keeps Windows integration independent of the temporary artwork and keeps gait cadence proportional to walking speed.

## Give each behavior a limited duration

Walking and rest durations vary within short ranges. Observation ends when the cursor leaves or the attention timer expires. A separate leave distance prevents rapid transitions near the detection threshold, and a cooldown lets the robot resume its activity near a stationary cursor. User interactions suspend the active timer so a long drag preserves the activity in progress.

## Navigate the foreground window

Restricting routes to the foreground window lets the prototype use the surface the user is interacting with. The edge route tracks coordinates relative to that window and falls back to desktop movement if the surface becomes unsuitable. Routes require space for the full overlay within the current work area.

Use the visible foreground frame and monitor rectangle to decide whether to hide the companion, independent of the app's display-mode label. The fullscreen check is based on ordinary Windows desktop window metadata. [Microsoft fullscreen modes](https://devblogs.microsoft.com/directx/demystifying-full-screen-optimizations/)

## Share the rig across finishes

Graphite, Foundry, and Glacier recolor the same hand-drawn Qt rig. A finish changes armor, trim, and sensors without changing the navigation footprint. The optional light pulse stays within the optic, where native hit testing already treats the surface as opaque. The optional servo click uses a bundled synthesized WAV and Python's Windows audio API. [Python Windows audio documentation](https://docs.python.org/3.12/library/winsound.html)

## Ship a portable Windows build

PyInstaller packages the existing entry point as a windowed executable with an adjacent runtime folder. The bundle keeps Qt's dynamically loaded libraries as separate files. The raster Qt Widgets viewport creates no OpenGL context, so the build excludes the optional software OpenGL renderer. The ZIP includes usage instructions and upstream component notices. [PyInstaller packaging modes](https://pyinstaller.org/en/stable/usage.html)
