# Test report

## 1.0.0 startup update

The extracted Windows build held its overlay in place during the rift animation, resumed walking afterward, and saved Blackout Red on a fresh profile. Regression tests cover playing the entrance once per launch, cancelling it when hidden, and preserving existing finish choices. The final build also passed the paused launch check. All 68 native tests passed at 100% Qt scaling.

## 1.0.0 · Windows release

The portable Windows x64 executable was built from 0.9.2.3. After a Windows Close event hid Arachnid, three overlapping launches for the same test profile restored the original window. Explicit Quit exited the original process, and a subsequent launch opened a new instance. The local activation test also checked that quitting releases the profile lock.

The full native suite reported 65 passed at both 100% and 150% Qt scaling. The executable version, ZIP CRCs, and SHA-256 were verified. The package is unsigned. Physical mixed-DPI, real system sleep/resume, and a separate clean Windows account remain outside this run.

## 0.9.2 · Expressions and curled sleep

Reviewed rendered petting and sleep poses for EdgeRunner and Graphite in both views. The native suite passed all 63 tests, including the petting eyes and transitions into and out of curled sleep. The extracted Windows build saved the curled-sleep setting, loaded it after relaunch, and completed Rest and Wake Up. The ZIP passed its archive and SHA-256 checks.

## 0.9.1 · Branding and interaction preview

Windows extracted the new scorpion icon from the packaged executable, whose product name reads Arachnid. The packaged size slider changed the desktop overlay from 176 to 264 logical pixels at 150% and restored that size after relaunch. The existing finish key continues to load as Edge Runner. The native suite passed all 61 tests, including click-through, the petting reaction, and drag behavior. Source tests verified scaled window contact and persisted size settings.

## 0.9.0 · Windows release candidate

**November 22, 2026.** Ran the 0.8.0 and 0.9.0 extracted Windows packages successively at 100% Qt scaling on the same 1920 × 1080 desktop. Both started with isolated settings. Windows process counters were sampled about four times per second. CPU percentages are a share of one logical core. Active runs included autonomous walking and rest. The paused and manually hidden samples came from a separate launch for each build.

| State | Seconds per build | 0.8.0 CPU | 0.9.0 CPU | 0.8.0 peak working set | 0.9.0 peak working set | 0.8.0 peak private | 0.9.0 peak private |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Active | 180 | 8.92% | 8.77% | 56.56 MiB | 56.48 MiB | 25.55 MiB | 25.46 MiB |
| Paused | 30 | 0.21% | 0.05% | 55.84 MiB | 55.81 MiB | 25.46 MiB | 25.21 MiB |
| Manually hidden | 30 | 0.21% | 0.05% | 60.30 MiB | 60.41 MiB | 26.44 MiB | 26.27 MiB |
| Fullscreen suppressed | 20 | 0.23% | 0.08% | 56.58 MiB | 56.45 MiB | 25.30 MiB | 25.27 MiB |

During the active 0.9.0 sample, CPU averaged 11.70% in intervals with a position change. Average private memory moved from 25.46 MiB in the first 10 seconds to 25.27 MiB in the last 10 seconds. Paused, hidden, and fullscreen samples recorded zero position changes. Both builds restored visibility after fullscreen and exited cleanly while hidden. These results cover a single desktop session with short inactive-state measurements.

The relocated package loaded Python, Qt Core, and the Windows Qt platform plugin from its own bundle. On a fresh INI profile, Settings saved Neon Runner, bird’s-eye view, and both independent click effects. A new executable process loaded those choices and saved them again. A separate Windows account remains pending.

The Explorer tray menu passed four additional Hide and Show cycles, along with opening Settings while hidden, pausing, resting, waking, and quitting while hidden. All 59 native tests passed at both 100% and 150% Qt scaling. The release ZIP passed its SHA-256 and per-entry CRC checks.

## 0.8.0 · Movement and animation

