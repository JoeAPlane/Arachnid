# Architecture

| Module | Responsibility |
| --- | --- |
| `arachnid.__main__` | Parse launch options, start Qt and the window monitor, and handle terminal shutdown. |
| `arachnid.overlay` | Host the Qt Graphics View, supply cursor distance and active time, drive motion, and handle input and work-area placement. |
| `arachnid.behavior` | Choose timed activities and walking direction changes independently of Qt. |
| `arachnid.character` | Draw the robot and animate its gait, facing, chassis posture, tail, and sensor lights. |
| `arachnid.appearance` | Define finishes for the shared mechanical rig. |
| `arachnid.settings` | Preview and persist finishes and feedback preferences per Windows user. |
| `arachnid.feedback` | Play the optional servo sound without blocking the overlay. |
| `arachnid.gait` | Calculate foot trajectories and the knee of each two-segment leg. |
| `arachnid.movement` | Clamp coordinates to a work area and reflect horizontal velocity at its edges. |
| `arachnid.navigation` | Attach to a logical window edge and calculate side, corner, and top poses. |
| `arachnid.windows` | Read top-level window bounds and foreground coverage with Win32. |

The overlay uses one small, frameless tool window. Qt renders the scene with a transparent background. Windows can deliver input through pixels with zero alpha, while painted pixels can receive mouse events. The overlay stops moving during a press or context menu and while paused. It cancels a press if Windows takes away mouse capture and Qt provides no matching release. Dragging uses the monitor at the cursor, with a fallback to the pet's current monitor when the cursor is in a gap. Automatic motion stays on one monitor at a time.

The Windows tray and overlay context menus share Pause/Resume, Rest/Wake Up, Settings, and Quit actions. Manual Show/Hide is independent of fullscreen suppression. The foreground monitor stays active while the character is hidden so it can restore visibility after a fullscreen app closes when the user has selected Show. [Qt tray icon documentation](https://doc.qt.io/qt-6/qsystemtrayicon.html)

The character's pose advances with distance traveled. At full stride, the lateral movement of a planted foot offsets the movement of the window. The other set of legs lifts and swings forward. A shared gait phase drives the chassis bob and tail sway. The movement timer ramps speed when motion starts or changes between a climb and top-edge walking. The remaining gait and posture animations finish over short Qt animation intervals, including a narrowed silhouette as the robot changes facing. Holding the robot cancels the stride immediately.

The behavior timer wakes roughly every 125 ms while the companion is active. Walking and observation sample cursor distance. Observation starts within 155 logical pixels and ends at 215 pixels or after a short timeout, with a cooldown before attention can recur. The 16 ms movement timer runs only during walks. Rests lower the body, relax the tail, and dim the optics. Clicks temporarily draw attention and brighten the sensor. Pausing, holding the character, and opening the menu suspend both timers.

The window monitor samples every 500 ms. It excludes the overlay process, hidden or minimized windows, tool windows, untitled windows, shell windows, cloaked windows, and windows entirely outside the monitor layout. A window crossing a monitor edge is still eligible. The monitor compares consecutive samples for additions, removals, and changes to bounds. Changes that happen entirely between two samples may be missed.

Window discovery stores physical desktop pixels with exclusive right and bottom edges. Navigation converts offsets from the Windows monitor origin into Qt logical pixels using the current screen's device pixel ratio. It checks the current origin and scaled dimensions before accepting a snapshot. A route keeps its distance along the current edge as the foreground window moves. It detaches when the edge leaves the usable area or the window disappears or loses focus. If a display configuration change leaves the robot outside the screen layout, it moves to the nearest surviving work area. Climbing uses the walking gait rotated toward the side and advances through a quarter-circle turn at the top corner. [Qt high-DPI documentation](https://doc.qt.io/qt-6/highdpi.html)

The window monitor listens for foreground changes through an out-of-context Windows event subscription. A 75 ms foreground sample also catches moves, resizes, and display mode changes while focus stays on the same window. The separate 500 ms census of all visible windows runs only with `--watch-windows`. A frame covering its monitor hides the overlay, except when Windows reports a conventional maximized title-bar window. The overlay stays hidden through short gaps in foreground detection. Focus on ARACHNID's own settings or menu preserves the last external window snapshot until external focus resolves. [Microsoft foreground events](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwineventhook) · [Microsoft IsZoomed](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-iszoomed)

Settings suspend autonomous activity while the dialog is open. Save applies the previewed finish and feedback options through QSettings. The click pulse stays inside the painted optic, and the original servo sample plays asynchronously through Windows. [Qt settings documentation](https://doc.qt.io/qtforpython-6.8/PySide6/QtCore/QSettings.html) · [Python Windows audio documentation](https://docs.python.org/3.12/library/winsound.html)

Bird’s-eye view reuses the alternating gait with a top-down rig and reflects motion independently at horizontal and vertical work-area edges. It detaches the character from window routes. Drag uses a bounded positional lag, while a brief carry animation drives the legs and tail. Release settles at the cursor-derived drop point before checking for a perch. The Rest/Wake Up action controls a manual sleep state that suspends both autonomous timers until explicitly woken.
