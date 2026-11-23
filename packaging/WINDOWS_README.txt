Arachnid 1.1.0 | Windows 11 x64 portable release

Quit any earlier preview, then extract the entire archive to its own
folder. Open the Arachnid folder and double-click Arachnid.exe. Keep the
_internal folder beside it. Python is bundled and your preferences carry over.
This portable build is unsigned. Windows SmartScreen may warn about it.
Check the download origin and the published SHA-256 before opening it.
Requires the x64 Microsoft Visual C++ v14 Redistributable.
https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

Left-click to pet the scorpion. It crouches, wags its tail, and shows a heart. When picked up, it trails the
cursor briefly, kicks its legs, and pouts until you put it down.
Right-click and choose Rest to make it sleep or Wake Up to rouse it.
Pause and Resume remain separate controls. Enable Curl up while sleeping
in Settings to use the curled pose when you choose Rest.
Right-click the Arachnid system tray icon for Pause/Resume, Rest/Wake Up,
Show/Hide, Settings, and Quit. Check the taskbar's hidden-icons arrow if
the icon is in overflow. The tray menu remains available while Arachnid
is hidden or asleep. Left-click the icon to reopen Arachnid after
hiding it or closing the window. Quit exits the app. To reopen after Quit,
right-click Arachnid.exe and choose Show more options > Pin to taskbar.
Launching again brings back the running companion when it uses the same
settings profile.

On startup, Arachnid pulls open a rift with its front legs and walks out.
Blackout Red is the default for a fresh settings profile.

In Settings, pick Graphite, Foundry, Glacier, Blackout Red, or Industrial Yellow,
then choose Save. The Size slider previews sizes from 70% to 150%.
Industrial Yellow has weathered yellow plating, exposed wiring, and a segmented
cyan visor that glitches briefly on wake-up and pickup.
Click sound is muted by default. Preferences are stored per Windows user.
Enable Bird's-eye view to roam in any direction on the current display.
Use the side view to climb and perch on application windows.
Drop Arachnid just below a window with room underneath to crawl upside down.
Or drop it beside the lower half of either side to watch it descend
and round the bottom corner. A higher drop leads toward the top.
Drag sideways to see the chassis lean. Release slowly for a normal drop or
release during a fast flick to throw it. Arachnid absorbs the landing and
resumes roaming. Grab it again to interrupt a throw. Disable Enable Throwing
in Settings to use normal drops every time.

In side view, Arachnid occasionally climbs a clear physical screen edge,
turns at the upper corner, and crawls upside down along the top boundary.
A taskbar blocks the edge it occupies. Routes stay on the active display.
In bird's-eye view, the robot shortens its stride during sharp turns.

To try climbing, focus an unmaximized app window with room around it.
Drop Arachnid beside a side edge or place its feet on the top edge.
Move the cursor away so its autonomous behavior can resume.

Arachnid hides for fullscreen apps and restores your last Show/Hide choice
when you return to the desktop. It stays visible with ordinary title-bar
windows that are maximized.

Optional PowerShell launch flags from the extracted folder:
    Start-Process .\Arachnid.exe -ArgumentList '--paused'
    Start-Process .\Arachnid.exe -ArgumentList '--speed','180'
    Start-Process .\Arachnid.exe -ArgumentList '--desktop-edge-preview'

The package is intended for Windows 11 x64. A verified clean Windows 11
installation and physical mixed-DPI display changes remain untested.

See THIRD_PARTY_NOTICES.txt and LICENSES for the bundled components.