**November 22, 2026.** The Windows x64 package passed a native pickup, lower-side drop, corner turn, underside crawl, and clean exit on the left at 100% Qt scaling and on the right at 150%. The extracted package also passed bird’s-eye pickup lag, release positioning, travel after turning away from the right work-area edge, and clean exit at both scales. The 100% bird’s-eye smoke passed after retries for pointer drift.

Rendered pose checks covered the initial sag, sideways tilt, struggle, release, and landing in both views, plus the turn from a lower wall to the underside. Source tests checked both lower-corner paths, fallback to climbing when the underside lacks clearance, continuity during a quick regrab, and the transparent overlay bounds. The full desktop suite passed all 59 tests at each scale. The standard suite passed 57 tests with two native-only skips.

## 0.7.2 · Display changes and fullscreen

The release uses the final mouse-release coordinates when dropping the pet and ends an active grab when the grabbed point disappears from the display layout. Before the fixes, a simulated release on a left-hand 150% screen used the last move on the right-hand 100% screen, and removing the grabbed display left the drag timer active. Both regressions passed after the fixes.

- The extracted executable completed three maximized → borderless fullscreen → windowed cycles at each of 100% and 150% Qt scaling on one physical display. The pet stayed visible while maximized, hid during fullscreen, and returned afterward.
- A local Direct3D 9 fixture created a 1920 × 1080 swap chain, read back `Windowed = FALSE`, and presented frames. Windows reported the overlay hidden during presentation and visible after the fixture released the device and closed.
- VALORANT reached its lobby. A separate Windows observer sampled the foreground window and the test overlay. The game covered the 1920 × 1080 monitor while the overlay stayed hidden for eight consecutive seconds. This check covered the lobby with the current game installation.
- The native suite passed 55 tests at each scale. A subsequently added simulated one-hour timer gap confirmed that the first tick advances movement and behavior by their bounded intervals. The final offscreen suite passed 54 tests with two native-only skips.
- Windows reported one active display. Physical mixed-DPI crossings, cable disconnect/reconnect, and actual OS suspend/resume remain open.

## 0.7.1 · Desktop reliability pass

**November 22, 2026.** Tested the existing 0.7.0 Windows package. At 100% Qt scaling, real right-clicks through Explorer's hidden-icons panel verified Hide, Settings while hidden, Show, Resume, Pause, Rest, Wake Up, and clean exit while hidden and asleep. The test checked menu ownership before selecting an action because a separate running preview registered an icon with the same label.

The extracted package passed pickup, underside attachment, window resize tracking, crawl, and menu exit at 100% and 150% Qt scaling. After the test fixes, the full opt-in source suite passed all 53 tests at each scale, including foreground fullscreen suppression and restoration on the single test display.

The navigation test now uses an isolated INI profile so the user's saved view cannot affect the side-view perch check. Native fixture focus and pointer acquisition now retry on the shared desktop. The earlier interruptions were in fixture setup and pointer targeting. This pass produced test and documentation changes. The verified download is 0.7.0.

## 0.7.0 · Windows tray and Neon Runner

**November 22, 2026.** The standard source suite reported 51 passed and two opt-in tests skipped. The extracted package registered the ARACHNID icon in Explorer's hidden-icons panel and opened its native menu. A scripted tray callback followed by mouse selections verified Hide, Show, Pause/Resume, Rest/Wake Up, opening Settings while hidden, and exiting with status 0 while hidden and asleep.

The extracted package passed a live Neon Runner drop, window resize, underside crawl, and menu exit at 150% Qt scaling. Sampled side and overhead walking and pickup poses kept a transparent border. The 100% packaged run stopped when it could not focus its fixture. The full opt-in source suite reported 52 passed and one interruption when the pointer moved off its target during the desktop input test.

In a side-by-side paused sample, the packaged working set rose from 54.44 MiB in 0.6.1 to 56.05 MiB in 0.7.0. Private memory rose from 24.60 to 25.47 MiB. The running 0.7.0 Neon Runner used 63.41 MiB of working set and 27.00 MiB of private memory during the live underside crawl.

A 100-second offscreen Qt stress run rendered 6,240 frames while cycling five finishes and repeating 39 routes with pickup, release, resize, and detachment. The 95th-percentile render time was 1.49 ms. The harness working set went from 61.15 to 62.68 MiB and peaked at 62.73 MiB. Private memory went from 40.74 to 40.84 MiB and peaked at 40.95 MiB. These measurements cover a short synthetic render workload.

## 0.6.1 · Underside crawling and finishes

**November 22, 2026.** The source suite reported 48 passed and two opt-in tests skipped. The freshly extracted package passed native checks at 100% Qt scaling with Blackout Red and at 150% with Neon Runner. Both checks dropped the robot under a normal window, moved and resized the window, observed horizontal crawling along its bottom edge, and quit from the menu.

A 100-second offscreen Qt stress run rendered 6,250 frames across 40 routes while cycling all five finishes and repeating pickup, release, resize, and detachment. Render time at the 95th percentile was 1.35 ms. The harness working set rose from 60.69 to 62.20 MiB, peaking at 62.24 MiB. Private memory rose from 40.24 to 40.34 MiB. These are short-run harness measurements.

On the same Windows desktop, paired paused samples of the portable builds measured 54.27 MiB for 0.6.0 and 54.38 MiB for 0.6.1. The 0.6.1 package sampled 61.55–62.29 MiB of working set during live underside crawling at the two Qt scales.

## 0.6.0 · Pickup, bird’s-eye view, and sleep

**November 22, 2026.** The extracted Windows executable passed the new interaction checks at 100% and 150% Qt scaling on one display. **Rest** kept the robot stationary beyond its natural rest duration. The same menu position showed **Wake Up** and started activity again. Bird’s-eye view traveled on both axes and persisted through a fresh launch. With the native pointer held down, the robot followed with a bounded lag and settled at the intended drop position on release.

The source suite passed all 49 tests at 150% Qt scaling, including the existing native click-through, drag capture, perching, settings, and fullscreen checks. Sampled side and overhead gait and pickup poses kept the transparent perimeter. The new tests also exercised reflection at both work-area edges, control of the sleep timers, and animation cleanup after a drag. Physical mixed-DPI and true exclusive fullscreen tests remain pending.

## 0.5.1 · Preview reliability

**November 21, 2026.** Windows 11 x64, build 26300. One 1920 × 1080 display was available.

- Reproduced the 0.5.0 false hide. Win32 reported a conventional maximized title-bar fixture, and its visible bounds covered all 1920 × 1080 pixels. The old classifier marked it fullscreen.
- The extracted 0.5.1 executable completed three transitions from maximize to fullscreen and back to windowed at each of 100% and 150% Qt scaling. It stayed visible while maximized, hid in fullscreen, and returned when the same foreground window left fullscreen. Packaged click-through, drag, perch and edge following, menu exit, and saved preferences after relaunch also passed at both scales.
- Added regression checks for brief losses of foreground information, focus moving into Settings and back to the desktop, relocation to the nearest mock work area after a display disappears, timer recovery after a simulated gap with zero displays, and conversion of a negative monitor origin at 150% scaling. The routing test also rejects a display area that is too small for the overlay.
- The source suite passed all 46 tests at 150% Qt scaling. At 100%, 45 passed and one opt-in mouse test stopped when the system pointer would not stay at the fixture position. The isolated retry hit the same pointer guard. The packaged pointer tests completed successfully at both scales.

Tests used an isolated application profile and a relocated package. A separate clean Windows account, physical mixed-DPI displays, live display disconnection, true exclusive fullscreen, and VALORANT/Vanguard were unavailable for verification in this pass.

## Phase 5 · Windows x64 preview

**November 21, 2026.** Windows 11 x64, build 26300. ARACHNID 0.5.0 was packaged with Python 3.12.14, PySide6 6.10.2, and PyInstaller 6.22.3.

- A freshly extracted copy launched from an empty working folder with Python and Qt removed from the child process's search path. Process inspection confirmed that the interpreter, Qt Core, and the Windows platform plugin loaded from the extracted bundle and Windows ICU loaded from System32.
- The packaged checks passed at 100% and 150% Qt scaling on one display. They covered click-through into a separate test app, dragging, perching and following a moved window, fullscreen hiding and restoration, and clean exit through the menu. Glacier and both click feedback settings survived reopening the executable with an isolated INI profile. Windows accepted the bundled 115 ms servo asset; audible output was not independently monitored.
- The source suite passed all 41 tests at 150% Qt scaling. At native scale, 40 passed in the complete run and the mouse test passed in isolation after pointer interference interrupted that step in the complete run.
- The initial 51.62 MiB archive contained an incompatible ICU DLL discovered on the build host's search path. The build now isolates its search path, uses Windows' ICU, and omits the optional software OpenGL renderer for the raster viewport. The delivered ZIP is 28.61 MiB and expands to 72.87 MiB. Its checksum, all ZIP entry CRCs, x64 executable header, and required runtime files were verified.
- Standard launches now skip the full desktop window census. Navigation and fullscreen behavior still use foreground monitoring. The separate window census remains available for diagnostics.

### Packaged performance

During a 125-second sample of the extracted executable after warm-up, the working set moved from 54.84 to 55.56 MiB with a 55.58 MiB sampled peak. Private memory moved from 24.63 to 24.70 MiB. CPU readings are percentages of one logical core, grouped by visible position changes and overlay visibility.

| Observed state | Sampled time | CPU |
| --- | ---: | ---: |
| Walking | 37.6 s | 8.92% |
| Visible idle, including rest | 15.9 s | 0.39% |
| Hidden | 71.2 s | 0.31% |

The sampler observed 2,248 position updates. Consecutive updates during motion had a median interval of 16.34 ms and a 95th percentile of 16.71 ms. This measures Win32 window position updates. Fullscreen coverage in this run changed with foreground focus. A separate sustained fullscreen probe recorded zero position updates while the fixture held focus, but the fixture lost focus after 1.2 seconds.

A separate clean Windows account, physical mixed-DPI displays, display disconnects, true exclusive fullscreen, and VALORANT/Vanguard remain unverified. The fresh INI profile and sanitized executable environment isolated application settings and dependencies on the available Windows account. The preview is unsigned.

## Phase 4 · Visual polish and customization

**November 21, 2026.** The full suite passed at 100% and with a process-local `QT_SCALE_FACTOR=1.5` override, 40 tests each on one Windows display.

- Inspected rendered Graphite, Foundry, and Glacier finishes on light and dark backgrounds. The preview included standing, resting, looking, and rotated gait poses.
- Verified that the settings preview could be canceled and that saving applied the finish. A fresh Python process reopened the settings store and restored the saved finish, sound, and light preferences. Click sound and light effects could be enabled independently.
- Native Windows tests still passed for click-through around the rig and at a vacated toe position, clicking and dragging, and perching, climbing, and window recovery. The Settings menu opened with real pointer input. A fullscreen fixture dismissed Settings and hid the overlay, then desktop focus restored the companion.
- The gait tests verified that horizontal foot velocity matches across lift-off and touchdown, and that animated poses retained a transparent perimeter. The pause test verified that movement stopped immediately and the legs finished their settling animation.
- The servo clip is a 115 ms PCM WAV. The Windows playback API accepted it asynchronously. Audible output was not independently monitored.

During a 150-second Windows desktop sample, ARACHNID rendered normally, suspended animation while a fullscreen window held focus, and later resumed. During active movement the median animation callback interval was 16.02 ms and the 95th percentile was 16.77 ms. The working set rose from 51.07 to 55.28 MiB and stayed near 55.3 MiB after the first 30 seconds. Process CPU averaged 1.35% of one logical core across the mixed activity sample, including fullscreen suspension. Sustained active performance and physical mixed-DPI displays remain unverified.

## Phase 3 · Desktop navigation

**November 21, 2026.** The full suite passed at 100% and with the process-local `QT_SCALE_FACTOR=1.5` override, 37 tests each on one Windows display.

- A simulated drop onto a separate application's title-bar edge attached the robot. The native fixture then moved and resized, and the robot followed the new top edge. Minimizing or closing the fixture detached the robot at a visible location.
- The robot reached a fixture's left side during an ordinary walk, climbed, rotated around the corner, and began walking along the top. Geometry tests covered the turn from both sides, reversing on the top, and rejecting an edge when the display has insufficient clearance. Sampled rotated poses kept a transparent perimeter.
- A separate Qt fullscreen fixture took foreground focus. ARACHNID became invisible at the Win32 window level, released the route, and stopped both motion and behavior timers. Returning focus to the windowed fixture restored visibility and activity. A separate test checked that a manual pause survived fullscreen entry and exit.
- The prior native checks still passed for click-through, including previously painted pixels, drag capture and recovery, window movement, and menu exit.

Fullscreen verification used the controlled borderless fixture. True exclusive fullscreen, VALORANT and Vanguard, physical mixed-DPI layouts, and long sessions under game load remain unverified. The fullscreen check is a frame-coverage heuristic and can also trigger on a maximized window with an auto-hidden taskbar.

## Phase 2 · Autonomous behavior

**November 21, 2026.** The full suite passed at native scale and with the process-local `QT_SCALE_FACTOR=1.5` override, 30 tests each.

- Behavior tests exercised rest and walking transitions, attention with separate enter and leave distances, timeout and cooldown near a stationary cursor, and repeated click reactions.
- The Windows tests moved the real cursor into and out of observation range. ARACHNID stopped its movement timer, looked toward the pointer, and resumed walking when the pointer left. The Qt tests verified that dragging and pausing preserved the active timer, and that a click briefly held the character in place before it walked again.
- Existing native checks passed for transparent areas and previously painted foot positions, drag capture, window awareness, and quitting through the menu.
- In a 15-second Windows run, ARACHNID completed two rest-to-walk transitions. The movement timer stopped during both rests and resumed for both walks. The instrumented process averaged 6.46% of one logical CPU during that sample. This was a short mixed-activity run on one display.

For a manual check, move the cursor away and watch for a crouched resting pose with dimmed sensors. Bring the cursor near, move it to either side of the robot, then move it away. A click should briefly brighten the eye. A long drag or manual pause should preserve the current activity until release or resume. The physical display and long-run checks below are still pending.

## Phase 1 · Mechanical prototype

**November 21, 2026.** All 25 tests passed at native scale and again with a process-local `QT_SCALE_FACTOR=1.5` override. Both runs exercised native Windows pointer input against a separate application process.

- The gait tests verified planted-foot motion, swing clearance, and fixed lengths for the two leg segments. The renderer kept a transparent perimeter across 48 sampled poses.
- Windows accepted pointer input on a painted foot and correctly found the underlying test window at the old foot position after the leg moved. Cross-process click-through, hover, click feedback, drag release, interrupted capture, the **Quit ARACHNID** menu, and window awareness also passed.
- A quick click followed by a press at the same point previously let Qt's double-click event bypass drag initiation. A regression test covers the fix.
- The prototype switches facing at work-area edges and settles into a standing pose when paused or held. Physical mixed-DPI monitor crossings, hot-plug, and extended runs under load still need verification. The display and input checks below apply to this prototype as well.

Each short performance sample lasted about 12.5 seconds on one 1920 × 1080 display at native scale, with window scanning enabled. Walking at the default speed produced 62.57 position updates per second (17.15 ms at the 95th percentile), used 7.50% of one logical CPU, and ended at 53.77 MiB of working set. A stationary paused run showed zero position updates, 0.13% of one logical CPU, and 53.38 MiB of working set. The position cadence measures Qt updates rather than displayed frames.

## Phase 0 · Overlay baseline

**November 21, 2026.** Windows 11 x64, build 26300. Tests used Python 3.12.14, Qt 6.10.2 via PySide6 Essentials, and one 1920 × 1080 display at 100% scaling. Windows reported a refresh rate of about 240 Hz.

### Verified

| Area | Evidence |
| --- | --- |
| Setup | A new workspace virtual environment installed the pinned packages. `pip check` reported no broken requirements. |
| Launch and exit | The documented module entry point launched successfully on three consecutive runs. Windows close messages ended the default and custom-speed runs. A real Ctrl+C console event ended the paused run. All three exit codes were 0. |
| Rendering and input | The native Windows test sent pointer input through a transparent corner to a separate process. On the painted body, entering with the cursor updated hover state and clicking changed the fill color. A drag crossed beyond the original shape before release. A real right-click opened the menu and selecting **Quit ARACHNID** closed the overlay. |
| Interrupted input | Forcibly releasing Win32 mouse capture reproduced a stalled press. After the capture-loss fix, the same test observed the overlay cancel the press before the mouse button was released. |
| Movement | The Qt tests exercised pause, resume, suspension during a press, and a bounce inside the display work area. Unit tests covered geometry clamping, negative display origins, fractional movement, and edge reflection. |
| Window awareness | The Windows test detected a separate process's test window and refreshed its visible bounds after it moved and resized. It detected minimization, restoration, and closure. The scan excluded the overlay. |
| Test suite | 19 passed at native scale and 19 passed with a process-local `QT_SCALE_FACTOR=1.5` override, including the opt-in desktop test in both runs. The regular command runs 18 tests and skips the opt-in test. |

The first native test attempt could query Windows' hit test but could not set the real pointer inside the sandbox. The successful native run used desktop access. Input responsiveness was verified by observing the actual event and its UI effect during the scripted interaction. End-to-end input latency was not measured.

### Short performance sample

The overlay ran for about 12.5 seconds in each state after a 1.3-second warm-up. The scanner stayed active at its normal 500 ms interval. CPU is process time divided by wall time, expressed as a share of one logical CPU. RAM is the process working set. A Qt window move event counts once per position update.

| State | Position updates/s | Median interval | 95th percentile | Longest interval | CPU | RAM at end |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Moving at default speed | 62.52 | 15.99 ms | 17.15 ms | 18.08 ms | 7.50% | 53.54 MiB |
| Paused | 0 | — | — | — | 0.38% | 53.57 MiB |

Position updates measure the animation cadence inside Qt. Displayed frame rate, long-run memory stability, and behavior under game or system load remain unmeasured.

## Desktop checklist

- **Input over everyday apps.** Start with `--paused` over a browser or editor. Click and scroll in all four transparent corners and between the legs. Confirm that the underlying app receives those inputs and keeps keyboard focus. Click the character and verify its sensor color changes.
- **Boundary and interruption behavior.** Drag against every screen edge and the taskbar, then release. Confirm the overlay stays reachable and resumes when appropriate. Alt+Tab or lock and unlock the desktop during a drag, then check that a fresh click or drag works.
- **Display changes.** With two physical monitors at different scaling settings, drag across both directions and across offset edges. Change resolution or disconnect the display holding the overlay and confirm it returns to a usable work area. The Qt scaling override exercised one display. Physical mixed-DPI monitor crossings and display hot-plug still need testing. Automatic movement stays on the active monitor.
- **Window movement under load.** Launch with `--watch-windows`, then move, resize, minimize, restore, and close an ordinary app while the overlay moves. Look for the updates after each change. The scanner samples snapshots every half second, so brief changes can be missed. Check pointer response and smoothness while other apps are busy, including a full-screen app.
- **Longer run.** Leave the overlay moving and paused for several minutes each. Compare CPU and working set in Task Manager and try **Quit ARACHNID** after each run.

## Re-run the native desktop test

Use an unlocked Windows desktop. Leave the mouse alone while the test briefly moves and restores the pointer. The test clicks the overlay and a fixture window that it creates, and it checks the window under the pointer before sending button presses.

```powershell
$env:ARACHNID_DESKTOP_TEST = '1'
& .\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:ARACHNID_DESKTOP_TEST
```

Use the prepared interpreter path in the [README](README.md) when testing from the original workspace. If the test cannot set the cursor, run it from a regular interactive PowerShell window on the input desktop.
